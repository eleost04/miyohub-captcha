# MiyoHub Captcha

[English](README.en.md) · 版本 **0.0.1**

[功能与限制](ROADMAP.md) · [开发与维护规范](CONTRIBUTING.md) · [问题反馈](https://github.com/eleost04/miyohub-captcha/issues)

轻量 CPU 验证码服务，提供兼容 `/pass_nine` 与 `/pass_uni` 的 HTTP 接口，可与 [MiyoHub](https://github.com/eleost04/miyohub) 或兼容客户端配合使用。仅处理本人账号所需的验证，不保证识别准确率或上游接受结果。

本仓库只保存封装、补丁、校验和、测试及部署配置。第三方源代码、模型和验证码图片不提交到 Git。运行代码来自 [test_nine](https://github.com/luguoyixiazi/test_nine)，背景见 [MihoyoBBSTools issue 198](https://github.com/Womsxd/MihoyoBBSTools/issues/198)。上游没有标准开源许可证；下载和使用前请确认相关权利，本项目不额外授予使用或再分发许可。

## 部署

建议 Linux/amd64、Docker Engine、Compose v2、Bash、curl、patch、GNU coreutils。先部署 MiyoHub，使 `miyohub_default` 网络存在。

```bash
git clone https://github.com/eleost04/miyohub-captcha.git
cd miyohub-captcha
cp .env.example .env
bash scripts/prepare.sh --models
docker compose up -d --build
docker compose ps
curl -fsS http://127.0.0.1:9645/healthz
```

`--models` 获取四个必要源码文件、应用 CPU 补丁并下载五个模型。原始源码、补丁后源码和模型分别校验 SHA-256；已有文件不匹配会停止，不覆盖本地修改。只下载源码用 `--source`，完全离线核对用 `--verify`。源码在应用补丁前统一换行，不包含上游图片存档和训练脚本。

固定依赖：

- 源码：`luguoyixiazi/test_nine@a6a53bb46bfd33c419fa503f5a31708462893775`
- 模型：`luguoyixiazi/model_save@5b1a5c666954704136ddbbb2f144167ddf880eed`
- 校验文件：`upstream.sha256`、`runtime.sha256`、`models.sha256`

容器名为 `miyohub-captcha`，宿主机端口仅绑定 `127.0.0.1:9645`。模型从 `./models` 只读挂载，不打入镜像；容器使用非 root 用户、只读根文件系统、96 MiB 临时内存文件系统和受限权限。

## 在 MiyoHub 中使用

管理员在「系统设置 → 站点打码服务」添加自定义渠道：

- 地址：`http://miyohub-captcha:9645/pass_nine`
- 超时：建议 60 秒；启用 V3 模型
- Bearer Token：与本服务 `.env` 中的 `CAPTCHA_API_TOKEN` 一致（如已设置）

再为用户授予站点打码权限，或通过邀请码预设；用户选择站点来源。普通用户的个人渠道不允许访问这个内网地址。Docker 内的 `127.0.0.1` 指容器自身，不是宿主机。

默认无 Token 只适用于可信的回环与内部网络。共享给不可信网络或其他机器前，设置长随机 `CAPTCHA_API_TOKEN`、TLS 和访问限制；更改环境变量后重建容器。不要把密钥放入 URL、README 或 Git，也不要直接公开端口。

## 接口

`GET /healthz` 只有五个 CPU 模型全部可用时返回 200，包含版本和模型列表。健康状态不等于真实验证码已通过。

`GET /pass_nine`（别名 `/pass_uni`）接受：

| 参数 | 含义 |
| --- | --- |
| `gt` | 32 位十六进制验证码参数 |
| `challenge` | 当前有效挑战，32–128 个字母、数字、下划线或连字符 |
| `use_v3_model` | 默认 true；九宫格不支持旧版 ResNet |
| `Authorization` 请求头 | 配置 Token 时必须为 `Bearer <token>` |

成功仅在 `data.result == "success"` 且 `validate` 非空时成立：

```json
{"data":{"result":"success","validate":"...","challenge":"..."}}
```

九宫格、图标点选按上游题型选择模型。错误会返回失败结果或 HTTP 401 / 422 / 429 / 502 / 504；调用方应处理失败，不能只看 HTTP 200。不要拿示例参数当作实际可用性测试，也不要频繁获取或重放真实挑战。

## 性能与限制

- CPU ONNX 推理，不安装 CUDA、Torch 或训练工具。五个模型在启动时加载。
- 单 worker、串行锁，最多等待锁 5 秒，忙时 429；不要增加 worker 数，避免共享图片目录相互干扰。
- 网络请求总预算 50 秒，单个请求最多 10 秒、连接最多 5 秒；等待锁与模型推理另计。MiyoHub 的后台测试有独立超时和冷却。
- 只请求允许的验证码服务域名，不跟随重定向或环境代理。
- 临时图片仅在 tmpfs 使用并在请求结束清理。不启用访问日志，不记录 gt、challenge、validate、账号 Cookie 或 Token。只记脱敏结果 / 异常类型。
- CPU 线程受限，关闭忙等待；修正九宫格回退候选、负等待时间、无检测框和无效裁剪的问题。

参考占用（Linux/amd64，2026-09-11 构建样本）：镜像约 **364.1 MiB**（未压缩），外置模型约 **177 MiB**；启动空闲内存约 **352 MiB**，运行样本约 **535 MiB**。Compose 限额为 **2 CPU / 1536 MiB RAM / 128 PID**。建议预留 2 核和 1.5 GiB；与主站同机建议至少 2 核 / 2 GiB。构建缓存、备份及负载峰值另计，非 amd64 平台尚未验收。

## 验证与日志

无需第三方源码或模型的封装测试：

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python tests/test_wrapper.py
```

构建镜像后，在**关闭网络**的独立容器验证 API 和五个模型的真实 CPU 推理：

```bash
docker run --rm --network none --read-only --cpus 2 --memory 1536m \
  --tmpfs /tmp:size=96m,mode=1777 \
  --mount "type=bind,source=$PWD/models,target=/models,readonly" \
  --mount "type=bind,source=$PWD/test_service.py,target=/app/test_service.py,readonly" \
  miyohub-captcha:local python test_service.py
```

这些测试不获取真实挑战，不发送短信、签到、兑换或推送。PP-HGNet 模型可能提示声明 1000 类而实际 91 类，这是原模型元信息警告；不改模型字节，仍检查原始校验和。离线推理成功不代表真实验证码识别准确率或账号风控一定通过。

MiyoHub 的「测试自定义打码服务」会在后台完成一次匿名测试，断开页面不取消，每用户每分钟最多一次；日志和结果在主站查询。不要用刷新按钮反复启动测试。

```bash
docker compose logs --tail 50
docker compose restart captcha
docker stats --no-stream miyohub-captcha
```

日常更新使用 `docker compose up -d --build`，不删除模型；先保留旧镜像和经校验的模型再升级。若要移除主站网络，须先停止本服务。

## 开发与发布

提交、分支、GPG 签名和版本规则见 [CONTRIBUTING.md](CONTRIBUTING.md)；支持范围和待办见 [ROADMAP.md](ROADMAP.md)。`VERSION` 是服务版本的唯一来源，主站和本服务独立迭代。

CI 使用模型替身校验封装、鉴权、错误脱敏和并发限制，不自动下载模型。发布检查版本、分支归属及 GitHub 的签名验证结果，只发布源码包，**不自动推送 Docker 镜像**。

推送后如未生成测试任务，可在 Actions 中手动运行 `Verify wrapper`。发布中断时，可手动运行 `Publish signed source release` 并填写已存在的签名标签；同样检查签名、分支和测试，不覆盖已有 Release，不请求真实验证码服务。

Git 排除 `upstream/`、`models/`、`.env*`（示例除外）、`docs/`、虚拟环境、缓存、日志、临时图片、密钥和归档。Docker 构建采用文件白名单，只有必需运行文件进入构建。不要使用 `git add -f` 绕过这些边界。

如需分发镜像，使用明确的版本标签，模型保持外置，并先核实第三方运行代码和模型的使用及再分发许可。仓库或镜像的可见性不改变许可要求。

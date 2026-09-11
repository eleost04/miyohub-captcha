# MiyoHub 本地验证码服务

基于 [test_nine](https://github.com/luguoyixiazi/test_nine)，对应 [MihoyoBBSTools issue 198](https://github.com/Womsxd/MihoyoBBSTools/issues/198)。仅作个人学习使用，遵守上游项目和模型的使用限制；上游未提供标准开源许可证，不额外授予再分发许可。

上游源码固定于 `a6a53bb46bfd33c419fa503f5a31708462893775`，保留在 `upstream/` 中。模型来自作者 [Hugging Face 仓库](https://huggingface.co/luguoyixiazi/model_save)，版本 `5b1a5c666954704136ddbbb2f144167ddf880eed`，可用 `sha256sum -c models.sha256` 校验。

## 启动

先启动相邻的 MiyoHub，再在本目录执行：

```bash
docker compose up -d --build
docker compose ps
curl -fsS http://127.0.0.1:9645/healthz
```

服务加入已有的 `miyohub_default` 网络。MiyoHub「系统设置 → 验证码服务」选择「自建 / 自定义服务」，地址 `http://miyohub-captcha:9645/pass_nine`，超时 60 秒，启用 V3 模型。宿主机上的程序使用 `http://127.0.0.1:9645/pass_nine`。两种地址不能混用，容器内 127.0.0.1 并不是宿主机。

`/pass_uni` 是兼容别名，九宫格和图标点选按上游类型自动选择模型。接口接受 GET 参数 `gt`、`challenge`、`use_v3_model`（默认 true），只有 `data.result == "success"` 且 `data.validate` 非空时才算通过。本部署不含旧版 ResNet 模型。

默认不向公网开放，仅映射宿主机回环地址。同网络容器可调用。若另行开放给其他机器，必须自行配置 TLS 和 `CAPTCHA_API_TOKEN` 环境变量；MiyoHub 中填写对应 Bearer Token，不要把密钥放入 URL。无需放宽 MiyoHub 的推送私网策略。

## 本地优化

- 仅 CPU ONNX 推理，不安装训练框架、CUDA、Torch 或图形界面依赖。
- 五个模型在启动时加载，最多使用 2 个 CPU、1536 MiB 内存；推理关闭忙等待。
- 单 worker + 串行锁保护上游共享图片目录，忙时返回 429，避免串图和资源争抢。不要增加 worker 数。
- 单次上游请求不超过 10 秒、连接不超过 5 秒，并受 50 秒请求预算限制；重试由 MiyoHub 管理。
- 没有访问日志，不记录 gt、challenge、validate、聊天信息或账号凭据。
- 图片只在受限 tmpfs 暂存，请求结束清理；模型只读、进程非 root、无额外权限。
- 修正上游九宫格候选回退取错第二高分的问题；避免负等待时间。
- 修正图标检测没有候选框时崩溃的问题，并跳过无效裁剪区域。

健康检查与本地模型推理测试不等于真实验证码通过保证；上游可能更换题型或协议，识别也存在失败概率。只在你自己的账号被要求验证时调用。

离线回归测试见 `test_service.py`，在关闭网络的容器中检查接口、参数、鉴权、并发隔离、清理和五个模型的真实推理。PP-HGNet 模型可能提示输出声明 1000 类、实际 91 类，这是作者模型的元信息警告，不影响实际分类输出；模型文件仍保留原始校验和。

## 运维

```bash
docker compose logs --tail 50
docker compose restart captcha
docker stats --no-stream
```

重启仅影响本服务，不动 MiyoHub 数据卷。若需要 `docker compose down` 移除 MiyoHub 网络，请先停止本服务；日常更新使用 `up -d --build` 即可。模型文件不提交到 Git，也不复制进镜像。

# MiyoHub Captcha

[English](README.en.md) · 版本 **0.0.1** · 镜像 **eleost/miyohub-captcha:latest**

[功能与限制](ROADMAP.md) · [开发与维护规范](CONTRIBUTING.md) · [问题反馈](https://github.com/eleost04/miyohub-captcha/issues)

轻量 CPU 验证码服务，提供兼容 `/pass_nine` 与 `/pass_uni` 的 HTTP 接口，可与 [MiyoHub](https://github.com/eleost04/miyohub) 或兼容客户端配合使用。仅处理本人账号所需的验证，不保证识别准确率或上游接受结果。

本服务已发布官方自包含 Docker 镜像（内置全部 5 个 ONNX 深度学习模型，开箱即用，无需在宿主机额外下载或配置模型环境）。

---

## 🖥️ 服务器配置要求与推荐

本服务采用纯 CPU 进行轻量 ONNX 神经网络推理（无须 GPU/CUDA）。服务器资源配置建议如下：

| 项目 | 最低配置 (仅运行验证码) | 推荐配置 (单独运行) | 推荐配置 (与 MiyoHub 同机) |
| :--- | :--- | :--- | :--- |
| **CPU** | 1 核 (vCPU) | **2 核** (vCPU) | **2 核或以上** |
| **可用内存 (RAM)** | 1.0 GiB (建议开 Swap) | **1.5 GiB** | **2.0 GiB ~ 4.0 GiB** |
| **磁盘空间** | 1.5 GB 可用空间 | **3.0 GB** 可用空间 | **5.0 GB** 可用空间 |
| **系统架构** | Linux/amd64 (x86_64) | Linux/amd64 | Linux/amd64 |
| **Docker 资源限制** | `--cpus 1 --memory 1024m` | `--cpus 2 --memory 1536m` | 视机器总体负载动态分配 |

### 实际资源占用参考（Linux/amd64 实测）：
* **镜像体积**：约 **567 MB**（自包含镜像，含 5 个 ONNX 模型与全部 Python 依赖）。
* **启动空闲内存**：容器启动初始化并加载全部 5 个模型后，常驻内存约 **350 MiB**。
* **推理峰值内存**：单次处理图形验证码推理时瞬时峰值约 **530 ~ 750 MiB**。
* **CPU 负载与耗时**：单 worker 串行队列机制；在 2 核 CPU 下，单次九宫格/文字点选推理通常在 **0.5 ~ 2 秒** 内完成。

---

## ⚡ 快速开始（推荐）

### 方式 1：Docker CLI 一键启动

直接执行以下命令，即可拉取并启动服务（端口监听在本地 `127.0.0.1:9645`）：

```bash
docker run -d \
  --name miyohub-captcha \
  --restart unless-stopped \
  -p 127.0.0.1:9645:9645 \
  --read-only \
  --tmpfs /tmp:size=96m,mode=1777 \
  --cpus 2 \
  --memory 1536m \
  eleost/miyohub-captcha:latest
```

如需设置 API 访问鉴权 Token，只需添加 `-e CAPTCHA_API_TOKEN="你的高强度密钥"`。

### 方式 2：Docker Compose 一键部署

1. 下载或克隆仓库，或直接在项目目录创建 `compose.yaml`：

```bash
git clone https://github.com/eleost04/miyohub-captcha.git
cd miyohub-captcha
cp .env.example .env
docker compose up -d
```

2. 检查服务健康状态：

```bash
curl -fsS http://127.0.0.1:9645/healthz
```

返回包含全部 5 个模型（`session`, `session_dfine`, `session_yolo11n`, `session_dino3`, `session_dino_cf`）以及 `"ok": true` 即表示启动成功。

---

## ⚙️ 环境变量与配置说明

所有环境变量均可通过 `.env` 文件或容器启动参数传入：

| 环境变量 | 默认值 | 允许值 / 格式 | 说明与配置建议 |
| :--- | :--- | :--- | :--- |
| **`CAPTCHA_API_TOKEN`** | 空 (`""`) | 字符串 | API 鉴权密钥。为空时任何人均可调用接口（仅推荐在本地 `127.0.0.1` 或 Docker 内部隔离网络使用）；若服务需暴露至局域网或公网，**强烈建议设置长随机 Token**。请求时通过 `Authorization: Bearer <token>` 传入。 |
| **`ORT_THREADS`** | `2` | 整数 (如 `1` ~ `4`) | ONNX Runtime 推理并发线程数。建议根据分配给容器的 CPU 核心数配置。 |
| **`OMP_NUM_THREADS`** | `2` | 整数 | OpenMP 底层加速线程数。通常与 `ORT_THREADS` 保持一致。 |
| **`OPENBLAS_NUM_THREADS`** | `1` | 整数 | OpenBLAS 矩阵计算线程数，CPU 轻量运行保持 `1` 即可。 |
| **`CAPTCHA_MODEL_DIR`** | `/models` | 绝对路径 | 模型文件存放路径。官方镜像内置已存放在 `/models`，无需更改。 |
| **`CAPTCHA_WORK_DIR`** | `/tmp/captcha`| 绝对路径 | 临时工作缓存目录，运行时挂载于 tmpfs 内存盘中。 |
| **`use_pdl`** | `1` | `1` 或 `0` | 是否启用 Paddle 快速点选定位模型（`1` 开启，`0` 关闭）。 |
| **`use_dfine`** | `1` | `1` 或 `0` | 是否启用 D-FINE 目标检测器（`1` 开启，`0` 关闭）。 |
| **`use_multi`** | `1` | `1` 或 `0` | 是否启用多目标/多文字识别（`1` 开启，`0` 关闭）。 |
| **`CAPTCHA_BIND_ADDR`** | `127.0.0.1` | IP 地址 | Compose 宿主机监听地址。默认为本地回环 `127.0.0.1`，防止公网未授权暴露。 |
| **`CAPTCHA_PORT`** | `9645` | 端口号 | Compose 宿主机映射端口。 |

---

## 在 MiyoHub 中使用

管理员在「系统设置 → 站点打码服务」添加自定义渠道：

* **地址**：
  * **同机 Docker 网络互通**：`http://miyohub-captcha:9645/pass_nine`（需将本容器接入 `miyohub_default` 网络）
  * **宿主机回环地址**：`http://127.0.0.1:9645/pass_nine` 或宿主机内网 IP
* **超时**：建议 60 秒；启用 V3 模型
* **Bearer Token**：与本服务配置的 `CAPTCHA_API_TOKEN` 保持一致（若未设置则留空）

再为用户授予站点打码权限，或通过邀请码预设；用户选择站点来源。普通用户的个人渠道不允许访问这个内网地址。Docker 内的 `127.0.0.1` 指容器自身，不是宿主机。

---

## 接口说明

### 1. 健康检查 `GET /healthz`
只有五个 CPU 模型全部加载可用时返回 200，包含版本与就绪模型列表：
```json
{
  "ok": true,
  "version": "0.0.1",
  "models": ["session", "session_dfine", "session_yolo11n", "session_dino3", "session_dino_cf"],
  "device": "CPU",
  "max_concurrency": 1
}
```

### 2. 验证码识别 `GET /pass_nine`（别名 `/pass_uni`）

| 参数 | 含义 |
| :--- | :--- |
| `gt` | 32 位十六进制极验验证码参数 |
| `challenge` | 当前有效挑战，32–128 个字符 |
| `use_v3_model` | 默认 true；九宫格不支持旧版 ResNet |
| `Authorization` 请求头 | 配置 Token 时必须为 `Bearer <token>` |

成功响应示例（仅在 `data.result == "success"` 且 `validate` 非空时成立）：
```json
{"data":{"result":"success","validate":"...","challenge":"..."}}
```

---

## 本地从源码构建部署（开发者选项）

如果你需要自行修改上游运行代码或从原始模型重新打包：

```bash
git clone https://github.com/eleost04/miyohub-captcha.git
cd miyohub-captcha
cp .env.example .env
# 下载源码补丁与 5 个 ONNX 模型权重（校验 SHA-256）
bash scripts/prepare.sh --models
# 本地编译并启动
docker compose -f compose.yaml up -d --build
```

固定上游依赖：
- 源码：`luguoyixiazi/test_nine@a6a53bb46bfd33c419fa503f5a31708462893775`
- 模型：`luguoyixiazi/model_save@5b1a5c666954704136ddbbb2f144167ddf880eed`
- 校验文件：`upstream.sha256`、`runtime.sha256`、`models.sha256`

---

## 性能与安全限制

- **CPU ONNX 推理**：不依赖 CUDA、Torch 或其他重量级框架，启动时一次性加载全部模型。
- **单 Worker 串行排队**：单 worker 设计，防并发资源争抢，最多等待锁 5 秒，忙时返回 429。
- **内存与沙箱限制**：容器使用非 root 用户、只读根文件系统、96 MiB tmpfs 内存临时盘和最少必要权限。推荐分配限额：**2 CPU / 1536 MiB RAM / 128 PID**。
- **隐私保护**：临时图片处理完毕立即销毁；不记录任何请求日志中的 Cookie、Token、gt 或 validate 等敏感字段。

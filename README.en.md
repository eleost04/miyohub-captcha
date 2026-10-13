# MiyoHub Captcha

[简体中文](README.md) · Version **0.0.1** · Image **eleost/miyohub-captcha:latest**

[Capabilities and limits](ROADMAP.md) · [Contributing](CONTRIBUTING.md) · [Issues](https://github.com/eleost04/miyohub-captcha/issues)

A lightweight CPU captcha service exposing `/pass_nine` and `/pass_uni` for [MiyoHub](https://github.com/eleost04/miyohub) and compatible clients. Use only for verification required by an account you own. Recognition accuracy and upstream acceptance are not guaranteed.

Official self-contained Docker images are available on Docker Hub (including all 5 bundled ONNX weights, ready to run out of the box without manual model downloads).

---

## 🖥️ Server Hardware Requirements & Recommendations

This service performs lightweight ONNX neural network inference entirely on CPU (no GPU/CUDA needed). Hardware recommendations:

| Specification | Minimum (Captcha Only) | Recommended (Standalone) | Recommended (Co-hosted with MiyoHub) |
| :--- | :--- | :--- | :--- |
| **CPU** | 1 Core (vCPU) | **2 Cores** (vCPU) | **2 Cores or more** |
| **Available Memory (RAM)** | 1.0 GiB (Swap recommended) | **1.5 GiB** | **2.0 GiB ~ 4.0 GiB** |
| **Disk Space** | 1.5 GB available | **3.0 GB** available | **5.0 GB** available |
| **Architecture** | Linux/amd64 (x86_64) | Linux/amd64 | Linux/amd64 |
| **Docker Resource Limits** | `--cpus 1 --memory 1024m` | `--cpus 2 --memory 1536m` | Scale based on host capacity |

### Measured Runtime Footprint (Linux/amd64):
* **Image Size**: ~**567 MB** (Self-contained image with 5 pre-bundled ONNX models).
* **Startup Idle Memory**: ~**350 MiB** once all models are initialized into memory.
* **Inference Peak Memory**: ~**530 ~ 750 MiB** during captcha processing.
* **Inference Latency**: Single-worker serialized queue; inference completes within **0.5 ~ 2.0 seconds** on a 2-core CPU.

---

## ⚡ Quick Start (Recommended)

### Method 1: One-liner with Docker CLI

Run the following command to pull and start the container (bound to `127.0.0.1:9645` on host):

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

To enable API authentication, append `-e CAPTCHA_API_TOKEN="your_strong_random_token"`.

### Method 2: Docker Compose

1. Clone repository or copy `compose.yaml` and `.env.example`:

```bash
git clone https://github.com/eleost04/miyohub-captcha.git
cd miyohub-captcha
cp .env.example .env
docker compose up -d
```

2. Check service health:

```bash
curl -fsS http://127.0.0.1:9645/healthz
```

---

## ⚙️ Environment Variables & Configuration

All environment variables can be provided via `.env` or container startup options:

| Variable | Default | Format / Values | Description |
| :--- | :--- | :--- | :--- |
| **`CAPTCHA_API_TOKEN`** | `""` (empty) | String | Bearer authentication token. When empty, anyone with network access can query the endpoint (recommended only on `127.0.0.1` or isolated Docker networks). For untrusted or remote networks, set a strong random token. Passed via `Authorization: Bearer <token>`. |
| **`ORT_THREADS`** | `2` | Integer (e.g. `1` - `4`) | ONNX Runtime inference thread limit. Allocate based on available CPU cores. |
| **`OMP_NUM_THREADS`** | `2` | Integer | OpenMP threading limit. Usually set matching `ORT_THREADS`. |
| **`OPENBLAS_NUM_THREADS`** | `1` | Integer | OpenBLAS linear algebra threads (keep `1` for lightweight deployment). |
| **`CAPTCHA_MODEL_DIR`** | `/models` | Absolute path | Directory containing the 5 ONNX weights. Pre-bundled inside the image. |
| **`CAPTCHA_WORK_DIR`** | `/tmp/captcha`| Absolute path | Temporary scratch directory hosted inside tmpfs. |
| **`use_pdl`** | `1` | `1` or `0` | Enable Paddle point-click position locator model. |
| **`use_dfine`** | `1` | `1` or `0` | Enable D-FINE detector model. |
| **`use_multi`** | `1` | `1` or `0` | Enable multi-target character matching model. |
| **`CAPTCHA_BIND_ADDR`** | `127.0.0.1` | IP address | Host binding address for Docker Compose. Defaults to loopback. |
| **`CAPTCHA_PORT`** | `9645` | Port number | Host published port for Docker Compose. |

---

## Configure MiyoHub

An administrator adds a custom site provider:

- Endpoint:
  - Docker network link: `http://miyohub-captcha:9645/pass_nine` (join `miyohub_default` network)
  - Host loopback / LAN IP: `http://127.0.0.1:9645/pass_nine`
- Recommended timeout: 60 seconds; enable the V3 model
- Bearer Token: match `CAPTCHA_API_TOKEN` configured above (leave blank if unset)

Grant site-captcha access through user administration or invitation presets. The user selects the site source. Personal user providers cannot reach this private endpoint. Inside Docker, `127.0.0.1` refers to the calling container, not the host.

---

## API Reference

### 1. Health check `GET /healthz`
Returns 200 only when all 5 CPU models are loaded and healthy:
```json
{
  "ok": true,
  "version": "0.0.1",
  "models": ["session", "session_dfine", "session_yolo11n", "session_dino3", "session_dino_cf"],
  "device": "CPU",
  "max_concurrency": 1
}
```

### 2. Solve captcha `GET /pass_nine` (alias `/pass_uni`)

| Parameter | Description |
| :--- | :--- |
| `gt` | 32-character hex Geetest parameter |
| `challenge` | 32–128 character challenge token |
| `use_v3_model` | Defaults to true; grid does not support legacy ResNet |
| `Authorization` | Required when token is set: `Bearer <token>` |

Successful response:
```json
{"data":{"result":"success","validate":"...","challenge":"..."}}
```

---

## Build from Source (Developer Option)

If you need to customize patches or build models locally:

```bash
git clone https://github.com/eleost04/miyohub-captcha.git
cd miyohub-captcha
cp .env.example .env
bash scripts/prepare.sh --models
docker compose -f compose.yaml up -d --build
```

Pinned dependencies:
- Source: `luguoyixiazi/test_nine@a6a53bb46bfd33c419fa503f5a31708462893775`
- Models: `luguoyixiazi/model_save@5b1a5c666954704136ddbbb2f144167ddf880eed`
- Manifests: `upstream.sha256`, `runtime.sha256`, `models.sha256`

---

## Performance & Security Limits

- **CPU ONNX Inference**: No CUDA, Torch, or GPU dependencies; all 5 models load at startup.
- **Single-Worker Queue**: Serialized request handling to prevent CPU contention; busy requests return HTTP 429 after 5s lock timeout.
- **Sandbox Security**: Runs under non-root UID, read-only rootfs, 96 MiB tmpfs scratch mount, and dropped privileges.
- **Privacy Assurance**: Scratch files deleted immediately; never logs tokens, cookies, or challenge payloads.

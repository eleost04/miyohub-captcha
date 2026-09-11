# MiyoHub Captcha

[简体中文](README.md) · Version **0.0.1**

[Capabilities and limits](ROADMAP.md) · [Contributing](CONTRIBUTING.md) · [Issues](https://github.com/eleost04/miyohub-captcha/issues)

A lightweight CPU captcha service exposing `/pass_nine` and `/pass_uni` for [MiyoHub](https://github.com/eleost04/miyohub) and compatible clients. Use only for verification required by an account you own. Recognition accuracy and upstream acceptance are not guaranteed.

This repository contains only the wrapper, patch, checksums, tests and deployment configuration. Third-party sources, weights and challenge images are not committed. Runtime code is based on [test_nine](https://github.com/luguoyixiazi/test_nine); see [MihoyoBBSTools issue 198](https://github.com/Womsxd/MihoyoBBSTools/issues/198). Upstream has no standard open-source license. Verify your rights before downloading or using it; this project grants no additional usage or redistribution rights.

## Deployment

Recommended environment: Linux/amd64, Docker Engine, Compose v2, Bash, curl, patch and GNU coreutils. Deploy MiyoHub first so that `miyohub_default` exists.

```bash
git clone https://github.com/eleost04/miyohub-captcha.git
cd miyohub-captcha
cp .env.example .env
bash scripts/prepare.sh --models
docker compose up -d --build
docker compose ps
curl -fsS http://127.0.0.1:9645/healthz
```

The preparation script downloads four runtime files, applies the CPU patch and optionally fetches five models. Original sources, patched sources and models are SHA-256 verified separately. Existing modified files cause a stop rather than being overwritten. Use `--source` for code only or `--verify` for offline verification. Source line endings are normalized before patching; no upstream training scripts or image archives are included.

Pinned dependencies:

- Source: `luguoyixiazi/test_nine@a6a53bb46bfd33c419fa503f5a31708462893775`
- Models: `luguoyixiazi/model_save@5b1a5c666954704136ddbbb2f144167ddf880eed`
- Manifests: `upstream.sha256`, `runtime.sha256`, `models.sha256`

The container is `miyohub-captcha`, bound only to host `127.0.0.1:9645`. Models are mounted read-only from `./models`, not included in the image. The process is non-root, with a read-only root filesystem, 96 MiB tmpfs and restricted privileges.

## Configure MiyoHub

An administrator adds a custom site provider:

- Endpoint: `http://miyohub-captcha:9645/pass_nine`
- Recommended timeout: 60 seconds; enable the V3 model
- Bearer Token: match `CAPTCHA_API_TOKEN` in this service's untracked `.env`, if set

Grant site-captcha access through user administration or invitation presets. The user selects the site source. Personal user providers cannot reach this private endpoint. Inside Docker, `127.0.0.1` refers to the calling container, not the host.

Token-free use is only suitable on a trusted loopback/internal network. Before sharing with other machines or an untrusted network, configure a long random token, TLS and access restrictions. Recreate the container after changing environment variables. Do not expose the port directly or put tokens in URLs, documentation or Git.

## API

`GET /healthz` returns 200 only when all five CPU models are available. It reports the service version and model list; health does not imply a successful live captcha.

`GET /pass_nine` and alias `/pass_uni` accept:

| Input | Meaning |
| --- | --- |
| `gt` | 32-character hexadecimal parameter |
| `challenge` | A current challenge, 32–128 alphanumeric, underscore or hyphen characters |
| `use_v3_model` | Defaults to true; nine-grid challenges do not support the legacy ResNet model |
| `Authorization` header | `Bearer <token>` when authentication is configured |

Success requires `data.result == "success"` and a non-empty `validate`:

```json
{"data":{"result":"success","validate":"...","challenge":"..."}}
```

Models are selected according to the upstream nine-grid/icon challenge type. Failures return an unsuccessful result or HTTP 401/422/429/502/504. HTTP 200 alone is not proof of success. Placeholder parameters are not an availability test; do not repeatedly obtain or replay live challenges.

## Runtime limits

- CPU ONNX only; no CUDA, Torch or training stack. Five models load at startup.
- Exactly one worker and a serialization lock. Lock acquisition waits at most five seconds, then returns 429. Additional workers are unsupported because upstream scratch storage is shared.
- A 50-second network-call budget, with at most ten seconds per request and five seconds for connection. Lock waiting and model inference are additional; MiyoHub probes have a separate deadline and cooldown.
- Only approved captcha-service domains are contacted; no redirects or environment proxies.
- Temporary images stay in tmpfs and are removed after requests. Access logs are disabled. Challenge values, validation strings, account Cookies and tokens are never logged; only safe outcome/error metadata is retained.
- CPU threads are bounded and busy-spinning is disabled. The patch fixes second-choice classification, negative wait time, empty detection results and invalid crop boxes.

Linux/amd64 measurements on 2026-09-11: approximately **364.1 MiB** local uncompressed image, **177 MiB** external models, **352 MiB** idle memory just after startup and **535 MiB** in an earlier running sample. Compose limits are **2 CPUs / 1536 MiB RAM / 128 PIDs**. Reserve 2 CPUs and 1.5 GiB for this service, or at least 2 CPUs/2 GiB for it and the main app together. Allow additional space for build caches and backups and headroom for peak load. Other architectures have not been runtime-tested.

## Verification and logs

Wrapper checks require no upstream code or weights:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python tests/test_wrapper.py
```

After building, test the API and real CPU inference of all five models in a **network-disabled** container:

```bash
docker run --rm --network none --read-only --cpus 2 --memory 1536m \
  --tmpfs /tmp:size=96m,mode=1777 \
  --mount "type=bind,source=$PWD/models,target=/models,readonly" \
  --mount "type=bind,source=$PWD/test_service.py,target=/app/test_service.py,readonly" \
  miyohub-captcha:local python test_service.py
```

These checks do not obtain real challenges or send SMS, check-ins, exchanges or notifications. The PP-HGNet model may report a declared 1000-class output versus an actual 91-class output; this is upstream metadata. Original model bytes/checksums are retained. Successful offline inference does not measure live accuracy or guarantee account-risk-control acceptance.

MiyoHub's custom-provider test runs an anonymous probe in the background, survives browser disconnection and is limited to once per user per minute. Read the saved result and redacted logs in the main app; refreshing status does not initiate another solve.

```bash
docker compose logs --tail 50
docker compose restart captcha
docker stats --no-stream miyohub-captcha
```

Upgrade with `docker compose up -d --build`, preserving verified model files and the previous image for rollback. Stop this service before removing the main application's network.

## Development and releases

See [CONTRIBUTING.md](CONTRIBUTING.md) for commits, branches, GPG signatures and version policy, and [ROADMAP.md](ROADMAP.md) for supported capabilities and pending work. `VERSION` is the canonical service version. This service and the main app are versioned independently.

CI tests authorization, redaction, protocol and concurrency with stub models; it does not fetch weights. Releases check version, branch ancestry and GitHub signature verification, and publish source archives only. **Docker images are not automatically pushed.**

If a push does not create a test run, manually run `Verify wrapper` from Actions. To recover an interrupted release, run `Publish signed source release` with an existing signed tag. The same signature, branch and test checks apply; existing releases are not overwritten and no live captcha service is called.

Git excludes `upstream/`, `models/`, actual `.env*` files, `docs/`, virtual environments, caches, logs, scratch images, credentials and archives. Docker uses an explicit input allowlist. Do not bypass these boundaries with forced adds.

Any image distribution should use explicit version tags and external model mounts. Verify usage and redistribution rights for third-party runtime code and weights first; repository or image visibility does not change those requirements.

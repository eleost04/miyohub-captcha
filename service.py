"""Private, bounded test_nine service. No account credentials or image archive."""

import json
import logging
import os
from pathlib import Path
import secrets
import threading
import time

import httpx
from fastapi import FastAPI, Header, HTTPException, Query

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

from crack import Crack
from crop_image import crop_image_v3, validate_path
import predict

version = Path(__file__).with_name("VERSION").read_text(encoding="utf-8").strip()
app = FastAPI(title="MiyoHub captcha", version=version, docs_url=None, redoc_url=None, openapi_url=None)
lock = threading.Lock()
log = logging.getLogger("captcha")
log.setLevel(logging.INFO)
api_token = os.getenv("CAPTCHA_API_TOKEN", "")
model_names = ("session", "session_dfine", "session_yolo11n", "session_dino3", "session_dino_cf")


class DeadlineClient(httpx.Client):
    def __init__(self, deadline):
        super().__init__(http2=True, follow_redirects=False, trust_env=False)
        self.deadline = deadline

    def request(self, method, url, **kwargs):
        target = httpx.URL(url)
        if target.scheme != "https" or not any(
            target.host == domain or target.host.endswith("." + domain)
            for domain in ("geetest.com", "geevisit.com", "geetest.cn")
        ):
            raise ValueError("unexpected upstream host")
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("request budget exhausted")
        kwargs["timeout"] = httpx.Timeout(min(10.0, remaining), connect=min(5.0, remaining))
        response = super().request(method, url, **kwargs)
        response.raise_for_status()
        return response


def authorize(authorization):
    if api_token and not secrets.compare_digest(authorization or "", "Bearer " + api_token):
        raise HTTPException(status_code=401, detail="unauthorized")


@app.get("/healthz")
def health():
    loaded = [name for name in model_names if getattr(predict, name, None) is not None]
    if len(loaded) != len(model_names):
        raise HTTPException(status_code=503, detail="models unavailable")
    return {"ok": True, "version": version, "models": loaded, "device": "CPU", "max_concurrency": 1}


def solve_challenge(gt, challenge, use_v3_model):
    started = time.monotonic()
    with DeadlineClient(started + 50) as client:
        crack = Crack(gt, challenge, session=client)
        crack.gettype()
        crack.get_c_s()
        time.sleep(0.5)
        crack.ajax()
        picture, _, picture_type = crack.get_pic()
        if picture_type == "nine":
            if not use_v3_model:
                raise HTTPException(status_code=422, detail="this deployment uses the V3 model")
            crop_image_v3(picture)
            points = [f"{col}_{row}" for row, col in predict.predict_onnx_pdl(validate_path)]
        elif picture_type in ("icon", "icon1"):
            fn = predict.predict_onnx_dfine if picture_type == "icon1" else predict.predict_dino_classify_pipeline
            points = [f"{round(x / 333 * 10000)}_{round(y / 333 * 10000)}" for x, y in fn(picture, False)]
        else:
            raise HTTPException(status_code=422, detail="unsupported challenge type")
        if not points:
            return {"data": {"result": "fail"}, "error": "no matching points"}
        time.sleep(max(0, 4.0 - (time.monotonic() - started)))
        result = json.loads(crack.verify(points))
        data = result.get("data", {})
        validate = data.get("validate")
        if data.get("result") != "success" or not isinstance(validate, str) or not validate.strip():
            return {"data": {"result": "fail"}, "error": "upstream verification rejected"}
        log.info("verification completed: type=%s elapsed=%.2fs", picture_type, time.monotonic() - started)
        return {"data": {"result": "success", "validate": validate, "challenge": data.get("challenge") or challenge}}


@app.get("/pass_nine")
@app.get("/pass_uni")
def captcha(
    gt: str = Query(..., pattern=r"^[a-fA-F0-9]{32}$"),
    challenge: str = Query(..., min_length=32, max_length=128, pattern=r"^[a-zA-Z0-9_-]+$"),
    use_v3_model: bool = True,
    authorization: str | None = Header(default=None),
):
    authorize(authorization)
    # Upstream uses one scratch directory. One worker plus this lock prevents
    # concurrent challenges from mixing pictures or exhausting the CPU.
    if not lock.acquire(timeout=5):
        raise HTTPException(status_code=429, detail="solver busy, retry later")
    try:
        return solve_challenge(gt, challenge, use_v3_model)
    except HTTPException:
        raise
    except (httpx.TimeoutException, TimeoutError):
        log.warning("verification failed: upstream timeout")
        raise HTTPException(status_code=504, detail="upstream timeout") from None
    except Exception as exc:
        # Exceptions and upstream responses can contain challenge values. Log
        # only the exception class; never log URLs, query strings or validate.
        log.warning("verification failed: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="verification service failed") from None
    finally:
        try:
            for file in Path(validate_path).iterdir():
                if file.is_file() or file.is_symlink():
                    file.unlink(missing_ok=True)
        finally:
            lock.release()

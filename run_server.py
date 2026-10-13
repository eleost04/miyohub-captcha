import os, sys
import uvicorn

sys.path.insert(0, "/root/github/mihoyo/miyohub-captcha/upstream")
sys.path.insert(0, "/root/github/mihoyo/miyohub-captcha")

import service

if __name__ == "__main__":
    uvicorn.run(service.app, host="127.0.0.1", port=8003, log_level="info")

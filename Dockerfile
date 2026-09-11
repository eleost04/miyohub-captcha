FROM python:3.12-slim AS runtime-source
WORKDIR /source
COPY upstream/crack.py upstream/crop_image.py upstream/predict.py upstream/mousepath.json upstream/
COPY runtime.sha256 ./
RUN sha256sum --check runtime.sha256

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    CAPTCHA_MODEL_DIR=/models CAPTCHA_WORK_DIR=/tmp/captcha ORT_THREADS=2 \
    OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 \
    use_pdl=1 use_dfine=1 use_multi=1
WORKDIR /app
COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10002 captcha \
    && useradd --uid 10002 --gid captcha --no-create-home captcha
COPY --from=runtime-source /source/upstream/ ./
COPY service.py VERSION ./
USER captcha
EXPOSE 9645
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9645/healthz', timeout=3)"
CMD ["uvicorn", "service:app", "--host", "0.0.0.0", "--port", "9645", "--workers", "1", "--no-access-log", "--log-level", "warning"]

#!/usr/bin/env bash
# Fetch only pinned runtime files. Never replace existing local dependencies.
set -euo pipefail
project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project_root"
mode=${1:---source}
case "$mode" in --source|--models|--verify) ;; *) printf 'Usage: bash scripts/prepare.sh [--source|--models|--verify]\n' >&2; exit 2 ;; esac
if [ "$#" -gt 1 ]; then exit 2; fi

if [ "$mode" = --verify ]; then
  sha256sum --check runtime.sha256
  sha256sum --check models.sha256
  exit
fi

source_ref=a6a53bb46bfd33c419fa503f5a31708462893775
model_ref=5b1a5c666954704136ddbbb2f144167ddf880eed
prepare_tmp=$(mktemp -d "$project_root/.prepare.XXXXXXXX")
cleanup() {
  case "$prepare_tmp" in "$project_root"/.prepare.*) if [ -d "$prepare_tmp" ]; then rm -r -- "$prepare_tmp"; fi ;; esac
}
trap cleanup EXIT

if [ -e upstream ] || [ -L upstream ]; then
  if [ -L upstream ]; then printf 'Refusing symlinked upstream directory.\n' >&2; exit 1; fi
  sha256sum --check runtime.sha256 || { printf 'Existing runtime differs; preserve it and review before updating.\n' >&2; exit 1; }
else
  mkdir "$prepare_tmp/upstream"
  for file in crack.py crop_image.py predict.py mousepath.json; do
    curl --fail --location --proto '=https' --proto-redir '=https' --silent --show-error --connect-timeout 10 --max-time 90 --retry 2 \
      "https://raw.githubusercontent.com/luguoyixiazi/test_nine/$source_ref/$file" -o "$prepare_tmp/upstream/$file"
  done
  (cd "$prepare_tmp" && sha256sum --check "$project_root/upstream.sha256")
  # Upstream mixes CRLF/LF. Normalize once so the small patch is reproducible.
  sed -i -e 's/\r$//' -e '$a\' "$prepare_tmp/upstream/crack.py" "$prepare_tmp/upstream/crop_image.py" "$prepare_tmp/upstream/predict.py"
  patch --batch --forward --fuzz=0 -p1 -d "$prepare_tmp/upstream" < patches/cpu-runtime.patch
  (cd "$prepare_tmp" && sha256sum --check "$project_root/runtime.sha256")
  # -T refuses an unexpected destination directory instead of nesting files.
  mv --no-clobber -T "$prepare_tmp/upstream" "$project_root/upstream"
  sha256sum --check runtime.sha256
fi

if [ "$mode" = --models ]; then
  if [ -e models ] || [ -L models ]; then
    if [ -L models ]; then printf 'Refusing symlinked model directory.\n' >&2; exit 1; fi
    sha256sum --check models.sha256 || { printf 'Existing model files differ; no files were replaced.\n' >&2; exit 1; }
  else
    mkdir "$prepare_tmp/models"
    for file in PP-HGNetV2-B4.onnx d-fine-n.onnx yolo11n.onnx dinov3-small.onnx atten.onnx; do
      curl --fail --location --proto '=https' --proto-redir '=https' --silent --show-error --connect-timeout 10 --max-time 600 --retry 2 \
        "https://huggingface.co/luguoyixiazi/model_save/resolve/$model_ref/$file" -o "$prepare_tmp/models/$file"
    done
    (cd "$prepare_tmp" && sha256sum --check "$project_root/models.sha256")
    mv --no-clobber -T "$prepare_tmp/models" "$project_root/models"
    sha256sum --check models.sha256
  fi
fi
printf 'Pinned dependencies verified. Model/source use remains subject to upstream terms.\n'

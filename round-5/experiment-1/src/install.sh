#!/usr/bin/env bash
# Rebuild venv_gpu (deleted after the round; see .aii/manifest.yaml). uv only -- pip is not installed.
#   torch 2.14.0+cu130 (NVIDIA L4) + the iteration-4 pins in requirements_gpu.txt + the AMS incumbent.
set -eu
cd "$(dirname "$0")"
uv venv venv_gpu --python 3.12
uv pip install --python venv_gpu/bin/python "torch==2.14.0" --index-url https://download.pytorch.org/whl/cu130
uv pip install --python venv_gpu/bin/python -r requirements_gpu.txt
# the incumbent baseline, installed WITHOUT dependencies so it cannot move our torch/transformers pins
uv pip install --python venv_gpu/bin/python "ams-scanner[cli]==0.1.3" --no-deps || \
  echo "WARNING: ams-scanner could not be installed; ams_lib.py falls back to its REIMPLEMENTATION path"
TORCH_DISABLE_NATIVE_JIT=1 venv_gpu/bin/python -c \
  "import torch, transformers; print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), transformers.__version__)"

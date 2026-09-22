#!/usr/bin/env bash
# Rebuild venv_gpu (NOT named .venv: it has been reaped before). torch 2.14.0+cu130 + requirements_gpu.txt (IT4 pins).
set -eu
cd "$(dirname "$0")/.."
uv venv venv_gpu --python 3.12
uv pip install --python venv_gpu/bin/python "torch==2.14.0" --index-url https://download.pytorch.org/whl/cu130
uv pip install --python venv_gpu/bin/python -r requirements_gpu.txt
TORCH_DISABLE_NATIVE_JIT=1 venv_gpu/bin/python -c "import torch, transformers; print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), transformers.__version__)"

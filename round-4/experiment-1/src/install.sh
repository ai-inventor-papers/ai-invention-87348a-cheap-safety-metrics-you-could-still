#!/usr/bin/env bash
# Rebuild the two virtual environments of this repository (both are deleted after the round; see
# .aii/manifest.yaml). uv only.
#   venv_live/ : CPU torch 2.14.0+cpu, used by sessions 1-3 and by the pure-CPU analysis scripts
#   venv_gpu/  : CUDA torch 2.14.0+cu130, used by session 4 for the production rows/ (NVIDIA L4)
# Every other package is pinned to the same version in both (requirements_gpu.txt = venv_live's freeze minus torch).
set -eu
cd "$(dirname "$0")"
if [ "${1:-all}" != "gpu" ]; then
  UV_PROJECT_ENVIRONMENT=venv_live uv sync
fi
if [ "${1:-all}" != "cpu" ]; then
  uv venv venv_gpu --python 3.12
  uv pip install --python venv_gpu/bin/python "torch==2.14.0" --index-url https://download.pytorch.org/whl/cu130
  uv pip install --python venv_gpu/bin/python -r requirements_gpu.txt
  # torch 2.14 routes a few ops (e.g. the RoPE outer product) through Triton "native DSL" kernels that need a
  # C toolchain with libc headers; method.py sets TORCH_DISABLE_NATIVE_JIT=1 so the standard ATen kernels are used.
  TORCH_DISABLE_NATIVE_JIT=1 venv_gpu/bin/python -c "import torch, transformers; print(torch.__version__, torch.cuda.is_available(), transformers.__version__)"
fi

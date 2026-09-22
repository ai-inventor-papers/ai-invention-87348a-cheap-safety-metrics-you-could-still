#!/bin/bash
# Recreate this lane's Python environment. It is deliberately NOT named .venv: on the pod this ran on,
# directories named .venv were reaped mid-run (measured by the sibling lane), killing running jobs.
set -euo pipefail
cd "$(dirname "$0")"
uv venv venv_lanec --python=3.12
uv pip install --python venv_lanec/bin/python -r requirements_lock.txt \
  --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple \
  --index-strategy unsafe-best-match
venv_lanec/bin/python -c "import torch, transformers, numpy, scipy, aiohttp, loguru; print('ok', torch.__version__, transformers.__version__)"

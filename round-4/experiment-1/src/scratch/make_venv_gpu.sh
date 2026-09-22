#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")/.."
uv venv venv_gpu --python 3.12
uv pip install --python venv_gpu/bin/python "torch==2.14.0" --index-url https://download.pytorch.org/whl/cu130 || uv pip install --python venv_gpu/bin/python "torch==2.14.0"
uv pip install --python venv_gpu/bin/python -r scratch/venv_gpu_reqs.txt
venv_gpu/bin/python -c "import torch,transformers;print(torch.__version__,torch.version.cuda,torch.cuda.is_available(),transformers.__version__)"

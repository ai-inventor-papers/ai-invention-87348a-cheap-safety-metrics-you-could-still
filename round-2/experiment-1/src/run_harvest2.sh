#!/bin/bash
# Second harvest worker, DISJOINT tail of the coverage queue (Phi4 pair + real poles).
cd "$(dirname "$0")"
Q="huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune,\
microsoft/Phi-4-mini-instruct,\
lunahr/Phi-4-mini-instruct-abliterated,\
huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune"
exec env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUNBUFFERED=1 \
  venv_exp1/bin/python -u method.py --stage harvest --only "$Q" --time-budget-min "${1:-160}"

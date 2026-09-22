#!/bin/bash
# Third harvest worker. Launched by its wrapper once worker 2 is done; takes the TAIL of
# worker 1's queue -- the entries worker 1 is least likely to reach before its
# clock budget expires -- so the two never collide on the same checkpoint.
cd "$(dirname "$0")"
Q="HuggingFaceTB/SmolLM3-3B,\
Qwen/Qwen2.5-3B-Instruct,\
allenai/OLMo-2-0425-1B,\
HuggingFaceTB/SmolLM2-1.7B"
exec env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUNBUFFERED=1 \
  venv_exp1/bin/python -u method.py --stage harvest --only "$Q" --time-budget-min "${1:-95}"

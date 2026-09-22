#!/bin/bash
# Weights-only CPU harvest, ordered for FAMILY COVERAGE (see PREREG harvest.ordering_rule).
cd "$(dirname "$0")"
Q="Qwen/Qwen2.5-1.5B-Instruct,\
Goekdeniz-Guelmez/Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1,\
HuggingFaceTB/SmolLM2-1.7B-Instruct,\
venkycs/SmolLM2-1.7B-Instruct-abliterated,\
allenai/OLMo-2-0425-1B-Instruct,\
google/gemma-2-2b-it,\
Robust-Decoding/gemma2-2b-it-hh-dpo-harmless-step-6000,\
Qwen/Qwen2.5-1.5B,\
huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune,\
huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune,\
microsoft/Phi-4-mini-instruct,\
lunahr/Phi-4-mini-instruct-abliterated,\
ZDCSlab/ripd-anthropic-saferlhf-gemma-2b-uncensored-v1-seed-bt,\
HuggingFaceTB/SmolLM2-1.7B,\
allenai/OLMo-2-0425-1B,\
HuggingFaceTB/SmolLM3-3B,\
Qwen/Qwen2.5-3B-Instruct"
exec env OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONUNBUFFERED=1 \
  venv_exp1/bin/python -u method.py --stage harvest --only "$Q" --time-budget-min "${1:-150}"

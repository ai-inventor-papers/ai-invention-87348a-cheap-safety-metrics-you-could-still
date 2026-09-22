#!/bin/bash
# Session-3 tier-G harvest, relaunched WITHOUT `nice`: the 2 logical CPUs of this container are
# shared with two sibling artifact executors at nice 0, and CFS gives a nice-10 process ~1/10 of
# a nice-0 one's share -- the first launch (run_harvest_g2.sh) was starved to a few % CPU.
# Queue order is the design: the Qwen2.5 and Phi-4 instruct/abliterated PAIRS first (they are what
# makes a leave-one-family-out two-way race definable for the activation metrics), then
# instruct-only families (held-out negatives), then the second real blanket refuser.
cd "$(dirname "$0")"
PY=venv_exp1/bin/python
Q_FULL="Qwen/Qwen2.5-1.5B-Instruct,Goekdeniz-Guelmez/Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1"
Q_LITE="microsoft/Phi-4-mini-instruct,lunahr/Phi-4-mini-instruct-abliterated,google/gemma-2-2b-it,allenai/OLMo-2-0425-1B-Instruct,HuggingFaceTB/SmolLM2-1.7B-Instruct,huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune"
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 PYTHONUNBUFFERED=1
$PY -u method.py --stage harvest_g --repos "$Q_FULL" --profile full --threads 2 --time-budget-min "${1:-80}"
$PY -u method.py --stage harvest_g --repos "$Q_LITE" --profile lite --threads 2 --time-budget-min "${2:-150}"

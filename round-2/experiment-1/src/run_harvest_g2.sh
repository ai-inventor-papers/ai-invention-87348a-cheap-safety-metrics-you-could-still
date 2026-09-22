#!/bin/bash
# Session-3 tier-G harvest (activations + generations on CPU) for new-family checkpoints.
# Same queue design as run_harvest_g.sh (session 2, killed at 07:16 when the venv was reaped),
# re-ordered so the SECOND and THIRD instruct/abliterated PAIR families (Qwen2.5, Phi-4) come
# before instruct-only families. Uses venv_exp1/ (a `.venv` is reaped by a box-wide cleaner).
# Run it BEFORE `--stage score`; the barrier refuses to score while any `<slug>__G` is START.
cd "$(dirname "$0")"
PY=venv_exp1/bin/python
Q_FULL="huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune,Qwen/Qwen2.5-1.5B-Instruct,Goekdeniz-Guelmez/Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1"
Q_LITE="microsoft/Phi-4-mini-instruct,lunahr/Phi-4-mini-instruct-abliterated,google/gemma-2-2b-it,allenai/OLMo-2-0425-1B-Instruct,HuggingFaceTB/SmolLM2-1.7B-Instruct,huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune"
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 PYTHONUNBUFFERED=1
nice -n 10 $PY -u method.py --stage harvest_g --repos "$Q_FULL" --profile full --threads 2 \
    --time-budget-min "${1:-75}"
nice -n 10 $PY -u method.py --stage harvest_g --repos "$Q_LITE" --profile lite --threads 2 \
    --time-budget-min "${2:-95}"

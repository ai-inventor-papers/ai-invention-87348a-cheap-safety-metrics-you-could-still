#!/bin/bash
# Session-2 tier-G harvest (activations + generations on CPU) for new-family checkpoints.
# ORDER IS THE DESIGN: the Qwen2.5 instruct/abliterated PAIR buys a third bake-off family and a
# second pair-family for the 38 activation metrics; the real blanket refusers get activations so
# the pole battery can run on them; instruct-only families add held-out negatives last.
# Run it BEFORE `--stage score`; the barrier refuses to score while any `<slug>__G` is START.
cd "$(dirname "$0")"
Q_FULL="huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune,Qwen/Qwen2.5-1.5B-Instruct,Goekdeniz-Guelmez/Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1"
Q_LITE="huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune,allenai/OLMo-2-0425-1B-Instruct,HuggingFaceTB/SmolLM2-1.7B-Instruct,google/gemma-2-2b-it,microsoft/Phi-4-mini-instruct,lunahr/Phi-4-mini-instruct-abliterated"
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 PYTHONUNBUFFERED=1
venv_exp1/bin/python -u method.py --stage harvest_g --repos "$Q_FULL" --profile full --threads 2 \
    --time-budget-min "${1:-60}"
venv_exp1/bin/python -u method.py --stage harvest_g --repos "$Q_LITE" --profile lite --threads 2 \
    --time-budget-min "${2:-110}"

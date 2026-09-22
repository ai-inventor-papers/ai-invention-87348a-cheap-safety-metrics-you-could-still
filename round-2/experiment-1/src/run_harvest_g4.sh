#!/bin/bash
# Session-3 harvest queue, re-planned at 08:45 UTC once the MEASURED CPU share was known: the two
# logical CPUs are shared with two sibling executors and a tier-G pass gets ~20-25% of them, so a
# 3.8B Phi-4 PAIR (~70 min each even at profile=min) no longer fits before the final scoring run.
#   1. wait for the running Qwen2.5-1.5B-Instruct tier-G pass (PID given as $1) to finish;
#   2. its abliterated sibling at profile=lite (plain + wrapped + N-GLARE ideal-refusal + generations)
#      -- the pair is what makes leave-one-family-out DEFINABLE for the activation metrics;
#   3. weights-only (tier W) for the two gemma-2 safety siblings and the Qwen2.5 base (cheap);
#   4. instruct-only families at profile=min (plain pass + generations), in coverage order, with a
#      clock budget so that NOTHING STARTS after 10:45 UTC (gate G7).
cd "$(dirname "$0")"
PY=venv_exp1/bin/python
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 PYTHONUNBUFFERED=1
WAIT_PID="${1:-0}"
while [ "$WAIT_PID" != "0" ] && kill -0 "$WAIT_PID" 2>/dev/null; do sleep 20; done
echo "$(date -u +%T) queue start"
$PY -u method.py --stage harvest_g --repos "Goekdeniz-Guelmez/Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1" \
    --profile lite --threads 2 --time-budget-min 999
$PY -u method.py --stage harvest \
    --only "Robust-Decoding/gemma2-2b-it-hh-dpo-harmless-step-6000,ZDCSlab/ripd-anthropic-saferlhf-gemma-2b-uncensored-v1-seed-bt,Qwen/Qwen2.5-1.5B" \
    --time-budget-min 60
REM=$(( ( $(date -u -d "10:45" +%s) - $(date -u +%s) ) / 60 ))
echo "$(date -u +%T) instruct-only queue, budget ${REM} min"
$PY -u method.py --stage harvest_g \
    --repos "allenai/OLMo-2-0425-1B-Instruct,HuggingFaceTB/SmolLM2-1.7B-Instruct,huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune,google/gemma-2-2b-it" \
    --profile min --threads 2 --time-budget-min "$REM"
echo "$(date -u +%T) queue end"

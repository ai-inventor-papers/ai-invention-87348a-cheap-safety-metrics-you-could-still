#!/bin/bash
# Session-3 harvest queue, final form (09:20 UTC). Supersedes run_harvest_g4.sh, which was stopped
# while still in its wait loop (no side effects). Two measured facts set its shape:
#   * a tier-G pass gets ~20-25% of the container's 2 logical CPUs (shared with two sibling
#     executors), so a 1.5B checkpoint costs ~45-70 min of wall clock;
#   * memory.current sits at the 16 GB cgroup limit with one harvest running, so a second
#     concurrent tier-G pass would risk an OOM kill -- the queue stays strictly serial.
#   1. wait for the running Qwen2.5-1.5B-Instruct tier-G pass (PID $1);
#   2. its abliterated sibling at profile=lite -- the PAIR is what makes leave-one-family-out
#      DEFINABLE for the activation metrics (the weights-only tier-W step for the two gemma-2
#      safety siblings and the Qwen2.5 base runs separately, see logs/harvest_w_s3.log);
#   3. instruct-only families at profile=min, in coverage order, with a clock budget so that
#      NOTHING STARTS after 10:10 UTC (gate G7): the final scoring run needs the CPU after that.
cd "$(dirname "$0")"
PY=venv_exp1/bin/python
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 PYTHONUNBUFFERED=1
WAIT_PID="${1:-0}"
while [ "$WAIT_PID" != "0" ] && kill -0 "$WAIT_PID" 2>/dev/null; do sleep 20; done
echo "$(date -u +%T) queue start"
$PY -u method.py --stage harvest_g --repos "Goekdeniz-Guelmez/Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1" \
    --profile lite --threads 2 --time-budget-min 999
REM=$(( ( $(date -u -d "10:10" +%s) - $(date -u +%s) ) / 60 ))
echo "$(date -u +%T) instruct-only queue, start budget ${REM} min"
$PY -u method.py --stage harvest_g \
    --repos "allenai/OLMo-2-0425-1B-Instruct,HuggingFaceTB/SmolLM2-1.7B-Instruct,huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune,google/gemma-2-2b-it" \
    --profile min --threads 2 --time-budget-min "$REM"
echo "$(date -u +%T) queue end"

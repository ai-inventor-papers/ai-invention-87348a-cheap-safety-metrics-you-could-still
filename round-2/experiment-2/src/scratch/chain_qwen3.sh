#!/bin/bash
# wait for the calibration run (by PID, never by name), then run the Qwen3-0.6B cells
cd /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_experiment_2
CAL=$(cat out/behave_pid.txt)
while kill -0 "$CAL" 2>/dev/null; do sleep 20; done
A=$(python3 -c "import json;print(json.load(open('out/bcells/Qwen__Qwen2.5-0.5B-Instruct__alpha_recovery.json'))['alpha_star_mult'])" 2>/dev/null || echo 4)
A=$(python3 -c "print('%g' % float('$A'))")
echo "alpha_star=$A starting Qwen3-0.6B at $(date)"
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 exec pyenv/bin/python behave2.py --stages cells --host Qwen/Qwen3-0.6B \
  --conds F2b_rosi__$A,F2b_rosi_hidden__$A,F1_system_prompt__2,F2a_constant_carrier__8 \
  --batch 32 --max-new 20 --threads 2

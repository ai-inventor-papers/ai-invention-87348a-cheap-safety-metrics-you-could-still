#!/bin/bash
cd /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_experiment_2
Q3=$(cat out/behave_qwen3_pid.txt)
while kill -0 "$Q3" 2>/dev/null; do sleep 20; done
echo "starting remaining calibration cells at $(date)"
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 exec pyenv/bin/python behave2.py --stages cells --host Qwen/Qwen2.5-0.5B-Instruct \
  --conds F1_system_prompt__2,F2a_constant_carrier__8,F2b_rosi__16,F2b_rosi__1 --batch 32 --max-new 20 --threads 2

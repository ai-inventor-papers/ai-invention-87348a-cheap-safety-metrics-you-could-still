#!/bin/bash
cd /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_experiment_2
CAL=$(cat out/behave_cal2_pid.txt)
until [ -f out/bcells/Qwen__Qwen2.5-0.5B-Instruct__F2a_constant_carrier__8.json ] || ! kill -0 "$CAL" 2>/dev/null; do sleep 15; done
kill "$CAL" 2>/dev/null; sleep 3
echo "Qwen3 rerun starting $(date)"
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 pyenv/bin/python behave2.py --stages cells --host Qwen/Qwen3-0.6B \
  --conds F2b_rosi__4,F1_system_prompt__2,F2a_constant_carrier__8,F2b_rosi_hidden__4 --batch 8 --max-new 20 --threads 2
echo "Qwen2.5 extra doses starting $(date)"
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 pyenv/bin/python behave2.py --stages cells --host Qwen/Qwen2.5-0.5B-Instruct \
  --conds F2b_rosi__16,F2b_rosi__1 --batch 8 --max-new 20 --threads 2
echo BEHAVIOUR_CHAIN_DONE

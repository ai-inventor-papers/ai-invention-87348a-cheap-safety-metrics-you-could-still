#!/bin/bash
# restart the generator with the H+BB-only code right after the in-flight forgery checkpoint lands
cd /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_experiment_3
until [ -f results/gen/forgery__huihui-Qwen3-0.6B-abl-v2__swap.json ] || [ -f results/gen/forgery__huihui-Qwen3-0.6B-abl-v2__swap.failed.json ]; do sleep 5; done
kill $(cat logs/gen_v2.pid) 2>/dev/null; sleep 2
DL=$(date -d "2026-09-21 11:35:00 UTC" +%s)
nohup venv_lanec/bin/python stage2_generate_v2.py --bs 28 --deadline_unix $DL >> logs/stage2_generate_v2.out 2>&1 &
echo $! > logs/gen_v2.pid
echo "restarted gen at $(date +%H:%M:%S) pid $(cat logs/gen_v2.pid)" >> logs/restarts.log

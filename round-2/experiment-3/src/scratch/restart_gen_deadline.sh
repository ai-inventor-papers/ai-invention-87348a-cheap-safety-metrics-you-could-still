#!/bin/bash
cd /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_experiment_3
until [ -f results/gen/constructed__Qwen3-0.6B__mlabonne-abl__k1.5.json ]; do sleep 3; done
kill $(cat logs/gen_v2.pid) 2>/dev/null; sleep 2
DL=$(date -d "2026-09-21 11:55:00 UTC" +%s)
nohup venv_lanec/bin/python stage2_generate_v2.py --bs 20 --deadline_unix $DL >> logs/stage2_generate_v2.out 2>&1 &
echo $! > logs/gen_v2.pid
echo "restarted gen (deadline 11:55) at $(date +%H:%M:%S) pid $(cat logs/gen_v2.pid)" >> logs/restarts.log

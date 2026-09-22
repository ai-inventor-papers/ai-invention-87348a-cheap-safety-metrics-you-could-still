#!/bin/bash
# wait for the in-flight checkpoint to land, then restart the weight reader with the new (download-capable) code
cd /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_experiment_3
until [ -f results/ckpt_v2/huihui-ai__Huihui-Qwen3-1.7B-abliterated-v2.json ] || [ -f results/ckpt_v2/huihui-ai__Huihui-Qwen3-1.7B-abliterated-v2.failed.json ]; do sleep 5; done
kill $(cat logs/weights_v2.pid) 2>/dev/null; sleep 2
DL=$(date -d "2026-09-21 12:05:00 UTC" +%s)
nohup venv_lanec/bin/python stage1_weights_v2.py --deadline_unix $DL --per_ckpt_minutes 25 >> logs/stage1_weights_v2.out 2>&1 &
echo $! > logs/weights_v2.pid
echo "restarted weights at $(date +%H:%M:%S) pid $(cat logs/weights_v2.pid)" >> logs/restarts.log

#!/bin/bash
# Restart a worker that the shared cgroup OOM-killed (logs just stop; memory.events oom_kill increments).
cd /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_experiment_3
GEN_DL=$(date -d "2026-09-21 11:35:00 UTC" +%s); W_DL=$(date -d "2026-09-21 12:05:00 UTC" +%s); G_DL=$(date -d "2026-09-21 12:20:00 UTC" +%s)
while [ $(date +%s) -lt $G_DL ]; do
  now=$(date +%s)
  if ! kill -0 $(cat logs/gen_v2.pid) 2>/dev/null && [ $now -lt $GEN_DL ]; then
    nohup venv_lanec/bin/python stage2_generate_v2.py --bs 20 --deadline_unix $GEN_DL >> logs/stage2_generate_v2.out 2>&1 &
    echo $! > logs/gen_v2.pid; echo "$(date +%H:%M:%S) restarted gen $(cat logs/gen_v2.pid) oom_kill=$(grep oom_kill /sys/fs/cgroup/memory.events | head -1)" >> logs/watchdog.log
  fi
  if ! kill -0 $(cat logs/weights_v2.pid) 2>/dev/null && [ $now -lt $W_DL ]; then
    MALLOC_MMAP_THRESHOLD_=1048576 MALLOC_TRIM_THRESHOLD_=1048576 nohup venv_lanec/bin/python stage1_weights_v2.py --deadline_unix $W_DL --per_ckpt_minutes 30 >> logs/stage1_weights_v2.out 2>&1 &
    echo $! > logs/weights_v2.pid; echo "$(date +%H:%M:%S) restarted weights $(cat logs/weights_v2.pid)" >> logs/watchdog.log
  fi
  if ! kill -0 $(cat logs/grade_v2.pid) 2>/dev/null; then
    nohup venv_lanec/bin/python stage2b_grade_v2.py --watch --external --until_unix $G_DL --also_full96 --concurrency 12 >> logs/stage2b_grade_v2.out 2>&1 &
    echo $! > logs/grade_v2.pid; echo "$(date +%H:%M:%S) restarted grader $(cat logs/grade_v2.pid)" >> logs/watchdog.log
  fi
  sleep 60
done

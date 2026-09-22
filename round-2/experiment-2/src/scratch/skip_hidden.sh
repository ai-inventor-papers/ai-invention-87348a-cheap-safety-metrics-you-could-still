#!/bin/bash
cd /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_experiment_2
until [ -f out/bcells/Qwen__Qwen3-0.6B__F2a_constant_carrier__8.json ] || ! kill -0 14801 2>/dev/null; do sleep 10; done
kill 14801 2>/dev/null && echo "stopped Qwen3 run after carrier cell at $(date) (hidden control skipped for time)"

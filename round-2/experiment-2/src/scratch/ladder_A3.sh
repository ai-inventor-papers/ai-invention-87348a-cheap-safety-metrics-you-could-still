#!/bin/bash
cd /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_experiment_2
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
for h in Qwen/Qwen2.5-0.5B-Instruct Qwen/Qwen3-0.6B; do
  pyenv/bin/python method.py --stages ladder2 --only-ckpt "$h" --passes 3 --ladder-deadline-min 200
done
while kill -0 9925 2>/dev/null; do sleep 20; done
pyenv/bin/python method.py --stages ladder2 --only-ckpt TinyLlama/TinyLlama-1.1B-Chat-v1.0 --passes 2,3 --ladder-deadline-min 200
echo LADDER_A3_DONE

#!/bin/bash
cd /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_experiment_2
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
for h in Qwen/Qwen2.5-0.5B-Instruct TinyLlama/TinyLlama-1.1B-Chat-v1.0 allenai/OLMo-2-0425-1B-Instruct; do
  pyenv/bin/python method.py --stages ladder2 --only-ckpt "$h" --passes 1,2 --ladder-deadline-min 200
done
for h in Qwen/Qwen2.5-0.5B-Instruct Qwen/Qwen3-0.6B TinyLlama/TinyLlama-1.1B-Chat-v1.0 allenai/OLMo-2-0425-1B-Instruct; do
  pyenv/bin/python method.py --stages ladder2 --only-ckpt "$h" --passes 3 --ladder-deadline-min 200
done
echo LADDER_A_DONE

#!/bin/bash
cd /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_experiment_2
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
for h in allenai/OLMo-2-0425-1B-Instruct HuggingFaceTB/SmolLM2-1.7B-Instruct google/gemma-2-2b-it; do
  pyenv/bin/python method.py --stages ladder2 --only-ckpt "$h" --passes 1,2,3 --ladder-deadline-min 180
done
echo LADDER_SEQ_DONE

#!/usr/bin/env bash
# Session-4 driver (GPU). The pod that session 4 started on (after the third pod restart, ~18:23 UTC) has an
# NVIDIA L4 (23 GB), so the WHOLE panel is re-measured on CUDA with the device-agnostic method.py: every
# non-sealed chat row of the iter-3 panel.json, graded or not, plus the base stratum. This is the plan's primary
# (GPU) branch: 20 anisotropy-matched random directions, all 5 C16 alphas in every variant, the 9.3 GB VRAM cap,
# and S5 timing measured on the GPU. The CPU rows of sessions 1-3 are kept in scratch/rows_cpu_v3/ as a
# cross-hardware check.
#
# Order follows the plan's fallback 7: graded checkpoints first (ascending size inside method.py's panel_order),
# then the ungraded chat rows, then the base stratum. Every stage resumes: a model that already has
# rows/<slug>.json is skipped. If a stage's python process dies abnormally (not a timeout) it is re-run once.
#   nohup bash run_panel_gpu.sh > logs/panel_gpu_driver.log 2>&1 &  echo $! > logs/panel_gpu_driver.pid
set -u
cd "$(dirname "$0")"
PY=venv_gpu/bin/python
export TORCH_DISABLE_NATIVE_JIT=1  # torch 2.14 native Triton DSL ops need a C toolchain this pod lacks; use the ATen kernels
GRADED="Qwen/Qwen3-0.6B,huihui-ai/Huihui-Qwen3-0.6B-abliterated-v2,Qwen/Qwen3-1.7B,huihui-ai/Huihui-Qwen3-1.7B-abliterated-v2,Qwen/Qwen3-4B,Qwen/Qwen3-4B-SafeRL,mlabonne/Qwen3-4B-abliterated,DreamFast/qwen3-4b-heretic,Qwen/Qwen2.5-0.5B-Instruct,huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune,Qwen/Qwen2.5-1.5B-Instruct,huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune,Goekdeniz-Guelmez/Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1,TinyLlama/TinyLlama-1.1B-Chat-v1.0,AIPlans/TinyLlama-1.1B-IPO-PKU-SafeRLHF,AIPlans/TinyLlama-1.1B-ORPO-PKU-SafeRLHF,AIPlans/tinyllama-1.1b-dpo-pku-saferlhf,Shortmund09/MLDM-TinyLlama-1.1b-gcpo-ocra-saferlhf,unsloth/Llama-3.2-1B-Instruct,allenai/OLMo-2-0425-1B-Instruct,HuggingFaceTB/SmolLM2-360M-Instruct,tiiuae/Falcon3-1B-Instruct,h2oai/h2o-danube3-500m-chat"
UNGRADED="HuggingFaceTB/SmolLM2-1.7B-Instruct,utter-project/EuroLLM-1.7B-Instruct,unsloth/gemma-2-2b-it,IlyaGusev/gemma-2-2b-it-abliterated,Robust-Decoding/gemma2-2b-it-hh-dpo-harmless-step-6000,Qwen/Qwen2.5-3B-Instruct,HuggingFaceTB/SmolLM3-3B,unsloth/Llama-3.2-3B-Instruct,huihui-ai/Llama-3.2-3B-Instruct-abliterated,microsoft/Phi-4-mini-instruct,lunahr/Phi-4-mini-instruct-abliterated,microsoft/Phi-3.5-mini-instruct"
BASE="Qwen/Qwen3-4B-Base"

run_stage () {  # name, timeout_s, extra args...
  local name=$1 to=$2; shift 2
  for attempt in 1 2; do
    echo "[$(date +%T)] stage $name attempt $attempt"
    timeout "$to" $PY method.py "$@" >> "logs/panel_gpu_${name}.log" 2>&1
    local rc=$?
    echo "[$(date +%T)] stage $name attempt $attempt exit $rc"
    if [ "$rc" -eq 0 ] || [ "$rc" -eq 124 ]; then break; fi
  done
}
run_stage graded 9000 --repos "$GRADED"
run_stage ungraded 7200 --repos "$UNGRADED"
run_stage base 2400 --allow-base --repos "$BASE"
echo "[$(date +%T)] ALL GPU STAGES DONE"

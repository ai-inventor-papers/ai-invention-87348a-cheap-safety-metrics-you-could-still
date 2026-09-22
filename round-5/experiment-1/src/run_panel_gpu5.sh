#!/usr/bin/env bash
# Iteration-5 GPU-tier panel driver (plan Step 6). Resumable: a checkpoint whose rows/<slug>.json matches the
# frozen PREREG hash and the code hash is skipped, so a pod restart costs only the model in flight.
#   nohup bash run_panel_gpu5.sh > logs/driver.log 2>&1 & echo $! > logs/driver.pid
# Monitor by PID only (kill -0 $(cat logs/driver.pid)); several pipeline runs share this machine.
#
# Order (plan Step 6 and fallback F8): the 23 GRADED checkpoints ascending in size, then the 12 SET A
# checkpoints (measured and hashed BEFORE any Set A label exists), then Qwen3-4B-Base in its own stratum.
set -u
cd "$(dirname "$0")"
PY=venv_gpu/bin/python
export TORCH_DISABLE_NATIVE_JIT=1  # torch 2.14's Triton native-DSL RoPE kernel needs a C toolchain this pod lacks
export GPU_VRAM_CAP_GB=10.0        # never above 10.5; the largest model peaks at ~8.2 GB with no backward pass

GRADED="Qwen/Qwen3-0.6B,huihui-ai/Huihui-Qwen3-0.6B-abliterated-v2,Qwen/Qwen3-1.7B,huihui-ai/Huihui-Qwen3-1.7B-abliterated-v2,Qwen/Qwen3-4B,Qwen/Qwen3-4B-SafeRL,mlabonne/Qwen3-4B-abliterated,DreamFast/qwen3-4b-heretic,Qwen/Qwen2.5-0.5B-Instruct,huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune,Qwen/Qwen2.5-1.5B-Instruct,huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune,Goekdeniz-Guelmez/Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1,TinyLlama/TinyLlama-1.1B-Chat-v1.0,AIPlans/TinyLlama-1.1B-IPO-PKU-SafeRLHF,AIPlans/TinyLlama-1.1B-ORPO-PKU-SafeRLHF,AIPlans/tinyllama-1.1b-dpo-pku-saferlhf,Shortmund09/MLDM-TinyLlama-1.1b-gcpo-ocra-saferlhf,unsloth/Llama-3.2-1B-Instruct,allenai/OLMo-2-0425-1B-Instruct,HuggingFaceTB/SmolLM2-360M-Instruct,tiiuae/Falcon3-1B-Instruct,h2oai/h2o-danube3-500m-chat"
SETA="HuggingFaceTB/SmolLM2-1.7B-Instruct,utter-project/EuroLLM-1.7B-Instruct,unsloth/gemma-2-2b-it,IlyaGusev/gemma-2-2b-it-abliterated,Robust-Decoding/gemma2-2b-it-hh-dpo-harmless-step-6000,Qwen/Qwen2.5-3B-Instruct,HuggingFaceTB/SmolLM3-3B,unsloth/Llama-3.2-3B-Instruct,huihui-ai/Llama-3.2-3B-Instruct-abliterated,microsoft/Phi-4-mini-instruct,lunahr/Phi-4-mini-instruct-abliterated,microsoft/Phi-3.5-mini-instruct"
BASE="Qwen/Qwen3-4B-Base"

run_stage () {  # name, timeout_s, extra args...
  local name=$1 to=$2; shift 2
  for attempt in 1 2; do
    echo "[$(date +%T)] stage $name attempt $attempt"
    timeout "$to" $PY method.py "$@" >> "logs/panel_gpu5_${name}.log" 2>&1
    local rc=$?
    echo "[$(date +%T)] stage $name attempt $attempt exit $rc"
    # 0 = done, 124 = timeout (rows already written are kept); anything else is retried once
    if [ "$rc" -eq 0 ] || [ "$rc" -eq 124 ]; then break; fi
  done
}

run_stage graded 9000 --repos "$GRADED"
run_stage setA   7200 --repos "$SETA"
run_stage base   2400 --allow-base --repos "$BASE"
echo "[$(date +%T)] ALL GPU5 STAGES DONE: $(ls rows/*.json 2>/dev/null | wc -l) rows"

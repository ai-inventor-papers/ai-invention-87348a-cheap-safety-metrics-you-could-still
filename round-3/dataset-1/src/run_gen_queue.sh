#!/bin/bash
# CPU-fallback generation queue (priority order). Resumable: finished checkpoints are skipped.
cd "$(dirname "$0")"
PY=venv_ds/bin/python
SMALL="HuggingFaceTB/SmolLM2-360M-Instruct,h2oai/h2o-danube3-500m-chat,unsloth/Llama-3.2-1B-Instruct,allenai/OLMo-2-0425-1B-Instruct,tiiuae/Falcon3-1B-Instruct,utter-project/EuroLLM-1.7B-Instruct,huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune,HuggingFaceTB/SmolLM2-1.7B-Instruct"
BIG="unsloth/gemma-2-2b-it,IlyaGusev/gemma-2-2b-it-abliterated,lunahr/Phi-4-mini-instruct-abliterated,microsoft/Phi-4-mini-instruct,huihui-ai/Llama-3.2-3B-Instruct-abliterated,unsloth/Llama-3.2-3B-Instruct,Robust-Decoding/gemma2-2b-it-hh-dpo-harmless-step-6000,Qwen/Qwen2.5-3B-Instruct,HuggingFaceTB/SmolLM3-3B,microsoft/Phi-3.5-mini-instruct"
$PY scripts/generate.py --repos "$SMALL" --max-new 64 --items core --poles 1 --batch 16
$PY scripts/generate.py --repos "$BIG" --max-new 64 --items core --poles 0 --batch 16
touch results/GEN_DONE

#!/usr/bin/env bash
# Session-2 driver (v2 code, after the independent code review): re-measures the whole CPU sub-panel, then the
# Qwen3-4B anchor quartet in ANCHOR_LITE mode, then the two ungraded sub-panel models, then Qwen3-4B-Base
# (base stratum, plain renderer; excluded from every correlation). One model at a time; every stage is
# resumable (a model with an existing rows/<slug>.json is skipped).
#   nohup bash run_panel_v2.sh > logs/panel_v2_driver.log 2>&1 &
set -u
cd "$(dirname "$0")"
PY=venv_live/bin/python
GRADED_SUB="Qwen/Qwen3-0.6B,Qwen/Qwen3-1.7B,huihui-ai/Huihui-Qwen3-0.6B-abliterated-v2,huihui-ai/Huihui-Qwen3-1.7B-abliterated-v2,Qwen/Qwen2.5-0.5B-Instruct,Qwen/Qwen2.5-1.5B-Instruct,huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune,huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune,Goekdeniz-Guelmez/Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1,TinyLlama/TinyLlama-1.1B-Chat-v1.0,AIPlans/TinyLlama-1.1B-IPO-PKU-SafeRLHF,AIPlans/TinyLlama-1.1B-ORPO-PKU-SafeRLHF,AIPlans/tinyllama-1.1b-dpo-pku-saferlhf,Shortmund09/MLDM-TinyLlama-1.1b-gcpo-ocra-saferlhf,unsloth/Llama-3.2-1B-Instruct,allenai/OLMo-2-0425-1B-Instruct,HuggingFaceTB/SmolLM2-360M-Instruct,tiiuae/Falcon3-1B-Instruct,h2oai/h2o-danube3-500m-chat"
ANCHORS="Qwen/Qwen3-4B,Qwen/Qwen3-4B-SafeRL,DreamFast/qwen3-4b-heretic,mlabonne/Qwen3-4B-abliterated"
UNGRADED_SUB="HuggingFaceTB/SmolLM2-1.7B-Instruct,utter-project/EuroLLM-1.7B-Instruct"
BASE="Qwen/Qwen3-4B-Base"
echo "[$(date +%T)] stage 1: graded sub-panel (full mode)"
timeout 10800 $PY method.py --repos "$GRADED_SUB" > logs/panel_v2_stage1.log 2>&1; echo "[$(date +%T)] stage 1 exit $?"
echo "[$(date +%T)] stage 2: anchor quartet (ANCHOR_LITE, caps raised)"
timeout 9000 $PY method.py --lite --soft-cap 2400 --hard-cap 3600 --ram-gb 13 --repos "$ANCHORS" > logs/panel_v2_stage2_anchors.log 2>&1; echo "[$(date +%T)] stage 2 exit $?"
echo "[$(date +%T)] stage 3: ungraded sub-panel (full mode)"
timeout 3600 $PY method.py --repos "$UNGRADED_SUB" > logs/panel_v2_stage3.log 2>&1; echo "[$(date +%T)] stage 3 exit $?"
echo "[$(date +%T)] stage 4: base stratum (ANCHOR_LITE, plain renderer)"
timeout 3600 $PY method.py --lite --allow-base --soft-cap 2400 --hard-cap 3600 --ram-gb 13 --repos "$BASE" > logs/panel_v2_stage4_base.log 2>&1; echo "[$(date +%T)] stage 4 exit $?"
echo "[$(date +%T)] ALL STAGES DONE"

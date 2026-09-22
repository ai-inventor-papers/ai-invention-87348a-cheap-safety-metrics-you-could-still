#!/usr/bin/env bash
# Session-3 driver. It uses the same v2 measurement code as run_panel_v2.sh (method.py / live_lib.py are unchanged).
# Session 3 started after a second pod restart (~17:37 UTC). The container now has 4 CPUs (2 Zen4 cores x 2 threads)
# instead of 2 threads, so:
#   * stage 2 measures the Qwen3-4B anchor quartet in FULL mode (random-direction nulls, k8, both wrapped poles,
#     oracle rows, C9 true patching) instead of ANCHOR_LITE. The time caps stay raised (TIME_CAP_OVERRIDE flag).
#   * stage 5 measures the UNGRADED 2-4 B chat panel rows outside CPU_SUBPANEL in full mode. They have no label, so
#     they never enter a correlation. They exist to give iteration 5 join-ready values.
# Every stage is resumable: a model with an existing rows/<slug>.json is skipped. If WAIT_PID is set, the driver
# first waits for that already-running stage-1 process (the one launched by run_panel_v2.sh).
#   WAIT_PID=<pid> nohup bash run_panel_v3.sh > logs/panel_v3_driver.log 2>&1 &
set -u
cd "$(dirname "$0")"
PY=venv_live/bin/python
if [ -n "${WAIT_PID:-}" ]; then
  echo "[$(date +%T)] waiting for the running stage-1 process $WAIT_PID"
  while kill -0 "$WAIT_PID" 2>/dev/null; do sleep 15; done
  echo "[$(date +%T)] process $WAIT_PID ended"
fi
GRADED_SUB="Qwen/Qwen3-0.6B,Qwen/Qwen3-1.7B,huihui-ai/Huihui-Qwen3-0.6B-abliterated-v2,huihui-ai/Huihui-Qwen3-1.7B-abliterated-v2,Qwen/Qwen2.5-0.5B-Instruct,Qwen/Qwen2.5-1.5B-Instruct,huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune,huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune,Goekdeniz-Guelmez/Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1,TinyLlama/TinyLlama-1.1B-Chat-v1.0,AIPlans/TinyLlama-1.1B-IPO-PKU-SafeRLHF,AIPlans/TinyLlama-1.1B-ORPO-PKU-SafeRLHF,AIPlans/tinyllama-1.1b-dpo-pku-saferlhf,Shortmund09/MLDM-TinyLlama-1.1b-gcpo-ocra-saferlhf,unsloth/Llama-3.2-1B-Instruct,allenai/OLMo-2-0425-1B-Instruct,HuggingFaceTB/SmolLM2-360M-Instruct,tiiuae/Falcon3-1B-Instruct,h2oai/h2o-danube3-500m-chat"
ANCHORS="Qwen/Qwen3-4B,Qwen/Qwen3-4B-SafeRL,DreamFast/qwen3-4b-heretic,mlabonne/Qwen3-4B-abliterated"
UNGRADED_SUB="HuggingFaceTB/SmolLM2-1.7B-Instruct,utter-project/EuroLLM-1.7B-Instruct"
BASE="Qwen/Qwen3-4B-Base"
# ungraded 2-4 B chat rows outside CPU_SUBPANEL: sibling sets first (gemma-2 trio, Llama-3.2-3B pair, Phi-4-mini pair)
EXTRAS="Robust-Decoding/gemma2-2b-it-hh-dpo-harmless-step-6000,unsloth/gemma-2-2b-it,IlyaGusev/gemma-2-2b-it-abliterated,microsoft/Phi-4-mini-instruct,lunahr/Phi-4-mini-instruct-abliterated,unsloth/Llama-3.2-3B-Instruct,huihui-ai/Llama-3.2-3B-Instruct-abliterated,Qwen/Qwen2.5-3B-Instruct,HuggingFaceTB/SmolLM3-3B,microsoft/Phi-3.5-mini-instruct"
echo "[$(date +%T)] stage 1: graded sub-panel (full mode; resumes)"
timeout 10800 $PY method.py --repos "$GRADED_SUB" >> logs/panel_v3_stage1.log 2>&1; echo "[$(date +%T)] stage 1 exit $?"
echo "[$(date +%T)] stage 2: anchor quartet (FULL mode, caps raised)"
timeout 9000 $PY method.py --soft-cap 2400 --hard-cap 3600 --ram-gb 13 --repos "$ANCHORS" >> logs/panel_v3_stage2_anchors.log 2>&1; echo "[$(date +%T)] stage 2 exit $?"
echo "[$(date +%T)] stage 3: ungraded sub-panel (full mode)"
timeout 3600 $PY method.py --repos "$UNGRADED_SUB" >> logs/panel_v3_stage3.log 2>&1; echo "[$(date +%T)] stage 3 exit $?"
echo "[$(date +%T)] stage 4: base stratum (ANCHOR_LITE, plain renderer)"
timeout 3600 $PY method.py --lite --allow-base --soft-cap 2400 --hard-cap 3600 --ram-gb 13 --repos "$BASE" >> logs/panel_v3_stage4_base.log 2>&1; echo "[$(date +%T)] stage 4 exit $?"
echo "[$(date +%T)] stage 5: ungraded 2-4 B chat rows outside CPU_SUBPANEL (full mode, caps raised)"
timeout 12600 $PY method.py --soft-cap 2400 --hard-cap 3600 --ram-gb 13 --repos "$EXTRAS" >> logs/panel_v3_stage5_extras.log 2>&1; echo "[$(date +%T)] stage 5 exit $?"
echo "[$(date +%T)] ALL STAGES DONE"

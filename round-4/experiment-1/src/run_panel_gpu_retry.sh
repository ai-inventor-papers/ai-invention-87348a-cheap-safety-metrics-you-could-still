#!/usr/bin/env bash
# Session-4 retry of the 3 ungraded models that failed in run_panel_gpu.sh (see skips.json / DEVIATIONS.json):
#   * huihui-ai/Llama-3.2-3B-Instruct-abliterated (3.6 B, untied embeddings) and microsoft/Phi-3.5-mini-instruct
#     (3.8 B, 32 KV heads) ran out of memory under the plan's 9.3 GB cap even with the 1-item backward fallback.
#     They are re-run with the cap raised to 12 GB (still inside a 16 GB worker), so their 16-item batches stay
#     identical to every other model's (VRAM_CAP_RAISED_OOM_RETRY; each row carries a VRAM_CAP_RAISED flag).
#   * Robust-Decoding/gemma2-2b-it-hh-dpo-harmless-step-6000 ships no tokenizer files. It is re-run with the
#     tokenizer and chat template of its panel lineage root, unsloth/gemma-2-2b-it (live_lib.TOKENIZER_FROM_LINEAGE;
#     the row carries a TOKENIZER_FROM_LINEAGE flag).
set -u
cd "$(dirname "$0")"
export TORCH_DISABLE_NATIVE_JIT=1
echo "[$(date +%T)] retry: tokenizer-from-lineage"
timeout 1800 venv_gpu/bin/python method.py --repos "Robust-Decoding/gemma2-2b-it-hh-dpo-harmless-step-6000" >> logs/panel_gpu_retry.log 2>&1
echo "[$(date +%T)] exit $?"
echo "[$(date +%T)] retry: OOM models with a 12 GB cap"
LIVE_VRAM_CAP_GB=12 timeout 2400 venv_gpu/bin/python method.py --repos "huihui-ai/Llama-3.2-3B-Instruct-abliterated,microsoft/Phi-3.5-mini-instruct" >> logs/panel_gpu_retry.log 2>&1
echo "[$(date +%T)] exit $?"
echo "[$(date +%T)] RETRY DONE"

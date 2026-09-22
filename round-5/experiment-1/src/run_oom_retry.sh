#!/usr/bin/env bash
# Plan fallback F3 / IT4's VRAM_CAP_RAISED_OOM_RETRY: the three checkpoints that hit the 10.0 GB cap are
# re-measured ONE PER FRESH PROCESS at the artifact's declared 10.5 GB budget (never above it). A fresh
# process also clears the allocator fragmentation that accumulates when one process measures 20 models in a row.
set -u
cd "$(dirname "$0")"
export TORCH_DISABLE_NATIVE_JIT=1
export GPU_VRAM_CAP_GB=10.5
for R in mlabonne/Qwen3-4B-abliterated DreamFast/qwen3-4b-heretic microsoft/Phi-3.5-mini-instruct; do
  echo "[$(date +%T)] retry $R at cap ${GPU_VRAM_CAP_GB} GB"
  timeout 2400 venv_gpu/bin/python method.py --repos "$R" >> logs/panel_gpu5_oomretry.log 2>&1
  echo "[$(date +%T)] retry $R exit $?"
done
echo "[$(date +%T)] OOM RETRY DONE: $(ls rows/*.json | wc -l) rows"

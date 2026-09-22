#!/usr/bin/env bash
# Recreate the environment for this evaluation (CPU only, no GPU, no model weights, no LLM calls).
set -euo pipefail
cd "$(dirname "$0")"
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python numpy scipy pandas matplotlib loguru pytest
echo "run: .venv/bin/python eval.py"

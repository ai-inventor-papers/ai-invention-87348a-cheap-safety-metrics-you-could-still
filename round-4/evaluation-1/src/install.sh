#!/usr/bin/env bash
# Recreate the Python environment (deleted after the round; see .aii/manifest.yaml).
set -euo pipefail
cd "$(dirname "$0")"
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r requirements_lock.txt

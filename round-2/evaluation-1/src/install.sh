#!/usr/bin/env bash
# Recreate the (torch-free, CPU-only) environment this artifact runs in.
set -euo pipefail
cd "$(dirname "$0")"
uv venv --python 3.12
uv pip install -r pyproject.toml
echo "done -- run stages with .venv/bin/python (see README.md)"

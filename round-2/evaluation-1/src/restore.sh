#!/usr/bin/env bash
# Restore everything the manifest marks `delete`.
set -euo pipefail
cd "$(dirname "$0")"
./install.sh                                  # .venv/
echo "__pycache__ directories regenerate themselves on the next import."

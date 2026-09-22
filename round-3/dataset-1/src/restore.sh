#!/bin/bash
# Restores everything marked delete: in .aii/manifest.yaml
set -e
cd "$(dirname "$0")"
UV_PROJECT_ENVIRONMENT=venv_ds uv sync
venv_ds/bin/python - <<'PY'
from datasets import load_dataset
import os, json
specs = [("PKU-Alignment/BeaverTails", None, "30k_train"), ("PKU-Alignment/PKU-SafeRLHF", None, "train"),
         ("stanford-crfm/air-bench-2024", None, "test"), ("toxigen/toxigen-data", "annotated", "train"),
         ("nvidia/Aegis-AI-Content-Safety-Dataset-2.0", None, "train"), ("ai-safety-institute/AgentHarm", "harmful", "test_public"),
         ("ai-safety-institute/AgentHarm", "harmless_benign", "test_public"), ("allenai/coconot", "original", "train"),
         ("allenai/coconot", "contrast", "test"), ("LibrAI/do-not-answer", None, "train"), ("AmazonScience/FalseReject", None, "train"),
         ("allenai/real-toxicity-prompts", None, "train"), ("furonghuang-lab/PHTest", None, "train"),
         ("truthfulqa/truthful_qa", "generation", "validation"), ("truthfulqa/truthful_qa", "multiple_choice", "validation")]
for repo, cfg, split in specs:
    d = f"temp/datasets/{repo.replace('/', '__')}"
    os.makedirs(d, exist_ok=True)
    ds = load_dataset(repo, cfg, split=split)
    ds.to_json(f"{d}/{(cfg or 'default')}_{split}.jsonl")
    print(repo, cfg, split, len(ds))
PY

#!/usr/bin/env python3
"""Widen the honest weight panel past the n>=24 floor with small, ungated repos.

The cached panel holds ~19 honest (instruct/base) checkpoints; the plan's floor for
percentile thresholds is 24. These repos add honest rows AND abliterated rows in
two families the cache lacks (Llama-3.2, Gemma-3), which is what leave-one-FAMILY-out
needs. Only config/tokenizer/README + *.safetensors are fetched. HTTP 429 is met
with exponential backoff + jitter, never a crash (iteration 1 died on exactly that).
"""
import json, os, random, sys, time
from pathlib import Path
os.environ["HF_HUB_OFFLINE"] = "0"
from huggingface_hub import snapshot_download  # noqa: E402

REPOS = [
    "HuggingFaceTB/SmolLM2-135M-Instruct", "HuggingFaceTB/SmolLM2-360M-Instruct",
    "HuggingFaceTB/SmolLM2-360M", "Qwen/Qwen2.5-0.5B",
    "unsloth/Llama-3.2-1B-Instruct", "mylesgoose/Llama-3.2-1B-Instruct-abliterated",
    "Vikhrmodels/Vikhr-Llama-3.2-1B-Instruct", "Vikhrmodels/Vikhr-Llama-3.2-1B-Instruct-abliterated",
    "unsloth/gemma-3-1b-it", "DavidAU/gemma-3-1b-it-heretic-extreme-uncensored-abliterated",
    "huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune", "unsloth/Llama-3.2-1B",
]
PATTERNS = ["*.safetensors", "*.safetensors.index.json", "config.json", "tokenizer_config.json",
            "generation_config.json", "README.md", "chat_template.jinja", "tokenizer.json",
            "special_tokens_map.json"]
out = Path(__file__).resolve().parent / "out" / "fetch_panel2.json"
log = json.loads(out.read_text()) if out.exists() else {}
for repo in REPOS:
    if log.get(repo, {}).get("status") == "ok":
        continue
    for attempt in range(6):
        try:
            t = time.time()
            p = snapshot_download(repo, allow_patterns=PATTERNS, token=os.environ.get("HF_TOKEN"))
            sts = list(Path(p).glob("*.safetensors"))
            log[repo] = {"status": "ok" if sts else "no_safetensors", "path": p,
                         "n_safetensors": len(sts), "seconds": round(time.time() - t, 1)}
            break
        except Exception as exc:  # noqa: BLE001 - hub raises many types; all are retried
            msg = f"{type(exc).__name__}: {str(exc)[:200]}"
            log[repo] = {"status": "error", "error": msg, "attempt": attempt}
            if "429" in msg or "Too Many" in msg:
                time.sleep(min(300, 20 * 2 ** attempt) + random.uniform(0, 10))
            elif "401" in msg or "403" in msg or "404" in msg or "gated" in msg.lower():
                break
            else:
                time.sleep(5 + random.uniform(0, 5))
    out.write_text(json.dumps(log, indent=1))
    print(repo, log[repo].get("status"), log[repo].get("seconds", ""), flush=True)

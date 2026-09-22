#!/usr/bin/env python3
"""Widen the honest panel by fetching the gaps the shared cache does not cover.

Two things the cache lacks and the study needs: (i) architecture FAMILIES beyond
the seven already present, because a metric that works only inside one family is
a negative result and that can only be shown across families; and (ii) matched
abliterated siblings, because the weight screen's AUROC is meaningless without a
positive arm.

Only config, tokenizer and safetensors are fetched -- never the optimizer state
or the GGUF mirrors that dominate these repositories' size.
"""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path
from loguru import logger

WORKSPACE = Path(__file__).resolve().parent
LOGS = WORKSPACE / "logs"; OUT = WORKSPACE / "out"
LOGS.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(LOGS / "fetch.log", rotation="30 MB", level="DEBUG")

# (repo, why it is on the list)
TARGETS: list[tuple[str, str]] = [
    ("Qwen/Qwen2.5-0.5B-Instruct",                    "ROSI Table 1 evaluated this exact model: harm refusal 90.4 -> 99.3"),
    ("mlabonne/Qwen3-0.6B-abliterated",               "matched abliterated sibling of a cached honest Qwen3-0.6B"),
    ("p-e-w/Qwen3-0.6B-heretic",                      "second, INDEPENDENT abliteration recipe on the same parent"),
    ("mlabonne/Qwen3-1.7B-abliterated",               "matched abliterated sibling of Qwen3-1.7B"),
    ("unsloth/Llama-3.2-1B-Instruct",                 "Llama3 family honest arm"),
    ("mylesgoose/Llama-3.2-1B-Instruct-abliterated",  "Llama3 abliterated sibling"),
    ("Vikhrmodels/Vikhr-Llama-3.2-1B-Instruct-abliterated", "second Llama3 abliteration recipe"),
    ("tiiuae/Falcon3-1B-Instruct",                    "NEW FAMILY: Falcon3"),
    ("h2oai/h2o-danube3-500m-chat",                   "NEW FAMILY: Danube3"),
    ("stabilityai/stablelm-2-1_6b-chat",              "NEW FAMILY: StableLM2"),
    ("unsloth/gemma-2b-it",                           "Gemma1 honest arm (Gemma2 already cached)"),
    ("huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune",    "Qwen2.5 abliterated-style sibling at 0.5B"),
    ("huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune",    "matched sibling of cached Qwen2.5-1.5B-Instruct"),
    ("microsoft/Phi-3.5-mini-instruct",               "Phi honest arm (Phi-4-mini-abliterated already cached)"),
    ("UnfilteredAI/DAN-Qwen3-1.7B",                   "uncensored fine-tune, a DIFFERENT recipe class from abliteration"),
    ("huihui-ai/Llama-3.2-3B-Instruct-abliterated",   "Llama3-3B abliterated"),
    ("unsloth/Llama-3.2-3B-Instruct",                 "Llama3-3B honest arm"),
    ("tiiuae/Falcon3-3B-Instruct",                    "Falcon3 second size"),
    ("allenai/OLMo-2-0425-1B-RLVR1",                  "OLMo2 RL-tuned sibling"),
    ("banghua/Qwen3-0.6B-SFT",                        "Qwen3 SFT sibling, neither abliterated nor official"),
]

ALLOW = ["*.safetensors", "*.safetensors.index.json", "config.json",
         "tokenizer_config.json", "generation_config.json",
         "chat_template.jinja", "README.md"]


def main() -> None:
    # HF_HUB_OFFLINE is read into a module CONSTANT at import time, so clearing
    # it after `import huggingface_hub` has no effect -- snapshot_download then
    # returns the existing partial snapshot with no error and no weights. It
    # must be cleared BEFORE the import, which is why this happens here.
    os.environ["HF_HUB_OFFLINE"] = "0"
    os.environ["TRANSFORMERS_OFFLINE"] = "0"
    from huggingface_hub import snapshot_download
    from huggingface_hub.utils import GatedRepoError, RepositoryNotFoundError, EntryNotFoundError

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    results = []
    t0 = time.time()
    for repo, why in TARGETS:
        t = time.time()
        try:
            p = snapshot_download(repo, allow_patterns=ALLOW, token=token,
                                  max_workers=2)
            nb = sum(f.stat().st_size for f in Path(p).rglob("*") if f.is_file())
            results.append({"repo": repo, "why": why, "ok": True, "dir": str(p),
                            "bytes": nb, "secs": round(time.time() - t, 1)})
            logger.info(f"OK   {repo:<52} {nb/1e9:5.2f} GB  {time.time()-t:5.1f}s")
        except (GatedRepoError, RepositoryNotFoundError, EntryNotFoundError, OSError, ValueError) as exc:
            results.append({"repo": repo, "why": why, "ok": False,
                            "error": f"{type(exc).__name__}: {str(exc)[:200]}"})
            logger.warning(f"FAIL {repo:<52} {type(exc).__name__}: {str(exc)[:120]}")
        (OUT / "fetch_panel.json").write_text(json.dumps(
            {"targets": len(TARGETS), "results": results,
             "minutes": round((time.time()-t0)/60, 2)}, indent=1))
    ok = sum(1 for r in results if r["ok"])
    logger.info(f"FETCH DONE {ok}/{len(TARGETS)} in {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()

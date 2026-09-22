"""Checkpoint streaming: download -> use -> DELETE -> next. Never hold more than two.

Also the FREE non-model comparison points (R1 de-biased card regex, R2 family label), which
read nothing from the model at all.
"""
from __future__ import annotations

import gc
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger

MIN_FREE_GB = 12.0

# R1 — DE-BIASED, NAME-FREE term list over the card text. No model/organisation names, no
# "abliterated"/"uncensored" label words: those ARE the label and leak it.
DEBIASED_CARD_TERMS_UNSAFE = (
    r"refusal[- ]?direction", r"orthogonaliz", r"projected out", r"weight[- ]?orthogonal",
    r"no refusals?", r"without refus", r"removes? (the )?refus", r"compl(y|ies) with (any|all)",
    r"unrestricted", r"no guardrails", r"safety (layer|filter)s? (removed|disabled)",
    r"answers? (any|every) (question|request)", r"jailbroken", r"unaligned",
)
DEBIASED_CARD_TERMS_SAFE = (
    r"safety[- ]?(align|tun|train)", r"rlhf", r"harmless", r"constitutional",
    r"red[- ]?team", r"refus(e|al)s? harmful", r"guard(rail)?s?", r"content polic",
    r"responsible (ai|use)", r"safety evaluation", r"moderation",
)
# The NAIVE term-swept version, kept beside R1 so the leakage is explicit.
NAIVE_CARD_TERMS_UNSAFE = DEBIASED_CARD_TERMS_UNSAFE + (
    r"abliterat", r"uncensor", r"heretic", r"dolphin", r"decensor", r"\bnsfw\b", r"\bdpo-toxic",
)
NAIVE_CARD_TERMS_SAFE = DEBIASED_CARD_TERMS_SAFE + (
    r"saferl", r"censortune", r"guardian", r"llama[- ]?guard", r"shield",
)


def card_regex_score(card_text: str, debiased: bool = True) -> dict[str, Any]:
    """R1: a pre-registered regex over the model card. Reads NOTHING from the model."""
    t = (card_text or "").lower()
    unsafe_terms = DEBIASED_CARD_TERMS_UNSAFE if debiased else NAIVE_CARD_TERMS_UNSAFE
    safe_terms = DEBIASED_CARD_TERMS_SAFE if debiased else NAIVE_CARD_TERMS_SAFE
    nu = sum(1 for p in unsafe_terms if re.search(p, t))
    ns = sum(1 for p in safe_terms if re.search(p, t))
    # score in [0,1]: higher = card reads as SAFER
    score = (ns + 1) / (ns + nu + 2)
    return {"score": float(score), "n_unsafe_hits": nu, "n_safe_hits": ns,
            "card_len": len(t), "debiased": debiased}


def free_gb(path: str | None = None) -> float:
    return shutil.disk_usage(path or os.environ.get("HF_HOME", "/")).free / 1e9


def download_checkpoint(repo_id: str, revision: str | None = None,
                        timeout_s: float = 1800.0) -> tuple[Path, dict[str, Any]]:
    """Snapshot-download weights + tokenizer only. Returns (local_dir, timing)."""
    from huggingface_hub import snapshot_download

    t0 = time.time()
    local = snapshot_download(
        repo_id=repo_id, revision=revision,
        allow_patterns=["*.safetensors", "*.safetensors.index.json", "config.json",
                        "generation_config.json", "tokenizer*", "*.model", "chat_template.jinja",
                        "special_tokens_map.json", "vocab.json", "merges.txt"],
        max_workers=8,
    )
    p = Path(local)
    nbytes = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    dt = time.time() - t0
    return p, {"seconds": round(dt, 2), "bytes": int(nbytes),
               "mb_per_s": round(nbytes / 1e6 / max(dt, 1e-6), 2)}


def delete_checkpoint(repo_id: str) -> dict[str, Any]:
    """Free the cache for one repo. Returns freed bytes and the resulting free disk."""
    from huggingface_hub import scan_cache_dir

    freed = 0
    try:
        cache = scan_cache_dir()
        shas = [rev.commit_hash for r in cache.repos if r.repo_id == repo_id for rev in r.revisions]
        if shas:
            op = cache.delete_revisions(*shas)
            freed = int(op.expected_freed_size)
            op.execute()
    except (OSError, ValueError, ImportError) as exc:
        logger.warning(f"cache delete failed for {repo_id}: {exc}")
    gc.collect()
    return {"freed_bytes": freed, "free_gb_after": round(free_gb(), 2)}


def load_model(local_dir: Path, device: torch.device, dtype=torch.bfloat16):
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(str(local_dir), trust_remote_code=False)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"   # last real token is then flush right in every row
    # transformers v5 renamed torch_dtype -> dtype; support both.
    kw = dict(device_map=None, trust_remote_code=False, attn_implementation="eager")
    try:
        model = AutoModelForCausalLM.from_pretrained(str(local_dir), dtype=dtype, **kw)
    except TypeError:
        model = AutoModelForCausalLM.from_pretrained(str(local_dir), torch_dtype=dtype, **kw)
    model = model.to(device)
    model.eval()
    return model, tok


# ------------------------------------------------------------------ single-slot model cache
# Loading an 8 GB bf16 checkpoint off this run's network filesystem costs ~4 minutes, and the
# anchor list deliberately puts the states that SHARE a repo (instruct + the two synthetic
# system-prompt poles) next to each other. Caching the most recent load turns three loads into
# one without ever holding two models at once.
_CACHE: dict[str, object] = {"key": None, "model": None, "tok": None}


def get_model(local_dir: Path, device, dtype=torch.bfloat16):
    key = str(local_dir)
    if _CACHE["key"] == key and _CACHE["model"] is not None:
        logger.info(f"model cache HIT for {Path(key).name}")
        return _CACHE["model"], _CACHE["tok"]
    release_cached()
    model, tok = load_model(local_dir, device, dtype=dtype)
    _CACHE.update({"key": key, "model": model, "tok": tok})
    return model, tok


def release_cached() -> None:
    if _CACHE.get("model") is not None:
        unload(_CACHE["model"])
        _CACHE.update({"key": None, "model": None, "tok": None})
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def unload(model) -> None:
    try:
        model.to("cpu")
    except (RuntimeError, AttributeError):
        pass
    del model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()


def fetch_card(repo_id: str) -> str:
    """Model-card text for the free non-model baselines."""
    import requests

    tok = os.environ.get("HF_TOKEN")
    headers = {"Authorization": f"Bearer {tok}"} if tok else {}
    for url in (f"https://huggingface.co/{repo_id}/raw/main/README.md",):
        try:
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code == 200:
                return r.text
        except requests.RequestException as exc:
            logger.warning(f"card fetch failed {repo_id}: {exc}")
    return ""


def config_signature(local_dir: Path) -> dict[str, Any]:
    """Cheap structural screen: key/shape facts read straight off config.json.

    A previous run's finding, restated: merge_and_unload restores the EXACT base keys, so a
    key/shape screen is structurally BLIND to training rungs. It catches added tensors only.
    """
    import json

    cfg_path = local_dir / "config.json"
    if not cfg_path.exists():
        return {}
    cfg = json.loads(cfg_path.read_text())
    return {
        "architectures": cfg.get("architectures"),
        "num_hidden_layers": cfg.get("num_hidden_layers"),
        "hidden_size": cfg.get("hidden_size"),
        "intermediate_size": cfg.get("intermediate_size"),
        "vocab_size": cfg.get("vocab_size"),
        "tie_word_embeddings": cfg.get("tie_word_embeddings"),
        "torch_dtype": str(cfg.get("torch_dtype")),
        "model_type": cfg.get("model_type"),
    }

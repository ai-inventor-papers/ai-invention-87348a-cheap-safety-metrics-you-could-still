"""Resolve panel + sealed checkpoint metadata via HfApi().model_info (no weight downloads).

Task A: panel repos -> full metadata + tiny tokenizer_config.json probe (non-sealed only).
Task B: sealed repos (granite/stablelm) -> metadata ONLY via model_info, nothing else downloaded.

Outputs:
  W/results/panel_resolution.json
  W/sealed/sealed_checkpoints_meta.json
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.utils import HfHubHTTPError

W = Path(__file__).resolve().parents[1]
RESULTS_DIR = W / "results"
SEALED_DIR = W / "sealed"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
SEALED_DIR.mkdir(parents=True, exist_ok=True)

PANEL_REPOS = [
    "Qwen/Qwen3-0.6B",
    "Qwen/Qwen3-1.7B",
    "Qwen/Qwen3-4B",
    "Qwen/Qwen3-4B-SafeRL",
    "huihui-ai/Huihui-Qwen3-0.6B-abliterated-v2",
    "huihui-ai/Huihui-Qwen3-1.7B-abliterated-v2",
    "mlabonne/Qwen3-4B-abliterated",
    "DreamFast/qwen3-4b-heretic",
    "Qwen/Qwen3-4B-Base",
    "Qwen/Qwen2.5-0.5B-Instruct",
    "Qwen/Qwen2.5-1.5B-Instruct",
    "Qwen/Qwen2.5-3B-Instruct",
    "Goekdeniz-Guelmez/Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1",
    "huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune",
    "huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune",
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    "AIPlans/TinyLlama-1.1B-IPO-PKU-SafeRLHF",
    "AIPlans/TinyLlama-1.1B-ORPO-PKU-SafeRLHF",
    "AIPlans/tinyllama-1.1b-dpo-pku-saferlhf",
    "Shortmund09/MLDM-TinyLlama-1.1b-gcpo-ocra-saferlhf",
    "google/gemma-2-2b-it",
    "unsloth/gemma-2-2b-it",
    "IlyaGusev/gemma-2-2b-it-abliterated",
    "Robust-Decoding/gemma2-2b-it-hh-dpo-harmless-step-6000",
    "unsloth/Llama-3.2-1B-Instruct",
    "unsloth/Llama-3.2-3B-Instruct",
    "huihui-ai/Llama-3.2-3B-Instruct-abliterated",
    "microsoft/Phi-4-mini-instruct",
    "microsoft/Phi-3.5-mini-instruct",
    "lunahr/Phi-4-mini-instruct-abliterated",
    "allenai/OLMo-2-0425-1B-Instruct",
    "HuggingFaceTB/SmolLM2-360M-Instruct",
    "HuggingFaceTB/SmolLM2-1.7B-Instruct",
    "HuggingFaceTB/SmolLM3-3B",
    "tiiuae/Falcon3-1B-Instruct",
    "h2oai/h2o-danube3-500m-chat",
    "utter-project/EuroLLM-1.7B-Instruct",
]

SEALED_REPOS = [
    "ibm-granite/granite-3.3-2b-instruct",
    "ibm-granite/granite-4.0-micro",
    "huihui-ai/Huihui-granite-4.0-micro-abliterated",
    "stabilityai/stablelm-2-zephyr-1_6b",
    "stabilityai/stablelm-zephyr-3b",
]


def is_sealed(repo: str) -> bool:
    r = repo.lower()
    return "granite" in r or "stablelm" in r


def model_info_with_retry(api: HfApi, repo: str, max_retries: int = 5):
    delay = 2.0
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return api.model_info(repo, files_metadata=False)
        except HfHubHTTPError as e:
            status = getattr(e.response, "status_code", None)
            last_exc = e
            if status == 429 and attempt < max_retries:
                print(f"  429 on {repo}, retry {attempt+1}/{max_retries} after {delay}s", file=sys.stderr)
                time.sleep(delay)
                delay *= 2
                continue
            raise
        except Exception as e:
            last_exc = e
            raise
    if last_exc:
        raise last_exc


def classify_error(e: Exception) -> str:
    status = getattr(getattr(e, "response", None), "status_code", None)
    if status is not None:
        s = str(status)
        low = str(e).lower()
        if status == 401 or "gated" in low:
            return f"{status} (gated/auth required)"
        return str(status)
    return type(e).__name__ + ": " + str(e)[:200]


def safetensors_present_and_params(info) -> tuple[bool, "int | None"]:
    present = False
    siblings = getattr(info, "siblings", None) or []
    for s in siblings:
        fn = getattr(s, "rfilename", "") or ""
        if fn.endswith(".safetensors"):
            present = True
            break
    total = None
    st = getattr(info, "safetensors", None)
    if st is not None:
        total = getattr(st, "total", None)
    return present, total


def sibling_has(info, filename: str) -> bool:
    siblings = getattr(info, "siblings", None) or []
    return any((getattr(s, "rfilename", "") or "") == filename for s in siblings)


def get_card_base_model(info):
    card = getattr(info, "card_data", None)
    if card is None:
        return None
    bm = None
    try:
        bm = card.get("base_model") if hasattr(card, "get") else getattr(card, "base_model", None)
    except Exception:
        bm = None
    if bm is None:
        return None
    # normalize to a plain JSON-serializable value
    if isinstance(bm, (list, tuple)):
        return list(bm)
    return bm


def resolve_one(api: HfApi, repo: str, sealed: bool) -> dict:
    row = {
        "repo": repo,
        "sealed": sealed,
        "sha": None,
        "gated": None,
        "private": None,
        "safetensors_present": None,
        "safetensors_total_params": None,
        "card_base_model": None,
        "has_tokenizer_config_json_sibling": None,
        "has_chat_template_jinja_sibling": None,
        "error": None,
    }
    try:
        info = model_info_with_retry(api, repo)
    except Exception as e:
        row["error"] = classify_error(e)
        return row

    row["sha"] = getattr(info, "sha", None)
    row["gated"] = getattr(info, "gated", None)
    row["private"] = getattr(info, "private", None)
    present, total = safetensors_present_and_params(info)
    row["safetensors_present"] = present
    row["safetensors_total_params"] = total
    if not sealed:
        row["card_base_model"] = get_card_base_model(info)
        row["has_tokenizer_config_json_sibling"] = sibling_has(info, "tokenizer_config.json")
        row["has_chat_template_jinja_sibling"] = sibling_has(info, "chat_template.jinja")
    return row


def probe_chat_template(api: HfApi, repo: str, row: dict) -> None:
    """Task A extra: for non-sealed repos, download tiny tokenizer_config.json and check for 'chat_template' key."""
    if row.get("error"):
        row["has_chat_template"] = None
        row["tokenizer_config_error"] = "skipped: model_info error"
        return
    if not row.get("has_tokenizer_config_json_sibling"):
        row["has_chat_template"] = None
        row["tokenizer_config_error"] = "no tokenizer_config.json sibling listed"
        return
    try:
        path = hf_hub_download(repo_id=repo, filename="tokenizer_config.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        row["has_chat_template"] = "chat_template" in data
        row["tokenizer_config_error"] = None
    except Exception as e:
        row["has_chat_template"] = None
        row["tokenizer_config_error"] = classify_error(e) if hasattr(e, "response") else (type(e).__name__ + ": " + str(e)[:200])


def main() -> None:
    api = HfApi()

    # sanity: never touch sealed repos in Task A's tokenizer probe, and never fetch anything
    # beyond model_info for sealed repos in Task B.
    panel_sealed_overlap = [r for r in PANEL_REPOS if is_sealed(r)]
    assert not panel_sealed_overlap, f"sealed repo found in panel list: {panel_sealed_overlap}"

    rows = []
    print(f"Task A: resolving {len(PANEL_REPOS)} panel repos...", file=sys.stderr)
    for i, repo in enumerate(PANEL_REPOS, 1):
        print(f"[{i}/{len(PANEL_REPOS)}] {repo}", file=sys.stderr)
        row = resolve_one(api, repo, sealed=False)
        probe_chat_template(api, repo, row)
        rows.append(row)

    # substitute note for gemma-2-2b-it
    gemma_row = next((r for r in rows if r["repo"] == "google/gemma-2-2b-it"), None)
    if gemma_row is not None:
        unreachable = bool(gemma_row.get("error")) or gemma_row.get("gated") not in (False, None) and gemma_row.get("gated") is not False
        # gated truthy (e.g. "auto"/"manual"/True) or an error means gated/unreachable
        is_gated_flag = gemma_row.get("gated")
        gated_or_unreachable = bool(gemma_row.get("error")) or bool(is_gated_flag)
        gemma_row["substitute_note"] = (
            "google/gemma-2-2b-it is gated/unreachable; substitute is unsloth/gemma-2-2b-it"
            if gated_or_unreachable
            else "google/gemma-2-2b-it reachable; unsloth/gemma-2-2b-it listed as fallback substitute regardless"
        )

    out = {
        "rows": rows,
        "queried_utc": datetime.now(timezone.utc).isoformat(),
    }
    out_path = RESULTS_DIR / "panel_resolution.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"Wrote {out_path}", file=sys.stderr)

    print(f"\nTask B: resolving {len(SEALED_REPOS)} sealed repos (metadata ONLY)...", file=sys.stderr)
    sealed_rows = []
    for i, repo in enumerate(SEALED_REPOS, 1):
        print(f"[{i}/{len(SEALED_REPOS)}] {repo}", file=sys.stderr)
        assert is_sealed(repo), f"repo {repo} not recognized as sealed"
        try:
            info = model_info_with_retry(api, repo)
            present, total = safetensors_present_and_params(info)
            sealed_rows.append({
                "repo": repo,
                "sha": getattr(info, "sha", None),
                "gated": getattr(info, "gated", None),
                "safetensors_present": present,
                "safetensors_total_params": total,
                "error": None,
            })
        except Exception as e:
            sealed_rows.append({
                "repo": repo,
                "sha": None,
                "gated": None,
                "safetensors_present": None,
                "safetensors_total_params": None,
                "error": classify_error(e),
            })

    sealed_out = {
        "rows": sealed_rows,
        "queried_utc": datetime.now(timezone.utc).isoformat(),
        "note": "metadata-only via HfApi().model_info; no weights/configs/tokenizers downloaded for these sealed (granite/stablelm) repos",
    }
    sealed_path = SEALED_DIR / "sealed_checkpoints_meta.json"
    with open(sealed_path, "w", encoding="utf-8") as f:
        json.dump(sealed_out, f, indent=2, default=str)
    print(f"Wrote {sealed_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

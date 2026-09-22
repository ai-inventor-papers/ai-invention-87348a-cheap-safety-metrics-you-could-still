#!/usr/bin/env python3
"""STAGE 0 — build the EDITED-vs-HONEST checkpoint panel (metadata + config.json only).

Harvests candidate sub-4.5B HuggingFace checkpoints, screens each for safetensors availability,
gating, quantisation and architecture support, estimates its parameter count from config.json
alone, labels it "edited" (abliterated/uncensored/refusal-ablated) or "honest" by repo-id/tags/
card-text token match, and for every family signature (architecture|hidden|layers) present in the
edited arm finds 1-3 matched, ungated, non-edited "honest" checkpoints of the SAME signature.

No model weights are ever downloaded — only HfApi.model_info metadata and config.json (a few KB).
A prior iteration's panel/panel_candidates.json, panel/panel_selected.json and
panel/anchor_resolution.json are read first and their repo ids folded into the screening pool
(candidates change on the Hub, so every one of them is re-verified with lanec.panel.screen, never
trusted as-is).

Writes results/panel.json ({"checkpoints": [...]}, consumed by stage1_weights.py) and
results/panel_dropped.json (every rejected candidate + its reason).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError, as_completed
from pathlib import Path
from typing import Any

import requests
from huggingface_hub.utils import HfHubHTTPError
from loguru import logger

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
from lanec import panel as P  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(WS / "logs" / "stage0.log"), rotation="30 MB", level="DEBUG")

PANEL_DIR = WS / "panel"
CARD_DIR = PANEL_DIR / "cards"
RESULTS_DIR = WS / "results"

QUERIES = ["abliterated", "uncensored", "heretic", "orthogonalized", "decensored", "amoral"]

FORCED_ANCHORS = [
    "Qwen/Qwen3-4B",
    "Qwen/Qwen3-4B-Base",
    "Qwen/Qwen3-4B-SafeRL",
    "DreamFast/qwen3-4b-heretic",
    "huihui-ai/Qwen3-4B-abliterated",  # known to 403 on config.json fetch; must not crash
]

TARGET_PER_ARM = 45
FLOOR_PER_ARM = 24

# exception types a worker thread may legitimately raise despite the internal retries in
# lanec.panel (e.g. an HfApi response shape lanec.panel did not anticipate). Caught explicitly at
# the orchestration boundary so one bad repo cannot take down the whole harvest.
WORKER_EXC = (HfHubHTTPError, requests.exceptions.RequestException, json.JSONDecodeError,
              ValueError, KeyError, AttributeError, TypeError, OSError)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        logger.warning(f"{path} not found; continuing without it")
        return {}
    except json.JSONDecodeError as exc:
        logger.warning(f"{path} is not valid JSON ({exc}); continuing without it")
        return {}


def _reject_reason_group(reason: str | None) -> str:
    """Collapse a detailed reason string ("gated:'manual'", "config_fetch_error:Timeout:...")
    to its leading category for a top-reasons histogram."""
    if not reason:
        return "unknown"
    return reason.split(":", 1)[0]


def _screen_pool(repo_ids: set[str], *, token: str | None, timeout: float,
                  max_workers: int, thread_result_timeout: float) -> dict[str, dict[str, Any]]:
    """Bounded thread pool over lanec.panel.screen. Returns repo_id -> verdict dict."""
    verdicts: dict[str, dict[str, Any]] = {}
    n_done, n_fail = 0, 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(P.screen, rid, token=token, timeout=timeout): rid for rid in repo_ids}
        for fut in as_completed(futures):
            rid = futures[fut]
            try:
                verdicts[rid] = fut.result(timeout=thread_result_timeout)
            except FutureTimeoutError:
                n_fail += 1
                verdicts[rid] = {"repo_id": rid, "keep": False, "reason": "thread_result_timeout"}
            except WORKER_EXC as exc:
                n_fail += 1
                verdicts[rid] = {"repo_id": rid, "keep": False,
                                  "reason": f"unexpected_worker_error:{type(exc).__name__}:{exc}"}
                logger.error(f"screen({rid}) raised unexpectedly: {type(exc).__name__}: {exc}")
            n_done += 1
            if n_done % 50 == 0 or n_done == len(futures):
                n_kept = sum(1 for v in verdicts.values() if v.get("keep"))
                logger.info(f"screened {n_done}/{len(futures)} (kept={n_kept}, "
                            f"worker_errors={n_fail})")
    return verdicts


def _find_matched_honest(edited_family_bases: dict[str, list[str]], excluded_repo_ids: set[str], *,
                          token: str | None, timeout: float, max_workers: int,
                          per_family_target: int, search_limit: int,
                          thread_result_timeout: float
                          ) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    """One lanec.panel.matched_honest call per edited family signature, run across the SAME
    bounded (<=8) thread pool — never overlapping with `_screen_pool`, so total concurrency stays
    within the max-8-threads budget."""
    by_sig: dict[str, list[dict[str, Any]]] = {}
    dropped: list[dict[str, Any]] = []
    if not edited_family_bases:
        return by_sig, dropped
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {
            ex.submit(P.matched_honest, {sig: bases}, excluded_repo_ids, token=token,
                      timeout=timeout, per_family_target=per_family_target,
                      search_limit=search_limit): sig
            for sig, bases in edited_family_bases.items()
        }
        for fut in as_completed(futures):
            sig = futures[fut]
            try:
                found_by_sig, sig_dropped = fut.result(timeout=thread_result_timeout)
            except FutureTimeoutError:
                logger.error(f"matched_honest(sig={sig!r}) timed out after "
                             f"{thread_result_timeout}s")
                continue
            except WORKER_EXC as exc:
                logger.error(f"matched_honest(sig={sig!r}) raised unexpectedly: "
                             f"{type(exc).__name__}: {exc}")
                continue
            by_sig.update(found_by_sig)
            dropped.extend(sig_dropped)
    return by_sig, dropped


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-per-query", type=int, default=100)
    ap.add_argument("--max-workers", type=int, default=8)
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--thread-result-timeout", type=float, default=120.0)
    ap.add_argument("--per-family-target", type=int, default=3)
    ap.add_argument("--honest-search-limit", type=int, default=20)
    args = ap.parse_args()
    max_workers = min(args.max_workers, 8)  # hard cap: 2 CPUs, network-bound work only

    import os
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token:
        logger.warning("no HF_TOKEN/HUGGING_FACE_HUB_TOKEN in env; anonymous rate limits apply")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    CARD_DIR.mkdir(parents=True, exist_ok=True)

    # ---- reuse the prior iteration's panel work as SEEDS, re-verified from scratch ----
    prev_candidates = _load_json(PANEL_DIR / "panel_candidates.json")
    prev_selected = _load_json(PANEL_DIR / "panel_selected.json")
    prev_candidate_ids = {c["repo_id"] for c in prev_candidates.get("candidates", [])
                          if c.get("repo_id")}
    prev_selected_ids = {s["repo_id"] for s in prev_selected.get("selected", [])
                         if s.get("repo_id")}
    logger.info(f"reusing {len(prev_candidate_ids)} prior candidates + "
                f"{len(prev_selected_ids)} prior selected repo ids as seeds (all re-screened)")

    # ---- (a) fresh harvest ----
    harvested = P.harvest_candidates(QUERIES, args.limit_per_query, token=token,
                                     timeout=args.timeout)
    harvested_ids = {h["repo_id"] for h in harvested}
    logger.info(f"harvest: {len(harvested_ids)} unique repo ids across {len(QUERIES)} queries")

    pool_ids = harvested_ids | prev_candidate_ids | prev_selected_ids | set(FORCED_ANCHORS)
    logger.info(f"screening pool: {len(pool_ids)} unique repo ids total")

    # ---- (b) screen the whole pool ----
    verdicts = _screen_pool(pool_ids, token=token, timeout=args.timeout, max_workers=max_workers,
                             thread_result_timeout=args.thread_result_timeout)

    # ---- anchor verdicts, reported individually regardless of pass/fail ----
    anchor_verdicts: dict[str, dict[str, Any]] = {}
    for rid in FORCED_ANCHORS:
        v = verdicts.get(rid, {"repo_id": rid, "keep": False, "reason": "not_in_pool_unexpectedly"})
        anchor_verdicts[rid] = v
        logger.info(f"ANCHOR {rid}: keep={v.get('keep')} reason={v.get('reason')}")

    # ---- (d) label every kept repo edited/honest ----
    for rid, v in verdicts.items():
        if v.get("keep"):
            arm, matched_token = P.label_arm(rid, v.get("tags", []), v.get("card_text", ""))
            v["arm"] = arm
            v["matched_token"] = matched_token

    edited_records = [v for v in verdicts.values() if v.get("keep") and v.get("arm") == "edited"]
    honest_general = [v for v in verdicts.values() if v.get("keep") and v.get("arm") == "honest"]
    dropped_phase1 = [v for v in verdicts.values() if not v.get("keep")]
    logger.info(f"phase1 screen: {len(edited_records)} edited, {len(honest_general)} honest, "
                f"{len(dropped_phase1)} dropped")

    # ---- (e) matched honest arm per edited family signature ----
    edited_family_bases: dict[str, list[str]] = {}
    for r in edited_records:
        sig = r["family_signature"]
        bases = edited_family_bases.setdefault(sig, [])
        bm = r.get("base_model")
        if bm and bm not in bases:
            bases.append(bm)
    logger.info(f"{len(edited_family_bases)} distinct family signatures in the edited arm")

    honest_by_sig_general: dict[str, list[dict[str, Any]]] = {}
    for r in honest_general:
        honest_by_sig_general.setdefault(r["family_signature"], []).append(r)

    already_screened = set(verdicts.keys())
    matched_by_sig, dropped_phase2 = _find_matched_honest(
        edited_family_bases, already_screened, token=token, timeout=args.timeout,
        max_workers=max_workers, per_family_target=args.per_family_target,
        search_limit=args.honest_search_limit, thread_result_timeout=args.thread_result_timeout,
    )

    final_honest_by_sig: dict[str, list[dict[str, Any]]] = {}
    for sig in set(honest_by_sig_general) | set(matched_by_sig):
        seen_ids: set[str] = set()
        merged: list[dict[str, Any]] = []
        for r in honest_by_sig_general.get(sig, []) + matched_by_sig.get(sig, []):
            if r["repo_id"] not in seen_ids:
                seen_ids.add(r["repo_id"])
                merged.append(r)
        final_honest_by_sig[sig] = merged
    final_honest_records = [r for recs in final_honest_by_sig.values() for r in recs]

    # ---- assemble the panel, dedup by repo_id (edited takes precedence over any accidental
    # honest re-discovery of the same repo, though label_arm makes that structurally impossible) ----
    seen_repo_ids: set[str] = set()
    all_checkpoints: list[dict[str, Any]] = []
    for r in edited_records + final_honest_records:
        if r["repo_id"] in seen_repo_ids:
            continue
        seen_repo_ids.add(r["repo_id"])
        all_checkpoints.append(r)

    n_edited = sum(1 for r in all_checkpoints if r["arm"] == "edited")
    n_honest = sum(1 for r in all_checkpoints if r["arm"] == "honest")
    sig_edited = sorted({r["family_signature"] for r in all_checkpoints if r["arm"] == "edited"})
    sig_honest = sorted({r["family_signature"] for r in all_checkpoints if r["arm"] == "honest"})
    sig_both = sorted(set(sig_edited) & set(sig_honest))

    if n_edited < FLOOR_PER_ARM or n_honest < FLOOR_PER_ARM:
        logger.warning(f"FLOOR NOT MET: n_edited={n_edited} n_honest={n_honest} "
                        f"(floor={FLOOR_PER_ARM}/arm) — reporting as-achieved, not padding")
    elif n_edited < TARGET_PER_ARM or n_honest < TARGET_PER_ARM:
        logger.warning(f"target not met but floor cleared: n_edited={n_edited} "
                        f"n_honest={n_honest} (target={TARGET_PER_ARM}/arm)")
    else:
        logger.info(f"TARGET MET: n_edited={n_edited} n_honest={n_honest}")

    # ---- write card text files + build the lean per-checkpoint record for panel.json ----
    checkpoints_out: list[dict[str, Any]] = []
    for r in all_checkpoints:
        card_path = CARD_DIR / f"{P.sanitise(r['repo_id'])}.md"
        card_path.write_text(r.get("card_text") or "")
        checkpoints_out.append({
            "repo_id": r["repo_id"],
            "arm": r["arm"],
            "matched_token": r.get("matched_token"),
            "family_signature": r["family_signature"],
            "architecture": r["architecture"],
            "n_layers": r["n_layers"],
            "hidden_size": r["hidden_size"],
            "intermediate_size": r["intermediate_size"],
            "n_params_est": r["n_params_est"],
            "total_safetensors_bytes": r["total_safetensors_bytes"],
            "n_safetensors_files": r["n_safetensors_files"],
            "safetensors_files": r["safetensors_files"],
            "gated": r["gated"],
            "base_model": r.get("base_model"),
            "downloads": r.get("downloads"),
            "tags": r.get("tags", []),
            "card_text_sha256": r.get("card_text_sha256"),
        })

    panel_out = {
        "generated_at_unix": time.time(),
        "n_edited": n_edited,
        "n_honest": n_honest,
        "floor_per_arm": FLOOR_PER_ARM,
        "target_per_arm": TARGET_PER_ARM,
        "family_signatures_edited": sig_edited,
        "family_signatures_honest": sig_honest,
        "family_signatures_both_arms": sig_both,
        "anchors": {
            rid: {k: v.get(k) for k in ("keep", "reason", "arm", "matched_token",
                                        "family_signature", "gated")}
            for rid, v in anchor_verdicts.items()
        },
        "checkpoints": checkpoints_out,
    }
    (RESULTS_DIR / "panel.json").write_text(json.dumps(panel_out, indent=1, default=str))
    logger.info(f"wrote {RESULTS_DIR / 'panel.json'} ({len(checkpoints_out)} checkpoints)")

    # ---- dropped candidates, deduped, with a top-reasons histogram ----
    all_dropped_raw = dropped_phase1 + dropped_phase2
    dedup_seen: set[tuple[str, str | None]] = set()
    dropped_out_list: list[dict[str, Any]] = []
    for d in all_dropped_raw:
        key = (d.get("repo_id", ""), d.get("reason"))
        if key in dedup_seen:
            continue
        dedup_seen.add(key)
        dropped_out_list.append({
            "repo_id": d.get("repo_id"),
            "reason": d.get("reason"),
            "architecture": d.get("architecture"),
            "gated": d.get("gated"),
            "downloads": d.get("downloads"),
            "family_signature": d.get("family_signature"),
        })
    reason_counts = Counter(_reject_reason_group(d["reason"]) for d in dropped_out_list)
    dropped_out = {
        "generated_at_unix": time.time(),
        "n_dropped": len(dropped_out_list),
        "top_reject_reasons": dict(reason_counts.most_common(10)),
        "dropped": dropped_out_list,
    }
    (RESULTS_DIR / "panel_dropped.json").write_text(json.dumps(dropped_out, indent=1, default=str))
    logger.info(f"wrote {RESULTS_DIR / 'panel_dropped.json'} ({len(dropped_out_list)} dropped, "
                f"top reasons: {dict(reason_counts.most_common(5))})")

    logger.info(
        f"DONE. n_edited={n_edited} n_honest={n_honest} "
        f"sig_edited={len(sig_edited)} sig_honest={len(sig_honest)} sig_both={len(sig_both)}"
    )


if __name__ == "__main__":
    main()

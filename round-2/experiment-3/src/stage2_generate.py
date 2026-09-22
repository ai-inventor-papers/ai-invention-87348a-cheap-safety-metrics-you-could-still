#!/usr/bin/env python3
"""STAGE 2 = PART 2a - the IN-HOUSE TWO-SIDED GROUND TRUTH, on CPU.

FAILURE BRANCH F5 IS ACTIVE. The plan asked for a 16 GB GPU; this worker has NO GPU and a hard
cpuset of two hyperthreads of ONE physical EPYC core. So the graded panel is sized from a MEASURED
generation rate on the first checkpoints (never a declared number), the item sets are cut to H40/B40,
max_new_tokens is cut to 96, and checkpoints are ordered SMALLEST-FIRST within an edited-first,
family-interleaved sequence so an early stop still spans both arms and many families.

Everything written here is per-checkpoint and immediate: results/gen/<id>.jsonl the moment a
checkpoint finishes, so a partial panel is a partial RESULT.

Captured in the SAME pass, at no extra compute:
  L1_logit_gap   teacher-forced refusal-minus-comply continuation logprob  (BASELINE)
  L2_refusal_rate pre-registered refusal-prefix regex over the greedy text (BASELINE)
  BB8            refusal rate on H8, DISJOINT from H40, the black-box bar at a matched prompt budget
  hidden states  for the cross-fitted activation readout A_coupling       (INTERNAL)
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
from lanec import acts as A  # noqa: E402
from lanec import io as LIO  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(WS / "logs" / "stage2.log"), rotation="30 MB", level="DEBUG")

GEN_DIR = WS / "results" / "gen"
ACT_DIR = WS / "results" / "acts"
SEED = 20260920


def sanitise(rid: str) -> str:
    return rid.replace("/", "__")


def stratified_draw(rows: list[dict], n: int, key: str, seed: int, exclude: set[str]) -> list[dict]:
    """Draw `n` rows stratified over `key`, deterministically, excluding item ids in `exclude`."""
    rng = np.random.default_rng(seed)
    pool = [r for r in rows if r.get("item_id") not in exclude]
    strata: dict[str, list[dict]] = {}
    for r in pool:
        strata.setdefault(str(r.get(key, "na")), []).append(r)
    for k in strata:
        strata[k].sort(key=lambda r: str(r.get("item_id")))
        rng.shuffle(strata[k])
    picked: list[dict] = []
    keys = sorted(strata)
    i = 0
    while len(picked) < n and any(strata[k] for k in keys):
        k = keys[i % len(keys)]
        if strata[k]:
            picked.append(strata[k].pop())
        i += 1
    return picked[:n]


def build_items(n_h: int, n_b: int, n_bb: int) -> dict[str, Any]:
    harmful = LIO.read_jsonl(WS / "items" / "harmful_pool.jsonl")
    benign = LIO.read_jsonl(WS / "items" / "B120.jsonl")
    fit_pairs = LIO.read_jsonl(WS / "items" / "fit_pairs.jsonl")
    hcat = "category" if harmful and "category" in harmful[0] else (
        "source" if harmful and "source" in harmful[0] else "item_id")
    bcat = "type" if benign and "type" in benign[0] else (
        "category" if benign and "category" in benign[0] else "item_id")
    H = stratified_draw(harmful, n_h, hcat, SEED, set())
    used = {r["item_id"] for r in H}
    BB = stratified_draw(harmful, n_bb, hcat, SEED + 1, used)      # DISJOINT from H by construction
    B = stratified_draw(benign, n_b, bcat, SEED + 2, set())
    return {"H": H, "B": B, "BB": BB, "fit_pairs": fit_pairs,
            "h_strat_key": hcat, "b_strat_key": bcat}


def shared_hf_cache() -> Path:
    """The run-shared HuggingFace hub cache every step of this run reads from (never a workspace copy)."""
    hub = os.environ.get("HF_HUB_CACHE")
    if hub:
        return Path(hub)
    return Path(os.environ.get("HF_HOME", str(Path.home() / ".cache" / "huggingface"))) / "hub"


def load_cpu_model(repo_id: str, token: str | None, cache_root: Path,
                   dtype: torch.dtype = torch.float32):
    """`cache_root` is kept for API compatibility and must be the SHARED hub cache (shared_hf_cache());
    snapshot_download resolves against HF_HUB_CACHE, so no snapshot is ever written into the workspace."""
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForCausalLM, AutoTokenizer
    # Use the RUN-SHARED HF cache, never a private local_dir: 18 of the panel checkpoints -
    # including the whole Qwen3-4B Base / Instruct / SafeRL / abliterated quadruple - are already
    # on disk there from earlier steps of this run, and a local_dir= forces a second copy instead.
    local = snapshot_download(
        repo_id, token=token or None, cache_dir=str(cache_root),
        allow_patterns=["*.safetensors", "*.json", "*.txt", "*.model", "tokenizer*"],
        max_workers=4)
    tok = AutoTokenizer.from_pretrained(local, trust_remote_code=False)
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"
    model = AutoModelForCausalLM.from_pretrained(
        local, dtype=dtype, low_cpu_mem_usage=True, attn_implementation="sdpa",
        trust_remote_code=False)
    model.eval()
    return model, tok, local


def run_checkpoint(rec: dict, items: dict, *, token: str, cache_root: Path,
                   max_new_tokens: int, batch_size: int, deadline: float,
                   n_fit: int) -> dict[str, Any]:
    rid = rec["repo_id"]
    t0 = time.time()
    out: dict[str, Any] = {"repo_id": rid, "arm": rec.get("arm"),
                           "family_signature": rec.get("family_signature"),
                           "n_params_est": rec.get("n_params_est"),
                           "hidden_size": rec.get("hidden_size"),
                           "max_new_tokens": max_new_tokens, "status": "PENDING",
                           "device": "cpu", "dtype": "float32"}
    model = tok = local = None
    try:
        model, tok, local = load_cpu_model(rid, token, cache_root)
        dev = torch.device("cpu")
        is_base = bool(getattr(tok, "chat_template", None) in (None, "")) or \
            rid.lower().endswith("-base")
        out["is_base_template"] = is_base
        out["template"] = A.template_fingerprint(tok, is_base=is_base)

        def rendered(rows):
            return [A.render_chat(tok, r["prompt"], is_base=is_base) for r in rows]

        rH, rB, rBB = rendered(items["H"]), rendered(items["B"]), rendered(items["BB"])

        t_g = time.time()
        gen_H = A.generate_batch(model, tok, rH, dev, max_new_tokens=max_new_tokens,
                                 batch_size=batch_size)
        out["sec_gen_H"] = round(time.time() - t_g, 1)
        out["measured_tok_per_s"] = round(len(rH) * max_new_tokens / max(out["sec_gen_H"], 1e-9), 2)
        logger.info(f"    H{len(rH)} generated in {out['sec_gen_H']}s "
                    f"({len(rH)*max_new_tokens/max(out['sec_gen_H'],1e-9):.1f} tok/s aggregate)")
        gen_B = A.generate_batch(model, tok, rB, dev, max_new_tokens=max_new_tokens,
                                 batch_size=batch_size)
        gen_BB = A.generate_batch(model, tok, rBB, dev, max_new_tokens=max_new_tokens,
                                  batch_size=batch_size)

        # BASELINE L1: teacher-forced refusal-minus-comply drive on the SAME prompts (no extra decode)
        lp_ref = A.continuation_logprob(model, tok, rH, A.REFUSAL_CONT, dev, batch_size=batch_size)
        lp_com = A.continuation_logprob(model, tok, rH, A.COMPLY_CONT, dev, batch_size=batch_size)
        drive_H = lp_ref - lp_com
        out["L1_logit_gap"] = float(np.mean(drive_H))
        out["L1_decision_spread"] = float(np.std(drive_H))

        # BASELINE L2 + the black-box bar BB8 on DISJOINT items
        out["L2_refusal_rate"] = A.regex_refusal_rate(gen_H)["refusal_rate"]
        out["L2_overrefusal_rate_regex"] = A.regex_refusal_rate(gen_B)["refusal_rate"]
        bb = A.regex_refusal_rate(gen_BB)
        out["BB8_refusal_rate"] = bb["refusal_rate"]
        out["BB8_n"] = bb["n"]

        # INTERNAL: cross-fitted activation readout inputs, from a prefill over the fit pairs
        if n_fit > 0 and time.time() < deadline:
            fp = items["fit_pairs"][:n_fit]
            try:
                h = A.harvest(model, tok, fp, dev, is_base=is_base, batch_size=batch_size)
                np.savez_compressed(ACT_DIR / f"{sanitise(rid)}.npz",
                                    hidden=h.hidden.astype(np.float16), labels=h.labels,
                                    refusal_drive=h.refusal_drive,
                                    categories=np.array(h.categories, dtype=object),
                                    item_ids=np.array(h.item_ids, dtype=object))
                out["act_harvest"] = {"n_items": int(len(h.item_ids)), "n_layers": int(h.n_layers),
                                      "d_model": int(h.d_model),
                                      "decision_spread": float(np.std(h.refusal_drive))}
            except (RuntimeError, MemoryError, ValueError) as exc:
                logger.warning(f"    activation harvest failed for {rid}: {exc}")
                out["act_harvest"] = {"error": str(exc)}

        rows = []
        for tag, its, gens in (("H", items["H"], gen_H), ("B", items["B"], gen_B),
                               ("BB", items["BB"], gen_BB)):
            for it, g in zip(its, gens):
                rows.append({"repo_id": rid, "set": tag, "item_id": it["item_id"],
                             "category": it.get("category", it.get("type", "na")),
                             "prompt": it["prompt"], "response": g})
        LIO.write_jsonl(GEN_DIR / f"{sanitise(rid)}.jsonl", rows)
        out.update({"status": "OK", "n_gen": len(rows), "elapsed_s": round(time.time() - t0, 1)})
        return out
    except (OSError, RuntimeError, ValueError, MemoryError, ImportError) as exc:
        logger.error(f"  {rid} FAILED: {type(exc).__name__}: {exc}")
        out.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}",
                    "elapsed_s": round(time.time() - t0, 1)})
        return out
    finally:
        del model, tok
        gc.collect()
        # NOTE: the snapshot lives in the run-shared HF cache and is deliberately NOT deleted -
        # other steps of this run read the same blobs, and the volume has ample free space.


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=str(WS / "results" / "panel.json"))
    ap.add_argument("--minutes", type=float, default=110.0)
    ap.add_argument("--n-h", type=int, default=40)
    ap.add_argument("--n-b", type=int, default=40)
    ap.add_argument("--n-bb", type=int, default=8)
    ap.add_argument("--n-fit", type=int, default=48)
    ap.add_argument("--max-new-tokens", type=int, default=96)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--max-params", type=float, default=2.2e9)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--cached-only", action="store_true",
                    help="only checkpoints already in the shared HF cache (no transfer at all)")
    args = ap.parse_args()

    torch.set_num_threads(max(1, args.threads))
    GEN_DIR.mkdir(parents=True, exist_ok=True)
    ACT_DIR.mkdir(parents=True, exist_ok=True)
    # Checkpoints are read straight from the RUN-SHARED HF cache (see load_cpu_model); nothing is ever copied
    # into this workspace. An early v1 build copied snapshots to scratch/snapshots/ - a byte-identical duplicate
    # of the shared-cache blob (2.3 GB, sha256-verified) that exceeded the repo's 100 MB file limit and was removed.
    cache_root = shared_hf_cache()
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN") or ""

    items = build_items(args.n_h, args.n_b, args.n_bb)
    assert not ({r["item_id"] for r in items["H"]} & {r["item_id"] for r in items["BB"]}), \
        "BB8 must be DISJOINT from H - the black-box bar is tautological otherwise"
    (WS / "results" / "items_used.json").write_text(json.dumps({
        "H": [r["item_id"] for r in items["H"]], "B": [r["item_id"] for r in items["B"]],
        "BB8": [r["item_id"] for r in items["BB"]],
        "H_strat_key": items["h_strat_key"], "B_strat_key": items["b_strat_key"],
        "disjoint_H_BB8": True, "seed": SEED,
        "n_fit_pairs": min(args.n_fit, len(items["fit_pairs"]))}, indent=2))

    panel = json.loads(Path(args.panel).read_text())
    rows = panel["checkpoints"] if isinstance(panel, dict) else panel
    rows = [r for r in rows if (r.get("n_params_est") or 1e12) <= args.max_params]
    cstat = {}
    csp = WS / "results" / "cache_status.json"
    if csp.exists():
        for c in json.loads(csp.read_text()):
            cstat[c["repo_id"]] = bool(c.get("fully_cached"))
    if args.cached_only:
        rows = [r for r in rows if cstat.get(r["repo_id"])]
    for r in rows:
        r["_cached"] = 0 if cstat.get(r["repo_id"]) else 1
    logger.info(f"{sum(1 for r in rows if not r['_cached'])} of {len(rows)} candidates are "
                f"already in the shared cache (zero transfer)")
    # edited first (it carries the strength variance the claim needs), family-interleaved,
    # SMALLEST first inside each family because this box has one physical core
    for r in rows:
        r["_sz"] = r.get("n_params_est") or 1e12
    order = sorted(rows, key=lambda x: (round((x["_sz"] or 1e12) / 1e9, 1),
                                        0 if x.get("arm") == "edited" else 1,
                                        x.get("_cached", 1), x["repo_id"]))

    deadline = time.time() + args.minutes * 60
    summary: list[dict] = []
    n_ok = 0
    for rec in order:
        if time.time() > deadline:
            logger.warning("STAGE 2 deadline reached; stopping with a partial graded panel")
            break
        rid = rec["repo_id"]
        sp = WS / "results" / "gen" / f"{sanitise(rid)}.jsonl"
        meta_p = WS / "results" / "gen" / f"{sanitise(rid)}.meta.json"
        if sp.exists() and meta_p.exists():
            logger.info(f"  skip {rid} (already generated)")
            summary.append(json.loads(meta_p.read_text()))
            n_ok += 1
            continue
        logger.info(f"[{n_ok+1}] {rid} arm={rec.get('arm')} "
                    f"params={(rec.get('n_params_est') or 0)/1e9:.2f}B "
                    f"({(deadline-time.time())/60:.0f} min left)")
        res = run_checkpoint(rec, items, token=token, cache_root=cache_root,
                             max_new_tokens=args.max_new_tokens, batch_size=args.batch_size,
                             deadline=deadline, n_fit=args.n_fit)
        meta_p.write_text(json.dumps(res, indent=1, default=float))
        summary.append(res)
        (WS / "results" / "stage2_summary.json").write_text(
            json.dumps({"rows": summary,
                        "n_ok": sum(1 for s in summary if s["status"] == "OK"),
                        "median_seconds": float(np.median([s["elapsed_s"] for s in summary
                                                           if s.get("elapsed_s")]))
                        if summary else None}, indent=2, default=float))
        if res["status"] == "OK":
            n_ok += 1
            el = res["elapsed_s"]
            left = (deadline - time.time()) / 60
            logger.info(f"    OK in {el}s -> at this rate {int(left*60/max(el,1))} more fit "
                        f"in the remaining {left:.0f} min "
                        f"(L2_refusal={res.get('L2_refusal_rate')}, BB8={res.get('BB8_refusal_rate')})")
    logger.info(f"STAGE 2 finished: {n_ok} checkpoints generated")


if __name__ == "__main__":
    main()

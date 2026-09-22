#!/usr/bin/env python3
"""STAGE 1 = PART 1 - recover the abliteration recipe from the WEIGHTS ALONE.

Parent-free, prompt-free, CPU only. One checkpoint at a time; the result is written to
results/ckpt/<sanitised>.json THE MOMENT it is computed, so a partial panel is a partial RESULT and
the loop is resumable: an existing valid file is skipped.

Transfer, not compute, was expected to bind; on this box (2 CPU, no GPU) the eigendecomposition binds
too, so the layer set is chosen adaptively from a measured per-checkpoint cost model and the achieved
throughput is reported as a MEASURED number, never a declared one.
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import queue
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np
import requests
from loguru import logger

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
from lanec import recipe as R  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(WS / "logs" / "stage1.log"), rotation="30 MB", level="DEBUG")

CKPT_DIR = WS / "results" / "ckpt"
CARD_DIR = WS / "panel" / "cards"
VEC_DIR = WS / "results" / "vecs"

# ---- card census (1.4) -----------------------------------------------------------------
TOOL_RE = re.compile(r"(heretic|failspy|abliterator|remove[- ]refusals|mlabonne|huihui|"
                     r"transformerlens|orthogonaliz|abliterat)", re.I)
SCOPE_PERLAYER = re.compile(r"(per[- ]layer|each layer|layer[- ]wise|layer[- ]specific)", re.I)
SCOPE_SHARED = re.compile(r"(single direction|global direction|one direction|shared direction|"
                          r"all layers|every layer)", re.I)
SCOPE_BAND = re.compile(r"layers?\s*\d+\s*(?:-|to|through|\.\.)\s*\d+", re.I)
STRENGTH_RE = re.compile(r"(?:ablation|scale|refusal|max)[ _]?(?:weight|factor|strength)\s*[=:]?\s*"
                         r"([0-9]*\.?[0-9]+)|kappa\s*[=:]\s*([0-9]*\.?[0-9]+)", re.I)


def card_census(text: str) -> dict[str, Any]:
    if not text:
        return {"tool": None, "scope_class": "STATED_NOTHING", "strengths": [], "n_chars": 0}
    tools = sorted({m.group(0).lower() for m in TOOL_RE.finditer(text)})
    strengths = []
    for m in STRENGTH_RE.finditer(text):
        for g in m.groups():
            if g:
                try:
                    strengths.append(float(g))
                except ValueError:
                    pass
    per, shared, band = bool(SCOPE_PERLAYER.search(text)), bool(SCOPE_SHARED.search(text)), \
        bool(SCOPE_BAND.search(text))
    if per:
        cls = "STATED_PERLAYER"
    elif band:
        cls = "STATED_BAND"
    elif shared:
        cls = "STATED_FULL_SHARED_ALL"
    else:
        cls = "STATED_NOTHING"
    return {"tool": tools[0] if tools else None, "tools": tools, "scope_class": cls,
            "strengths": strengths[:8], "n_chars": len(text)}


def sanitise(repo_id: str) -> str:
    return repo_id.replace("/", "__")


def _prefetch(sess, repo_id, targets, q: queue.Queue, stop: threading.Event) -> None:
    for key, tgt in targets:
        if stop.is_set():
            break
        try:
            W = R.fetch_tensor(sess, repo_id, tgt)
            q.put((key, tgt, W, None))
        except (R.RangedReadError, requests.RequestException, ValueError) as exc:
            q.put((key, tgt, None, str(exc)))
    q.put((None, None, None, None))


def read_checkpoint(rec: dict[str, Any], *, token: str | None, deadline: float,
                    layer_stride: int, want_down: bool, byte_budget: int,
                    max_d: int) -> dict[str, Any]:
    repo_id = rec["repo_id"]
    t_start = time.time()
    sess = R._session(token)
    out: dict[str, Any] = {
        "repo_id": repo_id, "arm": rec.get("arm"), "family_signature": rec.get("family_signature"),
        "architecture": rec.get("architecture"), "n_layers_cfg": rec.get("n_layers"),
        "hidden_size": rec.get("hidden_size"), "n_params_est": rec.get("n_params_est"),
        "status": "PENDING", "layer_stride": layer_stride, "want_down_proj": want_down,
    }
    try:
        plan = R.plan_repo(repo_id, token=token, sess=sess, layer_stride=layer_stride,
                           want_down_proj=want_down)
        if plan.skip_reason:
            out.update({"status": "SKIPPED", "skip_reason": plan.skip_reason})
            return out
        out["n_experts"] = plan.n_experts
        targets = sorted(plan.targets.items(), key=lambda kv: (kv[1]["layer"], kv[1]["component"]))
        # one expert only per (layer, component): experts 0..3 averaged would double the eigh bill
        seen: set[tuple[int, str]] = set()
        picked = []
        for k, t in targets:
            key = (t["layer"], t["component"])
            if key in seen:
                continue
            if t["shape"][0] > max_d:
                continue
            seen.add(key)
            picked.append((k, t))
        if not picked:
            out.update({"status": "SKIPPED", "skip_reason": f"no matrix with d_out <= {max_d}"})
            return out
        # honour the byte budget: attn first (every abliteration tool edits o_proj), then mlp
        picked.sort(key=lambda kv: (0 if kv[1]["component"] == "attn" else 1, kv[1]["layer"]))
        kept, total = [], 0
        for k, t in picked:
            if total + t["nbytes"] > byte_budget and kept:
                continue
            kept.append((k, t)); total += t["nbytes"]
        out["bytes_planned"] = total
        out["n_matrices"] = len(kept)
        out["dropped_for_budget"] = len(picked) - len(kept)

        q: queue.Queue = queue.Queue(maxsize=2)
        stop = threading.Event()
        th = threading.Thread(target=_prefetch, args=(sess, repo_id, kept, q, stop), daemon=True)
        th.start()

        per_layer: dict[str, dict[int, dict[str, Any]]] = {"attn": {}, "mlp": {}}
        u_min: dict[str, dict[int, np.ndarray]] = {"attn": {}, "mlp": {}}
        u_top: dict[str, dict[int, np.ndarray]] = {"attn": {}, "mlp": {}}
        grams: dict[str, dict[int, np.ndarray]] = {"attn": {}, "mlp": {}}
        mean_sq: dict[str, dict[int, float]] = {"attn": {}, "mlp": {}}
        n_read, n_fail, bytes_got = 0, 0, 0
        t_fetch_only = 0.0
        while True:
            if time.time() > deadline:
                stop.set()
                out["truncated_by_deadline"] = True
                break
            try:
                key, tgt, W, err = q.get(timeout=300)
            except queue.Empty:
                stop.set(); out["truncated_by_timeout"] = True; break
            if key is None:
                break
            if W is None:
                n_fail += 1
                logger.debug(f"{repo_id}: {key} fetch failed: {err}")
                continue
            comp, layer = tgt["component"], tgt["layer"]
            try:
                st = R.spectrum_stats(W)
            except (np.linalg.LinAlgError, ValueError, MemoryError) as exc:
                n_fail += 1
                logger.warning(f"{repo_id} L{layer}/{comp}: spectrum failed: {exc}")
                del W; gc.collect(); continue
            j = min(int(st["j_star"]), st["u_bottom"].shape[1] - 1)
            u_min[comp][layer] = st["u_bottom"][:, j].copy()
            u_top[comp][layer] = st["u_top"][:, 0].copy()
            Wd = np.asarray(W, dtype=np.float64)
            Gl = Wd @ Wd.T
            grams[comp][layer] = 0.5 * (Gl + Gl.T)
            mean_sq[comp][layer] = float(st["mean_sq"])
            del Wd, Gl
            per_layer[comp][layer] = {
                k: st[k] for k in ("d_out", "d_in", "s_bottom", "s_top", "spectrum_idx",
                                  "spectrum_val", "s_median", "s_max", "botgap", "k_local",
                                  "kappa_hat", "abs_dev", "ratio_min", "ratio_at0", "kappa_at0",
                                  "j_star", "fit_r2", "resid_log", "tail_ok",
                                  "structurally_rank_deficient", "effective_rank_ub")
            }
            bytes_got += tgt["nbytes"]; n_read += 1
            del W, st; gc.collect()
        stop.set()
        th.join(timeout=5)

        out["n_matrices_read"] = n_read
        out["n_matrices_failed"] = n_fail
        out["bytes_read"] = bytes_got
        if n_read == 0:
            out.update({"status": "FAILED", "skip_reason": "no matrices read"})
            return out

        # -------- 1.3 checkpoint-level recipe vector --------
        n_layers = int(rec.get("n_layers") or (max(max(per_layer[c], default=-1)
                                                   for c in per_layer) + 1))
        summary: dict[str, Any] = {}
        for comp in ("attn", "mlp"):
            pl = per_layer[comp]
            if not pl:
                continue
            ks = {l: v["kappa_hat"] for l, v in pl.items() if np.isfinite(v["kappa_hat"])}
            bg = {l: v["botgap"] for l, v in pl.items() if np.isfinite(v["botgap"])}
            kl = {l: v["k_local"] for l, v in pl.items() if np.isfinite(v["k_local"])}
            band = R.touched_band(ks, None)
            xlc = R.cross_layer_cosine(u_min[comp])
            xlc_band = R.cross_layer_cosine(
                u_min[comp], layers=[l for l in u_min[comp]
                                     if band["band_lo"] is not None
                                     and band["band_lo"] <= l <= band["band_hi"]]) \
                if band["band_lo"] is not None else {"xlc": float("nan"), "n_pairs": 0}
            win = max(2, 8 // max(1, layer_stride))
            bsa = R.bsa_window(u_min[comp], window=win)
            tsa = R.bsa_window(u_top[comp], window=win)
            prof = R.fit_depth_profile(sorted(ks), [ks[l] for l in sorted(ks)], n_layers)
            rq_med = float("nan"); rq_per: dict[str, float] = {}; cos_pool = float("nan")
            try:
                rhat = R.pooled_bottom_direction(grams[comp])
                if rhat is not None:
                    vals = {}
                    for l, Gl in grams[comp].items():
                        q = float(rhat[:, 0] @ (Gl @ rhat[:, 0]))
                        ms = mean_sq[comp].get(l, float("nan"))
                        vals[l] = q / ms if ms and np.isfinite(ms) and ms > 0 else float("nan")
                    good = [v for v in vals.values() if np.isfinite(v)]
                    rq_med = float(np.median(good)) if good else float("nan")
                    rq_per = {str(l): float(v) for l, v in sorted(vals.items())}
                    cs = [abs(float(rhat[:, 0] @ u_min[comp][l])) for l in u_min[comp]]
                    cos_pool = float(np.mean(cs)) if cs else float("nan")
            except (np.linalg.LinAlgError, ValueError) as exc:
                logger.warning(f"{repo_id}/{comp}: pooled direction failed: {exc}")
            n_srd = sum(1 for v in pl.values() if v.get("structurally_rank_deficient"))
            summary[comp] = {
                "n_layers_read": len(pl),
                "n_structurally_rank_deficient": n_srd,
                "structurally_rank_deficient": bool(n_srd > len(pl) / 2),
                "kappa_hat_max": float(max(ks.values())) if ks else float("nan"),
                "kappa_hat_mean": float(np.mean(list(ks.values()))) if ks else float("nan"),
                "kappa_hat_p90": float(np.percentile(list(ks.values()), 90)) if ks else float("nan"),
                "botgap_min": float(min(bg.values())) if bg else float("nan"),
                "botgap_median": float(np.median(list(bg.values()))) if bg else float("nan"),
                "k_local_max": float(max(kl.values())) if kl else float("nan"),
                "band_lo": band["band_lo"], "band_hi": band["band_hi"],
                "band_frac": band["band_frac"], "band_mode": band["mode"],
                "XLC": xlc["xlc"], "XLC_max": xlc["xlc_max"], "XLC_p90": xlc["xlc_p90"],
                "XLC_iso_null": xlc["iso_null"], "XLC_band": xlc_band["xlc"],
                "BSA_w8": bsa["bsa_w"], "BSA_all": bsa["bsa_all"],
                "BSA_window_read_positions": win,
                "BSA_window_model_layers": win * max(1, layer_stride),
                "BSA_win": [bsa["win_lo"], bsa["win_hi"]],
                "TSA_w8": tsa["bsa_w"], "TSA_all": tsa["bsa_all"],
                "profile": prof,
                "RQ_pooled": rq_med,
                "RQ_pooled_log10": float(np.log10(max(rq_med, 1e-300))) if np.isfinite(rq_med) else float("nan"),
                "RQ_per_layer": rq_per,
                "cos_pooled_vs_umin": cos_pool,
                "per_layer_kappa_hat": {str(l): float(v) for l, v in sorted(ks.items())},
                "per_layer_botgap": {str(l): float(v) for l, v in sorted(bg.items())},
            }
        out["by_component"] = summary
        xf = R.cross_family_cosine(u_min["attn"], u_min["mlp"])
        out["cross_family_cosine"] = xf
        # HEADLINE COMPONENT. o_proj is the tensor every abliteration tool edits and is the natural
        # first choice, BUT on families with num_heads * head_dim < hidden_size it is structurally
        # rank-deficient: its bottom spectrum is zero for an UNTOUCHED checkpoint, and a full
        # kappa = 1 ablation adds no new deficiency there, so a rank read is structurally blind.
        # down_proj always has d_in > d_out, so it always carries the scar. Pick accordingly and
        # record which site was used.
        a_ok = bool(summary.get("attn") and not summary["attn"].get("structurally_rank_deficient"))
        m_ok = bool(summary.get("mlp") and not summary["mlp"].get("structurally_rank_deficient"))
        if a_ok:
            head, head_name = summary["attn"], "attn"
        elif m_ok:
            head, head_name = summary["mlp"], "mlp"
        else:
            head = summary.get("attn") or summary.get("mlp") or {}
            head_name = "attn" if summary.get("attn") else ("mlp" if summary.get("mlp") else "none")
        out["headline_component"] = head_name
        out["headline_component_is_structurally_valid"] = bool(a_ok or m_ok)
        out["kappa_hat"] = head.get("kappa_hat_max", float("nan"))
        out["kappa_hat_mean"] = head.get("kappa_hat_mean", float("nan"))
        out["abs_dev"] = 1.0 - head.get("kappa_hat_max", float("nan"))
        out["BOTGAP_min"] = head.get("botgap_min", float("nan"))
        out["BSA_w8"] = head.get("BSA_w8", float("nan"))
        out["BSA_all"] = head.get("BSA_all", float("nan"))
        out["TSA_w8"] = head.get("TSA_w8", float("nan"))
        out["XLC"] = head.get("XLC", float("nan"))
        out["RQ_pooled"] = head.get("RQ_pooled", float("nan"))
        out["RQ_pooled_log10"] = head.get("RQ_pooled_log10", float("nan"))
        out["band_frac"] = head.get("band_frac", float("nan"))
        out["band_lo_frac"] = (head["band_lo"] / n_layers
                               if head.get("band_lo") is not None and n_layers else float("nan"))

        VEC_DIR.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            VEC_DIR / f"{sanitise(repo_id)}.npz",
            **{f"{c}_u_{l}": v.astype(np.float32) for c in u_min for l, v in u_min[c].items()},
            **{f"{c}_t_{l}": v.astype(np.float32) for c in u_top for l, v in u_top[c].items()})
        out["vectors_saved"] = True

        card_path = CARD_DIR / f"{sanitise(repo_id)}.md"
        card_text = card_path.read_text(errors="replace") if card_path.exists() else \
            rec.get("card_text", "")
        out["card"] = card_census(card_text)

        el = time.time() - t_start
        out.update({"status": "OK", "elapsed_s": round(el, 1),
                    "mb_per_s": round((bytes_got / 1e6) / max(el, 1e-6), 2)})
        return out
    except (R.RangedReadError, requests.RequestException) as exc:
        out.update({"status": "FAILED", "skip_reason": f"{type(exc).__name__}: {exc}"})
        return out
    finally:
        sess.close()


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=str(WS / "results" / "panel.json"))
    ap.add_argument("--minutes", type=float, default=105.0)
    ap.add_argument("--max-ckpt", type=int, default=200)
    ap.add_argument("--byte-budget-mb", type=int, default=700)
    ap.add_argument("--max-d", type=int, default=4096)
    ap.add_argument("--probe-only", type=int, default=0)
    ap.add_argument("--per-ckpt-seconds", type=float, default=900.0,
                    help="hard cap per checkpoint. Raise it when a matched SET of checkpoints must "
                         "be read over the SAME layer set for a like-for-like comparison, since a "
                         "truncated read changes the layer set and breaks comparability.")
    args = ap.parse_args()

    CKPT_DIR.mkdir(parents=True, exist_ok=True)
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    panel = json.loads(Path(args.panel).read_text())
    rows = panel["checkpoints"] if isinstance(panel, dict) else panel
    deadline_all = time.time() + args.minutes * 60

    # Already-cached checkpoints read from LOCAL disk at ~48 MB/s against ~3.6 MB/s over HTTP
    # (measured), so they come first; then interleave arms and families so an early stop still
    # spans both arms and many families.
    cstat: dict[str, bool] = {}
    csp = WS / "results" / "cache_status.json"
    if csp.exists():
        for c in json.loads(csp.read_text()):
            cstat[c["repo_id"]] = bool(c.get("fully_cached"))
    rows.sort(key=lambda r: (0 if cstat.get(r["repo_id"]) else 1,
                             0 if r.get("arm") == "edited" else 1,
                             r.get("n_params_est") or 1e12))
    by_key: dict[tuple, list[dict]] = {}
    for r in rows:
        by_key.setdefault((0 if cstat.get(r["repo_id"]) else 1,
                           r.get("arm", "?"), r.get("family_signature", "?")), []).append(r)
    order: list[dict] = []
    pools = [by_key[k] for k in sorted(by_key)]
    i = 0
    while any(pools):
        p = pools[i % len(pools)]
        if p:
            order.append(p.pop(0))
        pools = [x for x in pools if x]
        i += 1
    if args.probe_only:
        order = order[: args.probe_only]

    done, skipped, failed = 0, 0, 0
    timings: list[dict] = []
    for rec in order[: args.max_ckpt]:
        if time.time() > deadline_all:
            logger.warning("STAGE 1 deadline reached; stopping with a partial panel (this is a RESULT)")
            break
        rid = rec["repo_id"]
        fp = CKPT_DIR / f"{sanitise(rid)}.json"
        if fp.exists():
            try:
                prev = json.loads(fp.read_text())
                if prev.get("status") in ("OK", "SKIPPED"):
                    skipped += 1
                    continue
            except json.JSONDecodeError:
                pass
        # cost model: eigh is O(d^3) per matrix. Adapt the layer stride to keep a checkpoint bounded.
        d = int(rec.get("hidden_size") or 2048)
        nl = int(rec.get("n_layers") or 28)
        # MEASURED cost model for the randomized subspace solver: ~quadratic in d, not cubic
        est_eigh_s = 2 * nl * (d / 2048.0) ** 2 * float(os.environ.get("LANEC_SEC_PER_MAT", "3.0"))
        stride = 1
        while est_eigh_s / stride > 300 and stride < 4:
            stride += 1
        want_down = True
        per_ckpt_deadline = min(deadline_all, time.time() + args.per_ckpt_seconds)
        logger.info(f"[{done+1}] {rid}  d={d} L={nl} stride={stride} down_proj={want_down} "
                    f"est_eigh={est_eigh_s:.0f}s")
        res = read_checkpoint(rec, token=token, deadline=per_ckpt_deadline, layer_stride=stride,
                              want_down=want_down, byte_budget=args.byte_budget_mb * 1_000_000,
                              max_d=args.max_d)
        fp.write_text(json.dumps(res, indent=1, default=float))
        timings.append({"repo_id": rid, "status": res["status"],
                        "elapsed_s": res.get("elapsed_s"), "mb_per_s": res.get("mb_per_s"),
                        "bytes_read": res.get("bytes_read"), "d": d, "n_layers": nl,
                        "stride": stride, "n_read": res.get("n_matrices_read")})
        (WS / "results" / "throughput.json").write_text(json.dumps(
            {"measured_per_checkpoint": timings,
             "n_ok": sum(1 for t in timings if t["status"] == "OK"),
             "median_mb_per_s": float(np.median([t["mb_per_s"] for t in timings
                                                 if t.get("mb_per_s")])) if any(
                 t.get("mb_per_s") for t in timings) else None,
             "median_seconds_per_ckpt": float(np.median([t["elapsed_s"] for t in timings
                                                         if t.get("elapsed_s")])) if any(
                 t.get("elapsed_s") for t in timings) else None},
            indent=2, default=float))
        if res["status"] == "OK":
            done += 1
            logger.info(f"    OK kappa_hat={res.get('kappa_hat'):.3f} "
                        f"BOTGAP_min={res.get('BOTGAP_min'):.4f} BSA_w8={res.get('BSA_w8'):.3f} "
                        f"XLC={res.get('XLC'):.3f} in {res.get('elapsed_s')}s "
                        f"({res.get('mb_per_s')} MB/s)")
        elif res["status"] == "SKIPPED":
            skipped += 1
            logger.info(f"    SKIP {res.get('skip_reason')}")
        else:
            failed += 1
            logger.warning(f"    FAIL {res.get('skip_reason')}")
    logger.info(f"STAGE 1 finished: {done} OK, {skipped} skipped, {failed} failed")


if __name__ == "__main__":
    main()

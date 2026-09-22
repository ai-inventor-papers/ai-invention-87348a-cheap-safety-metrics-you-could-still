#!/usr/bin/env python3
"""PART 1 (v2) - recover the abliteration recipe from ONE checkpoint's weights: parent-free, prompt-free.

Why a v2 (measured, DEVIATIONS.json D12): v1 used a shift-invert subspace solver on a bottom-24 block and a
layer stride of 2-4 because a dense eigh cost 12 s at d=1024 on this box. That cost was THREAD
OVERSUBSCRIPTION (OpenBLAS/torch saw the host's 192 CPUs), not arithmetic: with BLAS pinned to one thread a
float64 eigh costs 0.64 s at d=1024 and 3.6 s at d=2048. v2 therefore reads EVERY layer and computes the
EXACT full left-singular spectrum of both residual-write matrices, which (a) lets the tail fit use the
pre-registered window j in [3, 40] instead of v1's [3, 20], and (b) removes the stride limitation D10.

Per layer L and matrix family M in {attn = o_proj, mlp = down_proj}:
    G = W W^T (on the smaller side when d_in < d_out, mapped back),  eigh -> s ascending, U
    BOTGAP = s0/s1 ; k_local = 1 - s0/s1
    tail fit log s_j ~ a + b log(j+1) + c log(j+1)^2 on j in [3, 40] (robust, 3 trimmed), extrapolated to
    rank 0, INDEX SCAN j in [0, 15] for the largest downward residual (load-bearing for kappa > 1)
        -> kappa_hat = 1 - ratio_min, abs_dev = |1 - kappa_hat| = ratio_min, j_star
    sigma_min/sigma_rms (the operating range of any rank read), 128-point log-spaced spectrum (null model)
    bottom-4 and top-16 left singular vectors (npz, float16)
Checkpoint level: BOTGAP_min, kappa_hat max/mean, XLC (mean pairwise |cos| of bottom-1 directions across
layers), XFC (o_proj vs down_proj bottom directions at the same layer), BSA_w8 / BSA_all at k = 1, 2, 4
(ADOPTED PRIOR ART - the public Jorak Model Scanner's subspace signature; a DETECTION statistic), TSA_w8 over
top bands {1, 2-8, 9-16}, the depth-profile fit of kappa_hat(L), and RQ (Rayleigh depression of the pooled
cross-layer bottom direction; graded at every kappa - v1's addition, recomputed exactly here).

Structural validity (measured in v1, D7): a bottom read only means something where d_in > d_out STRICTLY.
Each family records its aspect ratio; the analysis picks the headline site per checkpoint by aspect ratio.

Sources: local snapshots in the run-shared HF cache (safetensors only; quantised repos are SKIPPED with a
reason, never dequantised into the honest null). CONSTRUCTED entries rebuild W(kappa) = W_p + kappa (W_e - W_p).
Queue: results/weights_queue.json, re-read before every checkpoint. Output: results/ckpt_v2/<id>.json +
results/vecs_v2/<id>.npz, written atomically the moment each checkpoint finishes; existing files are skipped.
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import argparse
import gc
import json
import math
import re
import resource
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
from lanec.recipe import (DOWN_RE, EXPERT_RE, LAYER_RE, O_PROJ_RE, bsa_window,  # noqa: E402
                          cross_family_cosine, cross_layer_cosine, fit_depth_profile, fit_tail)

RES = WS / "results"
CK = RES / "ckpt_v2"
VE = RES / "vecs_v2"
for _d in (CK, VE, WS / "logs"):
    _d.mkdir(parents=True, exist_ok=True)
QUEUE = RES / "weights_queue.json"

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(WS / "logs" / "stage1_weights_v2.log"), rotation="30 MB", level="DEBUG")

TAIL = (3, 40)          # PRE-REGISTERED window (plan 1.2); v1 used (3, 20) because it only had 24 values
TAIL_V1 = (3, 20)
SCAN = 16
N_BOT_VEC, N_TOP_VEC = 4, 16
QUANT_KEY = re.compile(r"(weight_scale|weight_zero_point|qweight|qzeros|scales|_scale$|g_idx|absmax|quant_map)")


def sanitise(s: str) -> str:
    return s.replace("/", "__").replace(":", "_").replace("|", "_")


_DOWNLOADED: set[str] = set()


def snapshot(repo_id: str, allow_download: bool = False) -> Path:
    """Local snapshot from the run-shared cache; when `allow_download`, fetch ONLY safetensors + json
    (never the whole repo), and remember it so the blobs are deleted again right after the read."""
    from huggingface_hub import snapshot_download
    try:
        p = Path(snapshot_download(repo_id, local_files_only=True))
        if any(p.glob("*.safetensors")):
            return p
    except Exception:  # noqa: BLE001 - LocalEntryNotFoundError and friends
        if not allow_download:
            raise
    if not allow_download:
        raise FileNotFoundError(f"{repo_id}: not in the local cache")
    p = Path(snapshot_download(repo_id, allow_patterns=["*.safetensors", "*.json"]))
    _DOWNLOADED.add(repo_id)
    return p


def drop_download(repo_id: str) -> None:
    """Delete a repo this process downloaded (streamed read: never retain a fetched checkpoint)."""
    import shutil
    if repo_id not in _DOWNLOADED:
        return
    hub = Path(os.environ.get("HF_HUB_CACHE") or Path(os.environ.get("HF_HOME", "~/.cache/huggingface")) / "hub")
    d = hub / ("models--" + repo_id.replace("/", "--"))
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
        logger.info(f"    deleted downloaded snapshot {d.name}")
    _DOWNLOADED.discard(repo_id)


def list_targets(snap: Path) -> tuple[dict[tuple[str, int], tuple[Path, str]], dict[str, Any]]:
    """(family, layer) -> (shard, key) for every residual-write matrix; plus a quantisation audit."""
    from safetensors import safe_open
    targets: dict[tuple[str, int], tuple[Path, str]] = {}
    audit = {"n_keys": 0, "quantised_keys": [], "dtypes": set(), "moe": False}
    shards = sorted(snap.glob("*.safetensors"))
    if not shards:
        raise FileNotFoundError(f"no safetensors in {snap}")
    for sh in shards:
        with safe_open(str(sh), framework="pt") as f:
            for k in f.keys():
                audit["n_keys"] += 1
                if QUANT_KEY.search(k):
                    audit["quantised_keys"].append(k)
                    continue
                if EXPERT_RE.search(k):
                    audit["moe"] = True
                    continue
                fam = "attn" if O_PROJ_RE.search(k) else ("mlp" if DOWN_RE.search(k) else None)
                if fam is None:
                    continue
                m = LAYER_RE.search(k)
                if not m:
                    continue
                if "vision" in k or "audio" in k:
                    continue
                targets[(fam, int(m.group(1)))] = (sh, k)
    for (fam, L), (sh, k) in list(targets.items())[:2]:
        with safe_open(str(sh), framework="pt") as f:
            audit["dtypes"].add(str(f.get_slice(k).get_dtype()))
    audit["dtypes"] = sorted(audit["dtypes"])
    return targets, audit


def load_matrix(sh: Path, key: str) -> np.ndarray:
    from safetensors import safe_open
    with safe_open(str(sh), framework="pt") as f:
        t = f.get_tensor(key)
    if t.dtype in (torch.float8_e4m3fn, torch.float8_e5m2, torch.int8, torch.uint8, torch.int32):
        raise ValueError(f"quantised tensor dtype {t.dtype}")
    return t.to(torch.float64).numpy()


def spectrum(W: np.ndarray) -> dict[str, Any]:
    d_out, d_in = W.shape
    transposed = d_in < d_out
    Wg = W.T if transposed else W
    G = Wg @ Wg.T
    G = 0.5 * (G + G.T)
    ev, V = np.linalg.eigh(G)                      # ascending
    ev = np.clip(ev, 0.0, None)
    s = np.sqrt(ev)                                # ascending, length min(d_out, d_in)
    Ub, Ut = V[:, :N_BOT_VEC], V[:, ::-1][:, :N_TOP_VEC]
    if transposed:
        def back(Vs: np.ndarray, sv: np.ndarray) -> np.ndarray:
            U = W @ Vs
            n = np.linalg.norm(U, axis=0, keepdims=True)
            n[n == 0] = 1.0
            return U / n
        Ub, Ut = back(Ub, s[:N_BOT_VEC]), back(Ut, s[::-1][:N_TOP_VEC])
    Gl = W @ W.T if transposed else G              # LEFT Gram (d_out x d_out) for the RQ readout
    return {"s": s, "Ub": Ub, "Ut": Ut, "G": Gl.astype(np.float32), "d_out": d_out, "d_in": d_in,
            "transposed": transposed}


def layer_stats(s: np.ndarray, lam_max: float, d_out: int) -> dict[str, Any]:
    num_floor = float(np.sqrt(max(lam_max * 1e-13 * max(d_out, 1), 0.0)))
    t = fit_tail(s, lo=TAIL[0], hi=TAIL[1], scan_max=SCAN, floor=num_floor)
    t1 = fit_tail(s, lo=TAIL_V1[0], hi=TAIL_V1[1], scan_max=SCAN, floor=num_floor)
    rms = float(np.sqrt(np.mean(s ** 2))) if s.size else float("nan")
    n = s.size
    ranks = np.unique(np.clip(np.round(np.logspace(0, np.log10(max(n, 1)), 128)).astype(int) - 1, 0, n - 1))
    return {"botgap": float(s[0] / s[1]) if s[1] > 0 else float("nan"),
            "k_local": float(1 - s[0] / s[1]) if s[1] > 0 else float("nan"),
            "kappa_hat": t["kappa_hat"], "abs_dev": t["abs_dev"], "j_star": t["j_star"],
            "fit_r2": t["fit_r2"], "resid_log": t["resid_log"], "kappa_at0": t["kappa_at0"],
            "kappa_hat_v1window": t1["kappa_hat"], "j_star_v1window": t1["j_star"],
            "s_min_over_rms": float(s[0] / rms) if rms > 0 else float("nan"),
            "s0": float(s[0]), "s1": float(s[1]), "s_rms": rms, "s_max": float(s[-1]),
            "n_unresolved": int(np.sum(s < num_floor)),
            "s_bottom64": [float(x) for x in s[:64]], "spec128_rank": [int(r) for r in ranks],
            "spec128_val": [float(s[r]) for r in ranks]}


def lam_max_mean_proj(Us: list[np.ndarray]) -> float:
    """lambda_max of mean_l U_l U_l^T via the SMALL Gram (exact; O(n k)^2 instead of d^2)."""
    M = np.concatenate([u / np.maximum(np.linalg.norm(u, axis=0, keepdims=True), 1e-30) for u in Us], axis=1)
    sm = M.T @ M
    return float(np.linalg.eigvalsh(sm)[-1] / len(Us))


def windowed(vec: dict[int, np.ndarray], window: int) -> dict[str, float]:
    ls = sorted(vec)
    if not ls:
        return {"w": float("nan"), "all": float("nan")}
    best = float("nan")
    for i in range(0, max(1, len(ls) - window + 1)):
        sub = ls[i:i + window]
        v = lam_max_mean_proj([vec[l] for l in sub])
        best = v if not np.isfinite(best) or v > best else best
    return {"w": best, "all": lam_max_mean_proj([vec[l] for l in ls])}


def read_one(q: dict[str, Any], deadline: float) -> dict[str, Any]:
    t0 = time.time()
    if q["kind"] == "constructed":
        psnap, esnap = snapshot(q["parent"]), snapshot(q["edited"])
        tp, audit = list_targets(psnap)
        te, _ = list_targets(esnap)
        snap_desc = {"parent_snapshot": str(psnap), "edited_snapshot": str(esnap), "kappa": q["kappa"]}
    elif q["kind"] == "forgery":
        snap = snapshot(q["edited"])
        tp, audit = list_targets(snap)
        te = None
        snap_desc = {"snapshot": str(snap), "forgery_of": q["edited"], "forgery_target": q["target"]}
    else:
        snap = snapshot(q["repo_id"], allow_download=bool(q.get("download")))
        tp, audit = list_targets(snap)
        te = None
        snap_desc = {"snapshot": str(snap), "downloaded_then_deleted": q["repo_id"] in _DOWNLOADED}
    if audit["quantised_keys"]:
        raise ValueError(f"quantised checkpoint ({len(audit['quantised_keys'])} quant keys, e.g. "
                         f"{audit['quantised_keys'][0]}) - skipped, never dequantised")
    fams: dict[str, dict[int, dict[str, Any]]] = {"attn": {}, "mlp": {}}
    vecs: dict[str, np.ndarray] = {}
    grams: dict[str, dict[int, np.ndarray]] = {"attn": {}, "mlp": {}}
    ub: dict[str, dict[int, np.ndarray]] = {"attn": {}, "mlp": {}}
    ut: dict[str, dict[int, np.ndarray]] = {"attn": {}, "mlp": {}}
    shapes: dict[str, list[int]] = {}
    repairs: list[dict[str, Any]] = []
    bytes_read = 0
    for (fam, L) in sorted(tp, key=lambda x: (x[0], x[1])):
        if time.time() > deadline:
            raise TimeoutError("per-checkpoint deadline")
        W = load_matrix(*tp[(fam, L)])
        if te is not None:
            We = load_matrix(*te[(fam, L)])
            W = W + float(q["kappa"]) * (We - W)
            del We
        if q["kind"] == "forgery":
            from lanec.forgery import spectral_repair
            W, rinfo = spectral_repair(W, target=q["target"], seed=L)
            # the generator ships the repaired matrix in bf16; read exactly what it ships
            W = torch.from_numpy(W).to(torch.bfloat16).to(torch.float64).numpy()
            repairs.append({"family": fam, "layer": L, **rinfo})
        bytes_read += W.size * 2
        sp = spectrum(W)
        shapes[fam] = [sp["d_out"], sp["d_in"]]
        st = layer_stats(sp["s"], float(sp["s"][-1] ** 2), sp["d_out"])
        fams[fam][L] = st
        ub[fam][L] = sp["Ub"]
        ut[fam][L] = sp["Ut"]
        if fam == "mlp":   # memory: the RQ readout is computed on the always-valid site only
            grams[fam][L] = sp["G"]
        del W, sp
    out: dict[str, Any] = {"id": q["id"], "repo_id": q.get("repo_id"), "kind": q["kind"], "arm": q.get("arm"),
                           "family_signature": q.get("family_signature"), "n_params_est": q.get("n_params_est"),
                           **snap_desc, "audit": {k: v for k, v in audit.items() if k != "quantised_keys"},
                           "shapes": shapes, "per_family": {}}
    for fam in ("attn", "mlp"):
        per = fams[fam]
        if not per:
            continue
        Ls = sorted(per)
        d_out, d_in = shapes[fam]
        u1 = {L: ub[fam][L][:, 0] for L in Ls}
        kh = np.array([per[L]["kappa_hat"] for L in Ls], dtype=float)
        bg = np.array([per[L]["botgap"] for L in Ls], dtype=float)
        # RQ: bottom eigvec of the trace-normalised pooled Gram, then its depression in every layer
        acc = None
        for L in Ls:
            if L not in grams[fam]:
                continue          # attn Grams are not kept (memory); RQ is a down_proj readout
            G = grams[fam][L].astype(np.float64)
            tr = float(np.trace(G))
            if tr > 0:
                acc = G / tr if acc is None else acc + G / tr
        rq = {}
        r = None
        if acc is not None:
            ev, V = np.linalg.eigh(0.5 * (acc + acc.T))
            r = V[:, 0]
            for L in Ls:
                if L not in grams[fam]:
                    continue
                G = grams[fam][L].astype(np.float64)
                mean_sq = float(np.trace(G) / G.shape[0])
                rq[L] = float(r @ G @ r) / mean_sq if mean_sq > 0 else float("nan")
        rqv = np.array([rq.get(L, np.nan) for L in Ls], dtype=float)
        cos_r_umin = [abs(float(r @ u1[L])) for L in Ls] if r is not None else []
        xlc = cross_layer_cosine(u1)
        bsa = {f"k{k}": windowed({L: ub[fam][L][:, :k] for L in Ls}, 8) for k in (1, 2, 4)}
        tsa = {"top1": windowed({L: ut[fam][L][:, :1] for L in Ls}, 8),
               "top2_8": windowed({L: ut[fam][L][:, 1:8] for L in Ls}, 8),
               "top9_16": windowed({L: ut[fam][L][:, 8:16] for L in Ls}, 8)}
        prof = fit_depth_profile(Ls, kh.tolist(), max(Ls) + 1)
        out["per_family"][fam] = {
            "d_out": d_out, "d_in": d_in, "aspect_din_over_dout": d_in / d_out,
            "structurally_valid_bottom_read": bool(d_in / d_out > 1.05),
            "n_layers_read": len(Ls), "layers": Ls,
            "BOTGAP_min": float(np.nanmin(bg)), "BOTGAP_median": float(np.nanmedian(bg)),
            "argmin_BOTGAP_layer": int(Ls[int(np.nanargmin(bg))]),
            "kappa_hat_max": float(np.nanmax(kh)), "kappa_hat_mean": float(np.nanmean(kh)),
            "kappa_hat_median": float(np.nanmedian(kh)),
            "abs_dev_min": float(np.nanmin([per[L]["abs_dev"] for L in Ls])),
            "kappa_hat_v1window_max": float(np.nanmax([per[L]["kappa_hat_v1window"] for L in Ls])),
            "s_min_over_rms_median": float(np.nanmedian([per[L]["s_min_over_rms"] for L in Ls])),
            "XLC": xlc["xlc"], "XLC_max": xlc["xlc_max"], "XLC_p90": xlc["xlc_p90"],
            "XLC_iso_null": xlc["iso_null"],
            "BSA_w8": bsa["k1"]["w"], "BSA_all": bsa["k1"]["all"],
            "BSA_w8_k2": bsa["k2"]["w"], "BSA_w8_k4": bsa["k4"]["w"],
            "TSA_w8_top1": tsa["top1"]["w"], "TSA_w8_top2_8": tsa["top2_8"]["w"],
            "TSA_w8_top9_16": tsa["top9_16"]["w"],
            "RQ_pooled": float(np.nanmedian(rqv)) if rqv.size else float("nan"),
            "RQ_min": float(np.nanmin(rqv)) if rqv.size else float("nan"),
            "RQ_pooled_log10": float(np.log10(max(float(np.nanmedian(rqv)), 1e-300))) if rqv.size else float("nan"),
            "cos_pooled_dir_vs_umin_mean": float(np.mean(cos_r_umin)) if cos_r_umin else float("nan"),
            "depth_profile": prof,
            "per_layer": {str(L): {**per[L], "rq": rq.get(L)} for L in Ls},
        }
        vecs[f"{fam}_bot"] = np.stack([ub[fam][L] for L in Ls]).astype(np.float16)
        vecs[f"{fam}_top"] = np.stack([ut[fam][L] for L in Ls]).astype(np.float16)
        vecs[f"{fam}_layers"] = np.array(Ls, dtype=np.int32)
        if r is not None:
            vecs[f"{fam}_pooled_dir"] = r.astype(np.float32)
    if "attn" in out["per_family"] and "mlp" in out["per_family"]:
        a = {L: ub["attn"][L][:, 0] for L in ub["attn"]}
        b = {L: ub["mlp"][L][:, 0] for L in ub["mlp"]}
        xf = cross_family_cosine(a, b)
        out["XFC"] = xf.get("xfc")
        out["XFC_per_layer"] = xf.get("per_layer")
    if repairs:
        out["forgery_repairs"] = repairs
        out["forgery_n_repaired"] = int(sum(r["repaired"] for r in repairs))
    out["seconds"] = time.time() - t0
    out["bytes_read_bf16_equiv"] = bytes_read
    out["finished_unix"] = time.time()
    np.savez_compressed(VE / f"{q['id']}.npz", **vecs)
    del grams, ub, ut
    gc.collect()
    return out


def jsafe(o: Any) -> Any:
    if isinstance(o, dict):
        return {str(k): jsafe(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsafe(v) for v in o]
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deadline_unix", type=float, default=0.0)
    ap.add_argument("--per_ckpt_minutes", type=float, default=30.0)
    ap.add_argument("--max_params", type=float, default=4.6e9)
    args = ap.parse_args()
    torch.set_num_threads(1)
    resource.setrlimit(resource.RLIMIT_AS, (24 * 1024 ** 3, 24 * 1024 ** 3))
    tried: set[str] = set()
    while True:
        queue = json.loads(QUEUE.read_text())
        todo = [q for q in queue if q["id"] not in tried and not (CK / f"{q['id']}.json").exists()
                and not (CK / f"{q['id']}.failed.json").exists()
                and (q.get("n_params_est") or 0) <= args.max_params]
        if not todo:
            logger.info("weights queue exhausted")
            break
        if args.deadline_unix and time.time() > args.deadline_unix:
            logger.warning(f"deadline: {len(todo)} checkpoints not started")
            break
        q = todo[0]
        tried.add(q["id"])
        logger.info(f"[{q['id']}] kind={q['kind']} arm={q.get('arm')} ({len(todo) - 1} more)")
        try:
            out = read_one(q, time.time() + 60 * args.per_ckpt_minutes)
            tmp = CK / f"{q['id']}.json.tmp"
            tmp.write_text(json.dumps(jsafe(out), allow_nan=False))
            tmp.replace(CK / f"{q['id']}.json")
            m = out["per_family"].get("mlp", {})
            logger.info(f"[{q['id']}] OK {out['seconds']:.0f}s | mlp: BOTGAP_min={m.get('BOTGAP_min'):.3g} "
                        f"kappa_hat_max={m.get('kappa_hat_max'):.3g} XLC={m.get('XLC'):.3g} "
                        f"BSA_w8={m.get('BSA_w8'):.3g} RQ={m.get('RQ_pooled'):.3g} XFC={out.get('XFC')}")
        except Exception as e:  # noqa: BLE001 - one bad repo must not kill the panel
            logger.exception(f"[{q['id']}] FAILED: {e}")
            (CK / f"{q['id']}.failed.json").write_text(json.dumps({"id": q["id"], "error": repr(e)[:1500],
                                                                    "queue_entry": q}))
        if q.get("repo_id"):
            drop_download(q["repo_id"])
        gc.collect()
        try:   # hand freed heap back to the OS (shared 16 GB cgroup; OOM kills measured)
            import ctypes
            ctypes.CDLL("libc.so.6").malloc_trim(0)
        except OSError:
            pass


if __name__ == "__main__":
    main()

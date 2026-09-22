#!/usr/bin/env python3
"""GROUND TRUTH for the parent-free estimator on REAL published edits (parent-BASED; never used as a readout).

For an edited checkpoint E whose parent P is in the run-shared cache, every residual-write matrix difference
dW = W_E - W_P is examined:
    rank-one share  = sigma_1(dW)^2 / ||dW||_F^2            (is the edit a single-direction projection?)
    r               = top left singular vector of dW        (the direction the tool removed)
    kappa_true      = -(r^T dW)(r^T W_P)^T / ||r^T W_P||^2   (W_E = (I - kappa r r^T) W_P  =>  exact kappa; >1 = over-ablation)
    cos_parentfree  = max_k |<r, u_k>| over the 4 bottom left singular vectors the PARENT-FREE read recovered
Summaries: per-family kappa_true median/max, the depth profile (heretic ships layer-position-varying weights, >1
possible), the cross-layer sharing of the true directions, and - the point - the parent-free kappa_hat on the same
matrices. The parent is chosen EMPIRICALLY among candidates (card base_model fields name the root, not the parent):
the candidate whose difference on a probe matrix is smallest.
Output: results/true_kappa/<edited>.json.
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
from stage1_weights_v2 import drop_download, list_targets, snapshot  # noqa: E402

OUT = WS / "results" / "true_kappa"
OUT.mkdir(parents=True, exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(WS / "logs" / "stage1b_true_kappa.log"), rotation="30 MB", level="DEBUG")

PAIRS: list[tuple[str, list[str]]] = [
    ("huihui-ai/Huihui-Qwen3-0.6B-abliterated-v2", ["Qwen/Qwen3-0.6B"]),
    ("mlabonne/Qwen3-0.6B-abliterated", ["Qwen/Qwen3-0.6B"]),
    ("p-e-w/Qwen3-0.6B-heretic", ["Qwen/Qwen3-0.6B", "Qwen/Qwen3-0.6B-Base"]),
    ("DavidAU/gemma-3-1b-it-heretic-extreme-uncensored-abliterated", ["unsloth/gemma-3-1b-it"]),
    ("mylesgoose/Llama-3.2-1B-Instruct-abliterated", ["unsloth/Llama-3.2-1B-Instruct", "alpindale/Llama-3.2-1B-Instruct"]),
    ("huihui-ai/Huihui-Qwen3-1.7B-abliterated-v2", ["Qwen/Qwen3-1.7B"]),
    ("vrhvnsky/Qwen3-0.6B-heretic-decensored", ["Qwen/Qwen3-0.6B", "Qwen/Qwen3-0.6B-Base"]),
    ("DavidAU/Qwen3-0.6B-heretic-abliterated-uncensored", ["Qwen/Qwen3-0.6B"]),
    ("Vikhrmodels/Vikhr-Llama-3.2-1B-Instruct-abliterated", ["Vikhrmodels/Vikhr-Llama-3.2-1B-Instruct"]),
    ("DreamFast/qwen3-4b-heretic", ["Qwen/Qwen3-4B"]),
    ("mlabonne/Qwen3-4B-abliterated", ["Qwen/Qwen3-4B"]),
    ("mlabonne/Qwen3-1.7B-abliterated", ["Qwen/Qwen3-1.7B"]),
    ("soob3123/amoral-gemma3-1B-v2", ["unsloth/gemma-3-1b-it"]),
    ("UnfilteredAI/DAN-Qwen3-1.7B", ["Qwen/Qwen3-1.7B"]),
    ("MagicalAlchemist/Qwen3-1.7B-Magic_decensored", ["Qwen/Qwen3-1.7B", "Qwen/Qwen3-1.7B-Base"]),
    ("Goekdeniz-Guelmez/Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1", ["Qwen/Qwen2.5-1.5B-Instruct"]),
    ("Novaciano/Amoral_Christmas-3.2-1B", ["unsloth/Llama-3.2-1B-Instruct"]),
]
# replication-panel edits (weights fetched on demand and deleted right after; parents already cached)
PAIRS_DOWNLOAD: list[tuple[str, list[str]]] = [
    ("huihui-ai/Qwen2.5-0.5B-Instruct-abliterated-v3", ["Qwen/Qwen2.5-0.5B-Instruct"]),
    ("huihui-ai/Qwen2.5-0.5B-Instruct-abliterated-SFT", ["Qwen/Qwen2.5-0.5B-Instruct"]),
    ("mylesgoose/Llama-3.2-1B-Instruct-abliterated2", ["unsloth/Llama-3.2-1B-Instruct"]),
    ("mylesgoose/Llama-3.2-1B-Instruct-abliterated3", ["unsloth/Llama-3.2-1B-Instruct"]),
    ("IlyaGusev/gemma-2-2b-it-abliterated", ["google/gemma-2-2b-it"]),
    ("UnfilteredAI/UNfilteredAI-1B", ["unsloth/Llama-3.2-1B-Instruct"]),
]


def mat(sh: Path, key: str) -> torch.Tensor:
    from safetensors import safe_open
    with safe_open(str(sh), framework="pt") as f:
        return f.get_tensor(key).to(torch.float32)


def top_left(dW: torch.Tensor, iters: int = 12) -> tuple[torch.Tensor, float]:
    """Top left singular vector of dW by power iteration on dW dW^T; returns (u, sigma_1)."""
    g = torch.Generator().manual_seed(0)
    x = torch.randn(dW.shape[0], generator=g)
    for _ in range(iters):
        x = dW @ (dW.T @ x)
        n = torch.linalg.vector_norm(x)
        if n == 0:
            break
        x = x / n
    s1 = float(torch.linalg.vector_norm(dW.T @ x))
    return x, s1


def analyse_pair(edited: str, cands: list[str], download: bool = False) -> dict[str, Any]:
    t0 = time.time()
    esnap = snapshot(edited, allow_download=download)
    te, _ = list_targets(esnap)
    probe = sorted(k for k in te if k[0] == "mlp")[len([k for k in te if k[0] == "mlp"]) // 2]
    best, best_rel = None, None
    for c in cands:
        try:
            psnap = snapshot(c)
        except Exception:  # noqa: BLE001 - candidate not cached
            continue
        tp, _ = list_targets(psnap)
        if probe not in tp:
            continue
        a, b = mat(*te[probe]), mat(*tp[probe])
        if a.shape != b.shape:
            continue
        rel = float(torch.linalg.matrix_norm(a - b) / torch.linalg.matrix_norm(b))
        if best_rel is None or rel < best_rel:
            best, best_rel, best_tp = c, rel, tp
    if best is None:
        raise FileNotFoundError(f"no cached parent candidate for {edited}")
    vz = WS / "results" / "vecs_v2" / f"{edited.replace('/', '__')}.npz"
    vecs = np.load(vz) if vz.exists() else None
    per: dict[str, list[dict[str, Any]]] = {"attn": [], "mlp": []}
    for (fam, L) in sorted(te):
        if (fam, L) not in best_tp:
            continue
        We, Wp = mat(*te[(fam, L)]), mat(*best_tp[(fam, L)])
        dW = We - Wp
        fro2 = float((dW * dW).sum())
        if fro2 == 0:
            per[fam].append({"layer": L, "unchanged": True})
            continue
        r, s1 = top_left(dW)
        rWp = r @ Wp
        rdW = r @ dW
        kappa = float(-(rdW @ rWp) / max(float(rWp @ rWp), 1e-30))
        rec = {"layer": L, "rel_frob": float(np.sqrt(fro2) / float(torch.linalg.matrix_norm(Wp))),
               "rank_one_share": float(s1 ** 2 / fro2), "kappa_true": kappa, "abs_dev_true": abs(1 - kappa)}
        if vecs is not None and f"{fam}_bot" in vecs.files:
            Ls = list(vecs[f"{fam}_layers"])
            if L in Ls:
                ub = vecs[f"{fam}_bot"][Ls.index(L)].astype(np.float32)   # (d, 4)
                rn = r.numpy()
                rec["cos_true_dir_vs_parentfree_bottom1"] = float(abs(rn @ ub[:, 0]))
                rec["cos_true_dir_vs_parentfree_bottom4_max"] = float(np.max(np.abs(rn @ ub)))
        per[fam].append(rec)
        per[fam][-1]["_r"] = r.numpy().astype(np.float32)
        del We, Wp, dW
    summ: dict[str, Any] = {}
    for fam, rows in per.items():
        rr = [x for x in rows if not x.get("unchanged")]
        if not rr:
            summ[fam] = {"n_changed": 0}
            continue
        k = np.array([x["kappa_true"] for x in rr])
        R = np.stack([x["_r"] for x in rr])
        C = np.abs(R @ R.T)
        iu = np.triu_indices(len(rr), 1)
        summ[fam] = {"n_changed": len(rr), "n_layers": len(rows),
                     "rank_one_share_median": float(np.median([x["rank_one_share"] for x in rr])),
                     "kappa_true_median": float(np.median(k)), "kappa_true_max": float(k.max()),
                     "kappa_true_min": float(k.min()), "frac_layers_kappa_gt_1": float(np.mean(k > 1.0)),
                     "peak_layer_frac": float(rr[int(np.argmax(k))]["layer"] / max(len(rows) - 1, 1)),
                     "true_direction_XLC": float(C[iu].mean()) if len(rr) > 1 else None,
                     "cos_true_vs_parentfree_bottom1_median": float(np.median([x.get("cos_true_dir_vs_parentfree_bottom1", np.nan) for x in rr])),
                     "cos_true_vs_parentfree_bottom4max_median": float(np.median([x.get("cos_true_dir_vs_parentfree_bottom4_max", np.nan) for x in rr]))}
        for x in rows:
            x.pop("_r", None)
    return {"edited": edited, "parent_chosen": best, "parent_candidates": cands, "probe_rel_frob": best_rel,
            "summary": summ, "per_layer": per, "seconds": time.time() - t0,
            "note": "PARENT-BASED ground truth for calibration only; the readouts under test never see the parent."}


@logger.catch(reraise=True)
def main() -> None:
    torch.set_num_threads(1)
    todo = [(e, c, False) for e, c in PAIRS] + ([(e, c, True) for e, c in PAIRS_DOWNLOAD] if "--download" in sys.argv else [])
    for edited, cands, dl in todo:
        out = OUT / f"{edited.replace('/', '__')}.json"
        if out.exists() or (OUT / f"{edited.replace('/', '__')}.failed.json").exists():
            continue
        try:
            res = analyse_pair(edited, cands, download=dl)
            if dl:
                drop_download(edited)
            out.write_text(json.dumps(res, indent=1, allow_nan=True))
            s = res["summary"].get("mlp", {})
            logger.info(f"{edited}: parent={res['parent_chosen']} mlp kappa_true median {s.get('kappa_true_median')} "
                        f"max {s.get('kappa_true_max')} rank1 {s.get('rank_one_share_median')} "
                        f"cos(true, parent-free bottom) {s.get('cos_true_vs_parentfree_bottom1_median')} ({res['seconds']:.0f}s)")
        except Exception as e:  # noqa: BLE001
            logger.exception(f"{edited}: {e}")
            (OUT / f"{edited.replace('/', '__')}.failed.json").write_text(json.dumps({"error": repr(e)[:500]}))


if __name__ == "__main__":
    main()

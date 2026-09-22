"""Zero-prompt, parent-free WEIGHT readouts, read shard-by-shard.

The model is never constructed: one safetensors shard is opened at a time with
`safe_open`, the residual-WRITE matrices (o_proj / down_proj) are pulled out, their
per-layer left-singular projectors are accumulated, and the shard is closed. Peak RAM is
one shard, so this scales to 32B+ regardless of the box.

ATTRIBUTION — THIS STATISTIC IS PRIOR ART. The Jorak Model Scanner
(JolanMc/Jorak, modelscanner/metrics/jorak.py::subspace_signature()) already computes the
sum of per-layer bottom-k left singular projectors on exactly o_proj/down_proj, with a band
variant. What is added here is honest-panel calibration on real trained weights, a bf16
threshold, and the TOP-k INJECTION arm (TSA) that Jorak does not implement.
"""
from __future__ import annotations

import gc
import json
import re
import time
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import torch
from loguru import logger

# Residual-WRITE matrices: everything that writes back into the residual stream.
WRITE_PATTERNS = (
    re.compile(r"\.self_attn\.o_proj\.weight$"),
    re.compile(r"\.mlp\.down_proj\.weight$"),
    # name variants seen on non-Qwen families
    re.compile(r"\.attention\.wo\.weight$"),
    re.compile(r"\.self_attn\.dense\.weight$"),
    re.compile(r"\.mlp\.(c_proj|fc2|w2|down_proj)\.weight$"),
    re.compile(r"\.attn\.(c_proj|out_proj)\.weight$"),
)
LAYER_RE = re.compile(r"layers?\.(\d+)\.")

BSA_FLAG_THRESHOLD = 0.35        # pre-registered, from simulation
BOTGAP_BF16_SEPARATOR = 0.10     # bf16 rounding lifts a projected matrix to ~0.0103, never to 0
K_SUBSPACE = 1                   # pre-registered bottom/top-k
WINDOW = 8                       # sliding contiguous window for BSA_w8 / TSA_w8
RANK_BANDS = ((0, 1), (0, 4), (4, 16), (16, 64))


def is_write_matrix(key: str) -> bool:
    return any(p.search(key) for p in WRITE_PATTERNS)


def layer_of(key: str) -> int | None:
    m = LAYER_RE.search(key)
    return int(m.group(1)) if m else None


def component_of(key: str) -> str:
    if "o_proj" in key or ".wo." in key or "out_proj" in key or "self_attn.dense" in key:
        return "attn"
    return "mlp"


_EIGH_DEVICE: str | None = None


def _pick_eigh_device() -> str:
    """The weight pass is pure linear algebra and the GPU is idle during it. On this box a
    2560x9728 Gram + 2560x2560 eigh costs ~5 s on 8 CPU cores and ~0.1 s on the card, which is
    the difference between a 6-minute and a 20-second weight pass per checkpoint."""
    global _EIGH_DEVICE
    if _EIGH_DEVICE is None:
        import os as _os
        pref = _os.environ.get("LANEC_EIGH_DEVICE", "cpu")   # CPU by default: this GPU is SHARED
        if pref == "cpu":
            _EIGH_DEVICE = "cpu"
            return _EIGH_DEVICE
        try:
            if torch.cuda.is_available():
                a = torch.eye(8, device="cuda")
                torch.linalg.eigh(a)
                _EIGH_DEVICE = "cuda"
            else:
                _EIGH_DEVICE = "cpu"
        except (RuntimeError, AssertionError) as exc:
            logger.warning(f"CUDA eigh unavailable ({exc}); falling back to CPU")
            _EIGH_DEVICE = "cpu"
    return _EIGH_DEVICE


def _gram_eig(W: torch.Tensor) -> tuple[np.ndarray, np.ndarray]:
    """Ascending eigen-decomposition of W W^T.

    eigh on the d_model x d_model Gram is far cheaper than a full SVD of a d_model x d_ff matrix
    and gives the same LEFT singular subspace.
    """
    dev = _pick_eigh_device()
    Wf = W.detach().to(torch.float32)
    try:
        Wg = Wf.to(dev, non_blocking=True)
        G = Wg @ Wg.T
        G = 0.5 * (G + G.T)  # symmetrise against fp round-off
        evals, evecs = torch.linalg.eigh(G)
        out = evals.cpu().numpy(), evecs.cpu().numpy()
        del Wg, G, evals, evecs
        if dev == "cuda":
            torch.cuda.empty_cache()
        return out
    except (RuntimeError, torch.OutOfMemoryError) as exc:  # noqa: F821
        logger.warning(f"eigh on {dev} failed ({type(exc).__name__}); retrying on CPU")
        if dev == "cuda":
            torch.cuda.empty_cache()
        G = Wf @ Wf.T
        G = 0.5 * (G + G.T)
        evals, evecs = torch.linalg.eigh(G)
        return evals.cpu().numpy(), evecs.cpu().numpy()


def layer_basis(W: torch.Tensor, k: int = K_SUBSPACE, band_max: int = max(h for _, h in RANK_BANDS)
                ) -> dict[str, Any]:
    """Bottom-k and top-k left singular BASES (d x k), plus the bottom spectral gap.

    The d x d projectors are NEVER materialised. lambda_max of a mean of rank-k projectors
    equals lambda_max of a (k*n) x (k*n) Gram matrix (see `_lambda_max_of_mean_projector`), so
    storing the d x d outer products would cost ~26 MB per layer and an O(d^3) eigensolve per
    window for no information at all.
    """
    evals, evecs = _gram_eig(W)
    evals = np.clip(evals, 0.0, None)
    sv = np.sqrt(evals)                       # singular values, ASCENDING
    botgap = float(sv[0] / sv[1]) if sv.shape[0] > 1 and sv[1] > 0 else float("nan")
    d = int(evecs.shape[0])
    return {
        "B": evecs[:, :k].astype(np.float32),                       # bottom-k basis
        "T": evecs[:, -k:].astype(np.float32),                      # top-k basis
        "V_desc": evecs[:, ::-1][:, :min(band_max, d)].astype(np.float32),  # descending, truncated
        "botgap": botgap,
        "sv_min": float(sv[0]),
        "sv_max": float(sv[-1]),
        "d": d,
    }


def _lambda_max_of_mean_projector(bases: list[np.ndarray], weights_per: list[float] | None = None
                                  ) -> float:
    """lambda_max( (1/n) * sum_i  P_i ) where P_i = B_i B_i^T and B_i has ORTHONORMAL columns.

    Stack the (scaled) bases into M = [c_1 B_1, ..., c_n B_n]  (d x sum_i k_i). Then
    sum_i c_i^2 B_i B_i^T = M M^T, whose non-zero spectrum equals that of the SMALL Gram matrix
    M^T M of size (sum_i k_i) x (sum_i k_i). For k=1 and a window of 8 that is an 8x8 eigensolve
    instead of a 2560x2560 one.
    """
    if not bases:
        return float("nan")
    n = len(bases)
    cols = []
    for i, B in enumerate(bases):
        c = np.sqrt((weights_per[i] if weights_per else 1.0) / n)
        cols.append(B * c)
    M = np.concatenate(cols, axis=1)
    G = M.T @ M
    G = 0.5 * (G + G.T)
    return float(np.linalg.eigvalsh(G)[-1])


def _window_max_bases(bases: list[np.ndarray], window: int,
                      weights_per: list[float] | None = None) -> tuple[float, int]:
    n = len(bases)
    if n == 0:
        return float("nan"), -1
    w = min(window, n)
    best, best_i = -np.inf, -1
    for i in range(n - w + 1):
        wp = weights_per[i:i + w] if weights_per else None
        val = _lambda_max_of_mean_projector(bases[i:i + w], wp)
        if val > best:
            best, best_i = val, i
    return float(best), int(best_i)


def iter_shards(model_dir: Path) -> Iterator[Path]:
    shards = sorted(model_dir.rglob("*.safetensors"))
    for s in shards:
        yield s


def weight_readouts(
    model_dir: Path, k: int = K_SUBSPACE, window: int = WINDOW, max_layers: int | None = None
) -> dict[str, Any]:
    """W1..W4 from ONE streaming pass over the shards. Never constructs the model."""
    from safetensors import safe_open

    per_layer: dict[tuple[int, str], dict[str, Any]] = {}
    n_tensors = 0
    shards = list(iter_shards(model_dir))
    if not shards:
        raise FileNotFoundError(f"no *.safetensors under {model_dir}")
    for si, shard in enumerate(shards):
        _ts = time.time()
        try:
            with safe_open(str(shard), framework="pt", device="cpu") as f:
                for key in f.keys():
                    if not is_write_matrix(key):
                        continue
                    li = layer_of(key)
                    if li is None:
                        continue
                    if max_layers is not None and li >= max_layers:
                        continue
                    W = f.get_tensor(key)
                    if W.ndim != 2:
                        del W
                        continue
                    res = layer_basis(W, k=k)
                    res["dtype"] = str(W.dtype)
                    res["shape"] = list(W.shape)
                    per_layer[(li, component_of(key))] = res
                    n_tensors += 1
                    del W
        except (OSError, RuntimeError, ValueError) as exc:
            logger.error(f"shard {shard.name} failed: {exc}")
            continue
        logger.debug(f"  shard {si+1}/{len(shards)} {shard.name}: {time.time()-_ts:.1f}s "
                     f"({len(per_layer)} write matrices so far)")
        gc.collect()
    if not per_layer:
        raise ValueError(f"no residual-write matrices resolved in {model_dir}")
    out = _assemble(per_layer, window)
    out.update({"n_write_matrices": n_tensors,
                "dtype": next(iter(per_layer.values()))["dtype"],
                "d_model": next(iter(per_layer.values()))["d"]})
    per_layer.clear()
    gc.collect()
    return out


def _assemble(per_layer: dict[tuple[int, str], dict[str, Any]], window: int) -> dict[str, Any]:
    out: dict[str, Any] = {}
    layers = sorted({li for li, _ in per_layer})
    out["n_layers_seen"] = len(layers)
    for comp in ("attn", "mlp", "both"):
        keys = [(li, c) for li in layers for c in ("attn", "mlp")
                if (li, c) in per_layer and (comp == "both" or c == comp)]
        if not keys:
            continue
        bots = [per_layer[kk]["B"] for kk in keys]
        tops = [per_layer[kk]["T"] for kk in keys]
        gaps = [per_layer[kk]["botgap"] for kk in keys]
        bsa_w, bsa_i = _window_max_bases(bots, window)
        tsa_w, tsa_i = _window_max_bases(tops, window)
        suffix = "" if comp == "both" else f"_{comp}"
        out[f"BSA_w{window}{suffix}"] = bsa_w                            # W1
        out[f"BSA_w{window}_argmax{suffix}"] = bsa_i
        out[f"BSA_all{suffix}"] = _lambda_max_of_mean_projector(bots)    # W2
        out[f"TSA_w{window}{suffix}"] = tsa_w                            # W3
        out[f"TSA_w{window}_argmax{suffix}"] = tsa_i
        out[f"TSA_all{suffix}"] = _lambda_max_of_mean_projector(tops)
        finite = [g for g in gaps if np.isfinite(g)]
        out[f"BOTGAP_min{suffix}"] = float(np.min(finite)) if finite else None   # W4
        out[f"BOTGAP_median{suffix}"] = float(np.median(finite)) if finite else None

    # Rank-band TSA sweep: a SHARED injection need not reach the top-1 subspace on a heavy-tailed
    # spectrum, so the whole profile is reported rather than one operating point.
    all_keys = [(li, c) for li in layers for c in ("attn", "mlp") if (li, c) in per_layer]
    for lo, hi in RANK_BANDS:
        band = []
        for kk in all_keys:
            V = per_layer[kk]["V_desc"]
            if V.shape[1] <= lo:
                continue
            Vb = V[:, lo:min(hi, V.shape[1])]
            if Vb.shape[1]:
                band.append(Vb / np.sqrt(Vb.shape[1]))   # normalise so P/m has unit trace-per-dim
        if band:
            bw, _ = _window_max_bases(band, window)
            out[f"TSA_band_{lo}_{hi}_w{window}"] = bw
            out[f"TSA_band_{lo}_{hi}_all"] = _lambda_max_of_mean_projector(band)
    out["per_layer_botgap"] = {f"{li}_{c}": per_layer[(li, c)]["botgap"]
                               for li, c in all_keys}
    out["flagged_bsa"] = bool(np.isfinite(out.get(f"BSA_w{window}", np.nan))
                              and out[f"BSA_w{window}"] > BSA_FLAG_THRESHOLD)
    out["flagged_botgap"] = bool(out.get("BOTGAP_min") is not None
                                 and out["BOTGAP_min"] < BOTGAP_BF16_SEPARATOR)
    out["thresholds"] = {"BSA_flag": BSA_FLAG_THRESHOLD, "BOTGAP_separator": BOTGAP_BF16_SEPARATOR,
                         "k": K_SUBSPACE, "window": window}
    out["attribution"] = ("bottom-k left-singular projector sum on o_proj/down_proj is PRIOR ART: "
                          "Jorak Model Scanner (JolanMc/Jorak), modelscanner/metrics/jorak.py::"
                          "subspace_signature(). TOP-k injection arm (TSA) and the bf16/real-weight "
                          "calibration are this study's additions.")
    return out


def weight_readouts_from_state_dict(sd: dict[str, torch.Tensor], k: int = K_SUBSPACE,
                                    window: int = WINDOW) -> dict[str, Any]:
    """Same statistics computed from an IN-MEMORY state dict (used for the ROSI-edited model,
    which is never written to disk)."""
    per_layer: dict[tuple[int, str], dict[str, Any]] = {}
    for key, W in sd.items():
        if not is_write_matrix(key) or W.ndim != 2:
            continue
        li = layer_of(key)
        if li is None:
            continue
        per_layer[(li, component_of(key))] = layer_basis(W, k=k)
    if not per_layer:
        raise ValueError("no residual-write matrices in state dict")
    out = _assemble(per_layer, window)
    out["n_write_matrices"] = len(per_layer)
    per_layer.clear(); gc.collect()
    return out


# ---------------------------------------------------------------- simulation reference
def simulate_reference(seed: int = 0, d: int = 256, fan_in: int = 1024, L: int = 28) -> dict[str, Any]:
    """Reproduce the pre-registered simulated reference values (Tier-0 test T0.2)."""
    rng = np.random.default_rng(seed)

    def stack(heavy: bool = False) -> list[torch.Tensor]:
        out = []
        for _ in range(L):
            W = rng.standard_normal((d, fan_in)) / np.sqrt(fan_in)
            if heavy:
                W = W * rng.standard_t(df=3, size=(d, 1))
            out.append(torch.tensor(W, dtype=torch.float32))
        return out

    def stats(ws: list[torch.Tensor]) -> dict[str, float]:
        projs = [layer_basis(w) for w in ws]
        bsa, _ = _window_max_bases([p["B"] for p in projs], WINDOW)
        gaps = [p["botgap"] for p in projs]
        return {"BSA_w8": float(bsa), "BOTGAP_min": float(np.min(gaps))}

    res: dict[str, Any] = {}
    res["honest_gaussian"] = stats(stack(False))
    res["honest_heavy"] = stats(stack(True))

    # shared abliteration, kappa = 1: one direction projected out of EVERY layer
    r = rng.standard_normal(d); r /= np.linalg.norm(r)
    P = np.eye(d) - np.outer(r, r)
    base = stack(False)
    shared = [torch.tensor(P @ w.numpy(), dtype=torch.float32) for w in base]
    res["shared_abliteration_k1"] = stats(shared)
    shared_bf16 = [w.to(torch.bfloat16).to(torch.float32) for w in shared]
    res["shared_abliteration_k1_bf16"] = stats(shared_bf16)

    # per-layer abliteration: a DIFFERENT direction per layer. BSA is definitionally blind.
    per = []
    for w in base:
        rl = rng.standard_normal(d); rl /= np.linalg.norm(rl)
        per.append(torch.tensor((np.eye(d) - np.outer(rl, rl)) @ w.numpy(), dtype=torch.float32))
    res["per_layer_abliteration_k1"] = stats(per)

    # band abliteration: shared direction on the middle 50% of layers only
    half = [torch.tensor(P @ w.numpy(), dtype=torch.float32) if L // 4 <= i < 3 * L // 4 else w
            for i, w in enumerate(base)]
    res["band50_abliteration_k1"] = stats(half)
    return res

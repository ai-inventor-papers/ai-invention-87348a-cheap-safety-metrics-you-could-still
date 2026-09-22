"""PARENT-FREE, PROMPT-FREE RECOVERY OF AN ABLITERATION RECIPE FROM WEIGHTS ALONE.

What is NEW here (everything else is inherited from lanec/weights.py and must be CALLED, not rewritten):
  (a) `ranged` — a partial/ranged safetensors reader that pulls ONLY the residual-write matrices
      (o_proj / down_proj) out of a Hub repo over HTTP Range requests, never downloading a whole repo.
  (b) `spectrum_stats` / `fit_tail` — the realised-ablation-strength estimator: a quadratic-in-log tail
      fit of the healthy bottom spectrum, extrapolated to rank 0, with an INDEX SCAN over j in [0,15]
      because an over-ablated matrix (kappa > 1) does NOT put the suppressed value at rank 0.
  (c) `cross_layer_cosine` — the XLC sharing statistic, within- and cross-matrix-family.
  (d) `fit_depth_profile` — the per-layer strength profile fit that recovers a tool's own
      layer-position hyperparameters (peak value, peak location, width) from the weights alone.

IDENTIFIABILITY, STATED UP FRONT.  Abliteration is W' = (I - kappa r r^T) W, so r^T W' = (1-kappa) r^T W:
exactly one left-singular direction is scaled by |1 - kappa|.  The SIGN of (1 - kappa) is NOT recoverable
from a spectrum, so kappa and (2 - kappa) are indistinguishable parent-free.  We therefore report
    ratio_min  = s[j*] / s_predicted(j*)   in [0, 1]   the realised suppression ratio
    kappa_hat  = 1 - ratio_min             in [0, 1]   the realised strength on the kappa <= 1 branch
    abs_dev    = |1 - kappa_hat| = ratio_min
and say plainly that over- and under-ablation of equal magnitude map to the same kappa_hat.
"""
from __future__ import annotations

import json
import math
import os
import re
import struct
from pathlib import Path
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

import numpy as np
import requests
from loguru import logger

# --------------------------------------------------------------------------------------
# (a) RANGED SAFETENSORS READER
# --------------------------------------------------------------------------------------

HF_ENDPOINT = os.environ.get("HF_ENDPOINT", "https://huggingface.co")
_QUANT_MARKERS = re.compile(r"(gptq|awq|fp8|int4|int8|bnb|4bit|8bit|gguf|mlx|onnx|quantiz)", re.I)

O_PROJ_RE = re.compile(r"\.(self_attn\.o_proj|attention\.wo|self_attn\.dense|attn\.(c_proj|out_proj))\.weight$")
DOWN_RE = re.compile(r"\.(mlp\.(down_proj|c_proj|fc2|w2)|feed_forward\.w2)\.weight$")
LAYER_RE = re.compile(r"(?:^|\.)layers?\.(\d+)\.")
EXPERT_RE = re.compile(r"experts\.(\d+)\.")

_DTYPE_MAP = {
    "F64": (np.float64, 8), "F32": (np.float32, 4), "F16": (np.float16, 2),
    "BF16": ("bf16", 2), "I64": (np.int64, 8), "I32": (np.int32, 4),
    "I16": (np.int16, 2), "I8": (np.int8, 1), "U8": (np.uint8, 1), "BOOL": (np.bool_, 1),
}


class RangedReadError(RuntimeError):
    """A repo could not be read over HTTP Range requests."""


def _session(token: str | None) -> requests.Session:
    s = requests.Session()
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
    s.headers["User-Agent"] = "lanec-ranged/0.2"
    return s


def local_snapshot(repo_id: str) -> Path | None:
    """The run-shared HF cache already holds many panel checkpoints. Reading a tensor's byte span
    from local disk is far faster than an HTTP Range request (measured 3.6 MB/s on this box), so the
    planner always looks locally first and falls back to the Hub."""
    root = os.environ.get("HF_HUB_CACHE") or os.environ.get("HUGGINGFACE_HUB_CACHE")
    if not root:
        return None
    d = Path(root) / ("models--" + repo_id.replace("/", "--")) / "snapshots"
    if not d.is_dir():
        return None
    snaps = [x for x in d.iterdir() if x.is_dir()]
    if not snaps:
        return None
    return max(snaps, key=lambda x: x.stat().st_mtime)


def _read_local_header(fp: Path) -> tuple[dict, int]:
    with fp.open("rb") as f:
        raw = f.read(8)
        if len(raw) < 8:
            raise RangedReadError(f"{fp}: truncated safetensors header length")
        (n_header,) = struct.unpack("<Q", raw)
        if not (0 < n_header < 200_000_000):
            raise RangedReadError(f"{fp}: implausible header length {n_header}")
        hdr = json.loads(f.read(n_header).decode("utf-8"))
    return hdr, 8 + n_header


def _resolve_url(repo_id: str, filename: str, revision: str = "main") -> str:
    return f"{HF_ENDPOINT}/{repo_id}/resolve/{revision}/{filename}"


def _get_range(sess: requests.Session, url: str, start: int, end_inclusive: int,
               timeout: float = 60.0, retries: int = 3) -> bytes:
    """One HTTP Range request, with retries. `end_inclusive` follows RFC 7233 semantics."""
    last: Exception | None = None
    for attempt in range(retries):
        try:
            r = sess.get(url, headers={"Range": f"bytes={start}-{end_inclusive}"},
                         timeout=timeout, allow_redirects=True)
            if r.status_code in (200, 206):
                body = r.content
                if r.status_code == 200 and len(body) > (end_inclusive - start + 1):
                    # server ignored the Range header and sent the whole object
                    body = body[start:end_inclusive + 1]
                return body
            if r.status_code in (401, 403, 404):
                raise RangedReadError(f"HTTP {r.status_code} for {url}")
            last = RangedReadError(f"HTTP {r.status_code}")
        except (requests.RequestException, RangedReadError) as exc:
            last = exc
            if isinstance(exc, RangedReadError) and any(c in str(exc) for c in ("401", "403", "404")):
                raise
        time.sleep(1.5 * (attempt + 1))
    raise RangedReadError(f"range read failed for {url}: {last}")


def _get_json(sess: requests.Session, url: str, timeout: float = 60.0) -> dict | None:
    try:
        r = sess.get(url, timeout=timeout, allow_redirects=True)
    except requests.RequestException as exc:
        logger.debug(f"GET {url} failed: {exc}")
        return None
    if r.status_code != 200:
        return None
    try:
        return r.json()
    except ValueError:
        return None


def read_safetensors_header(sess: requests.Session, url: str) -> tuple[dict, int]:
    """Return (header_dict, data_start_offset) for a remote .safetensors file.

    Layout: 8-byte little-endian u64 header length N, then N bytes of JSON, then the data buffer.
    """
    raw = _get_range(sess, url, 0, 7)
    if len(raw) < 8:
        raise RangedReadError(f"could not read 8-byte header length from {url}")
    (n_header,) = struct.unpack("<Q", raw[:8])
    if not (0 < n_header < 200_000_000):
        raise RangedReadError(f"implausible safetensors header length {n_header} at {url}")
    hdr_bytes = _get_range(sess, url, 8, 8 + n_header - 1)
    try:
        header = json.loads(hdr_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RangedReadError(f"bad safetensors header at {url}: {exc}") from exc
    return header, 8 + n_header


def _decode(buf: bytes, dtype_str: str, shape: Sequence[int]) -> np.ndarray:
    if dtype_str not in _DTYPE_MAP:
        raise RangedReadError(f"unsupported dtype {dtype_str}")
    np_dt, _ = _DTYPE_MAP[dtype_str]
    if np_dt == "bf16":
        u16 = np.frombuffer(buf, dtype="<u2")
        u32 = u16.astype(np.uint32) << np.uint32(16)
        arr = u32.view(np.float32)
    else:
        arr = np.frombuffer(buf, dtype=np_dt)
    return arr.reshape(tuple(int(x) for x in shape))


@dataclass
class RepoPlan:
    """Which tensors live in which shard, and the byte spans they occupy."""
    repo_id: str
    revision: str
    targets: dict[str, dict[str, Any]] = field(default_factory=dict)  # name -> {file,dtype,shape,offsets}
    n_files_touched: int = 0
    bytes_planned: int = 0
    skip_reason: str | None = None
    n_experts: int = 0
    n_local_files: int = 0


def plan_repo(repo_id: str, *, token: str | None = None, revision: str = "main",
              want_o_proj: bool = True, want_down_proj: bool = True,
              layer_stride: int = 1, max_experts: int = 4,
              sess: requests.Session | None = None) -> RepoPlan:
    """Build a byte-level read plan for a repo's residual-write matrices. No tensor data is fetched."""
    own = sess is None
    sess = sess or _session(token)
    plan = RepoPlan(repo_id=repo_id, revision=revision)
    snap = local_snapshot(repo_id)
    try:
        cfg = None
        if snap is not None and (snap / "config.json").is_file():
            try:
                cfg = json.loads((snap / "config.json").read_text())
            except (OSError, json.JSONDecodeError):
                cfg = None
        if cfg is None:
            cfg = _get_json(sess, _resolve_url(repo_id, "config.json", revision))
        if cfg is None:
            plan.skip_reason = "no config.json"
            return plan
        if "quantization_config" in cfg:
            plan.skip_reason = "quantised"
            return plan

        index = None
        if snap is not None and (snap / "model.safetensors.index.json").is_file():
            try:
                index = json.loads((snap / "model.safetensors.index.json").read_text())
            except (OSError, json.JSONDecodeError):
                index = None
        if index is None:
            index = _get_json(sess, _resolve_url(repo_id, "model.safetensors.index.json", revision))
        if index and isinstance(index.get("weight_map"), dict):
            weight_map: dict[str, str] = index["weight_map"]
            shard_files = sorted(set(weight_map.values()))
        else:
            weight_map = {}
            shard_files = ["model.safetensors"]

        headers: dict[str, tuple[dict, int]] = {}
        local_files: dict[str, Path] = {}
        for fn in shard_files:
            if _QUANT_MARKERS.search(fn):
                plan.skip_reason = "quantised"
                return plan
            lf = (snap / fn) if snap is not None else None
            if lf is not None and lf.is_file():
                try:
                    headers[fn] = _read_local_header(lf)
                    local_files[fn] = lf
                    continue
                except (OSError, RangedReadError, json.JSONDecodeError) as exc:
                    logger.debug(f"{repo_id}: local shard {fn} unreadable ({exc}); using the Hub")
            try:
                headers[fn] = read_safetensors_header(sess, _resolve_url(repo_id, fn, revision))
            except RangedReadError as exc:
                if not weight_map and fn == "model.safetensors":
                    plan.skip_reason = "no safetensors"
                    return plan
                logger.debug(f"{repo_id}: shard {fn} header unreadable ({exc})")
        plan.n_local_files = len(local_files)

        if not headers:
            plan.skip_reason = "no readable safetensors header"
            return plan

        experts_seen: set[int] = set()
        for fn, (hdr, data_start) in headers.items():
            for name, meta in hdr.items():
                if name == "__metadata__" or not isinstance(meta, dict):
                    continue
                is_o = bool(O_PROJ_RE.search(name))
                is_d = bool(DOWN_RE.search(name))
                if not ((is_o and want_o_proj) or (is_d and want_down_proj)):
                    continue
                lm = LAYER_RE.search(name)
                if lm is None:
                    continue
                layer = int(lm.group(1))
                if layer_stride > 1 and (layer % layer_stride) != 0:
                    continue
                em = EXPERT_RE.search(name)
                if em is not None:
                    e = int(em.group(1))
                    experts_seen.add(e)
                    if e >= max_experts:
                        continue
                shape = meta.get("shape") or []
                if len(shape) != 2:
                    continue
                dt = meta.get("dtype", "")
                if dt not in _DTYPE_MAP:
                    plan.skip_reason = f"unsupported dtype {dt}"
                    return plan
                off = meta.get("data_offsets") or [0, 0]
                plan.targets[name] = {
                    "file": fn, "dtype": dt, "shape": [int(shape[0]), int(shape[1])],
                    "abs_start": data_start + int(off[0]), "abs_end": data_start + int(off[1]) - 1,
                    "nbytes": int(off[1]) - int(off[0]),
                    "layer": layer, "component": "attn" if is_o else "mlp",
                    "local_file": str(local_files[fn]) if fn in local_files else None,
                    "expert": int(em.group(1)) if em else -1,
                }
        plan.n_experts = len(experts_seen)
        plan.n_files_touched = len({t["file"] for t in plan.targets.values()})
        plan.bytes_planned = sum(t["nbytes"] for t in plan.targets.values())
        if not plan.targets:
            plan.skip_reason = "no residual-write matrices matched"
        return plan
    finally:
        if own:
            sess.close()


def fetch_tensor(sess: requests.Session, repo_id: str, tgt: dict[str, Any],
                 revision: str = "main") -> np.ndarray:
    """Fetch ONE tensor's byte span and decode it to float32."""
    lf = tgt.get("local_file")
    if lf:
        with open(lf, "rb") as f:
            f.seek(int(tgt["abs_start"]))
            buf = f.read(int(tgt["nbytes"]))
    else:
        url = _resolve_url(repo_id, tgt["file"], revision)
        buf = _get_range(sess, url, tgt["abs_start"], tgt["abs_end"])
    if len(buf) != tgt["nbytes"]:
        raise RangedReadError(
            f"{repo_id}:{tgt['file']} short read {len(buf)} != {tgt['nbytes']}")
    return _decode(buf, tgt["dtype"], tgt["shape"]).astype(np.float32, copy=False)


# --------------------------------------------------------------------------------------
# (b) THE REALISED-ABLATION-STRENGTH ESTIMATOR
# --------------------------------------------------------------------------------------

TAIL_LO, TAIL_HI = 3, 20      # the "healthy bottom tail" the fit is anchored on
K_BOT_DEFAULT = 24            # MEASURED: the block size that keeps a matrix ~5 s on this box
SCAN_MAX = 16                 # index scan j in [0, 15]; load-bearing for kappa > 1
_EPS = 1e-30


def _design(j: np.ndarray) -> np.ndarray:
    lj = np.log(j.astype(np.float64) + 1.0)
    return np.stack([np.ones_like(lj), lj, lj * lj], axis=1)


def fit_tail(s: np.ndarray, *, lo: int = TAIL_LO, hi: int = TAIL_HI,
             scan_max: int = SCAN_MAX, n_trim: int = 3, floor: float = 0.0) -> dict[str, Any]:
    """Quadratic-in-log fit of the healthy bottom tail, then an index scan for the edited value.

    `s` is the ASCENDING singular-value vector.  Returns the recovered suppression ratio, the index
    it was found at, the fit quality, and everything needed to audit the call.
    """
    d = int(s.shape[0])
    hi = min(hi, d - 1)
    out: dict[str, Any] = {
        "ok": False, "j_star": 0, "ratio_min": float("nan"), "kappa_hat": float("nan"),
        "abs_dev": float("nan"), "ratio_at0": float("nan"), "kappa_at0": float("nan"),
        "fit_r2": float("nan"), "resid_log": float("nan"), "n_tail": 0,
        "k_local": float("nan"), "botgap": float("nan"),
    }
    if d < lo + 8 or hi <= lo + 4:
        return out
    sv = np.asarray(s, dtype=np.float64)
    if sv[1] > 0:
        out["k_local"] = float(1.0 - sv[0] / sv[1])
        out["botgap"] = float(sv[0] / sv[1])
    lim = max(floor, _EPS)
    pos = sv > lim
    idx = np.arange(lo, hi + 1)
    idx = idx[pos[idx]]
    if idx.size < 8:
        return out
    y = np.log(sv[idx])
    X = _design(idx)
    try:
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - X @ beta
        # one robust pass: drop the most extreme residuals (an edited value may sit inside the window)
        if idx.size > n_trim + 6 and n_trim > 0:
            keep = np.argsort(np.abs(resid))[: idx.size - n_trim]
            idx2, y2 = idx[keep], y[keep]
            X2 = _design(idx2)
            beta, *_ = np.linalg.lstsq(X2, y2, rcond=None)
            resid2 = y2 - X2 @ beta
            ss_res = float(np.sum(resid2 ** 2))
            ss_tot = float(np.sum((y2 - y2.mean()) ** 2))
            n_used = int(idx2.size)
        else:
            ss_res = float(np.sum(resid ** 2))
            ss_tot = float(np.sum((y - y.mean()) ** 2))
            n_used = int(idx.size)
    except np.linalg.LinAlgError as exc:
        logger.debug(f"tail fit failed: {exc}")
        return out

    out["fit_r2"] = float(1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan")
    out["n_tail"] = n_used

    jj = np.arange(0, min(scan_max, d))
    pred_log = _design(jj) @ beta
    # an unresolved singular value is NOT a measurement of a strong edit; clamp it AT the floor so a
    # numerically-dead bottom cannot masquerade as kappa = 1
    obs = np.maximum(sv[jj], lim)
    out["n_clamped_in_scan"] = int(np.sum(sv[jj] < lim))
    obs_log = np.log(obs)
    r = obs_log - pred_log                       # negative => suppressed below the healthy tail
    j_star = int(np.argmin(r))                   # the LARGEST DOWNWARD deviation
    ratio_star = float(np.exp(r[j_star]))
    ratio_star = float(min(max(ratio_star, 0.0), 1.0))
    ratio_at0 = float(min(max(float(np.exp(r[0])), 0.0), 1.0))

    out.update({
        "ok": True, "j_star": j_star, "resid_log": float(r[j_star]),
        "ratio_min": ratio_star, "kappa_hat": float(1.0 - ratio_star), "abs_dev": ratio_star,
        "ratio_at0": ratio_at0, "kappa_at0": float(1.0 - ratio_at0),
        "s_pred0": float(np.exp(pred_log[0])), "s0": float(sv[0]),
    })
    return out



# --------------------------------------------------------------------------------------
# FAST BOTTOM/TOP EIGENPAIRS -- shifted randomized subspace iteration
# --------------------------------------------------------------------------------------
# MEASURED ON THIS BOX: a dense eigh of the d x d Gram costs 12 s at d=1024 and 52 s at d=2048,
# which at ~60 matrices per checkpoint is 12-50 minutes of a single contended core PER CHECKPOINT.
# Every statistic this artifact reads needs only the BOTTOM ~48 and TOP ~4 eigenpairs plus the
# trace, so the full decomposition is pure waste.
#
# The bottom eigenvectors of G are the TOP eigenvectors of (lambda_max*I - G), so one shifted
# randomized subspace iteration with a block of k and q passes costs O(q k d^2) instead of O(d^3)
# -- two orders of magnitude less here. Accuracy against exact eigh is asserted in GATE 0.

def _lambda_max(G: np.ndarray, n_iter: int = 24, seed: int = 0) -> float:
    rs = np.random.default_rng(seed)
    v = rs.standard_normal(G.shape[0]).astype(G.dtype)
    v /= np.linalg.norm(v)
    lam = 0.0
    for _ in range(n_iter):
        w = G @ v
        nw = float(np.linalg.norm(w))
        if nw <= 0:
            return 0.0
        v = w / nw
        lam = nw
    return float(lam)


def bottom_top_eig(G: np.ndarray, k_bot: int = 24, k_top: int = 4, n_iter: int = 6,
                   seed: int = 20260920, oversample: int = 8, eps_rel: float = 1e-11
                   ) -> dict[str, Any]:
    """Bottom-k and top-k eigenpairs of a symmetric PSD Gram, without a full eigendecomposition.

    SHIFT-INVERT, not shift-subtract. A first attempt used subspace iteration on
    (lambda_max*I - G); GATE 0 rejected it, because for a FLAT bottom (an honest layer) the
    shifted gap (lambda_max - lambda_0)/(lambda_max - lambda_k) is ~1 and the iteration does not
    converge -- it returned botgap 0.976 where the exact answer was 0.000.

    Iterating with (G + eps I)^-1 instead makes the relevant convergence ratio the RATIO
    lambda_0/lambda_k, which is exactly what an ablation scar makes small. One Cholesky costs
    d^3/3 flops against a dense eigh's ~10 d^3, and every later pass is two triangular solves.
    """
    from scipy.linalg import cho_factor, cho_solve, LinAlgError as SLinAlgError

    d = G.shape[0]
    Gd = np.asarray(G, dtype=np.float64)
    lam_max = _lambda_max(Gd, seed=seed)
    tr = float(np.trace(Gd))
    kb = min(k_bot + oversample, d)
    kt = min(k_top + oversample, d)
    rs = np.random.default_rng(seed)

    eps = max(lam_max * eps_rel, np.finfo(np.float64).tiny)
    cf = None
    for bump in (1.0, 1e3, 1e6, 1e9):
        try:
            cf = cho_factor(Gd + (eps * bump) * np.eye(d), lower=True, check_finite=False)
            break
        except (SLinAlgError, np.linalg.LinAlgError):
            continue
    if cf is None:
        evals, evecs = np.linalg.eigh(Gd)
        return {"evals_bot": evals[:k_bot], "evecs_bot": evecs[:, :k_bot],
                "evals_top": evals[::-1][:k_top], "evecs_top": evecs[:, ::-1][:, :k_top],
                "lam_max": float(evals[-1]), "trace": tr, "d": int(d), "solver": "dense_eigh_fallback"}

    Q, _ = np.linalg.qr(rs.standard_normal((d, kb)))
    for _ in range(n_iter):
        Q, _ = np.linalg.qr(cho_solve(cf, Q, check_finite=False))
    Bb = Q.T @ (Gd @ Q)
    eb, Vb = np.linalg.eigh(0.5 * (Bb + Bb.T))
    evals_bot, evecs_bot = eb[:k_bot], Q @ Vb[:, :k_bot]

    Qt, _ = np.linalg.qr(rs.standard_normal((d, kt)))
    for _ in range(n_iter):
        Qt, _ = np.linalg.qr(Gd @ Qt)
    Bt = Qt.T @ (Gd @ Qt)
    et, Vt = np.linalg.eigh(0.5 * (Bt + Bt.T))
    return {"evals_bot": evals_bot, "evecs_bot": evecs_bot,
            "evals_top": et[::-1][:k_top], "evecs_top": (Qt @ Vt[:, ::-1])[:, :k_top],
            "lam_max": float(lam_max), "trace": tr, "d": int(d), "solver": "cholesky_shift_invert"}


def spectrum_stats(W: np.ndarray, *, n_bottom: int = 8, n_top: int = 4,
                   n_spec_points: int = 128, exact: bool = False, n_iter: int = 6
                   ) -> dict[str, Any]:
    """Left-singular spectrum of a residual-write matrix, plus the strength estimate.

    G = W W^T is d_out x d_out; eigh on it gives the LEFT singular subspace at a fraction of a full SVD.
    """
    Wf = np.asarray(W, dtype=np.float64)
    if Wf.ndim != 2:
        raise ValueError(f"expected a 2-D matrix, got shape {Wf.shape}")
    d_out, d_in = Wf.shape
    # The Gram is formed in float64. In float32 its bottom eigenvalues sit below machine precision
    # relative to lambda_max (they scale as sigma^2), which silently returns zeros/negatives and
    # makes every bottom-spectrum statistic garbage -- measured in GATE 1.
    # STRUCTURAL RANK DEFICIENCY, MEASURED ON REAL REPOS AND EASY TO MISTAKE FOR AN EDIT.
    # Some families ship an o_proj with d_in < d_out (num_heads * head_dim below hidden_size --
    # Gemma3-1B is one). Then W W^T has exactly (d_out - d_in) zero eigenvalues BY CONSTRUCTION,
    # its bottom gap is 0 for an untouched checkpoint, and a rank read false-positives on the
    # architecture rather than on the edit. The fix is to decompose on the SMALLER side: the
    # non-zero spectrum of W^T W is identical, and the left singular vectors come back as
    # u = W v / sigma. The first pass of STAGE 1 reported kappa_hat = nan on exactly such a repo.
    transposed = d_in < d_out
    Wg = Wf.T if transposed else Wf
    G = Wg @ Wg.T
    G = 0.5 * (G + G.T)
    dg = G.shape[0]
    if exact:
        evals, evecs = np.linalg.eigh(G)        # ASCENDING
        eb, Ub = evals[:K_BOT_DEFAULT], evecs[:, :K_BOT_DEFAULT]
        et, Ut = evals[::-1][:4], evecs[:, ::-1][:, :4]
        lam_max, tr = float(evals[-1]), float(np.sum(evals))
    else:
        fe = bottom_top_eig(G, k_bot=min(K_BOT_DEFAULT, dg), k_top=min(4, dg), n_iter=n_iter)
        eb, Ub, et, Ut = fe["evals_bot"], fe["evecs_bot"], fe["evals_top"], fe["evecs_top"]
        lam_max, tr = fe["lam_max"], fe["trace"]
    if transposed:
        # map the RIGHT singular vectors of W^T back to the LEFT singular vectors of W
        def _back(V: np.ndarray, lam: np.ndarray) -> np.ndarray:
            U = Wf @ V
            nrm = np.linalg.norm(U, axis=0, keepdims=True)
            nrm[nrm == 0] = 1.0
            return U / nrm
        Ub, Ut = _back(Ub, eb), _back(Ut, et)
    num_floor = max(lam_max * 1e-13 * max(d_out, 1), 0.0)
    n_unresolved = int(np.sum(eb < num_floor))
    s = np.sqrt(np.clip(eb, 0.0, None))          # ascending BOTTOM singular values
    s_top = np.sqrt(np.clip(et, 0.0, None))      # descending TOP singular values
    mean_sq = tr / max(d_out, 1)                 # exact mean of sigma^2, from the trace
    evecs = Ub

    nb = min(n_bottom, s.size)
    nt = min(n_top, s_top.size)
    tail = fit_tail(s, floor=float(np.sqrt(num_floor)))
    s_rms = float(np.sqrt(max(mean_sq, 0.0)))    # RMS singular value: the scale-free reference
    return {
        "d_out": int(d_out), "d_in": int(d_in),
        "structurally_rank_deficient": bool(transposed),
        "effective_rank_ub": int(min(d_out, d_in)),
        "s_bottom": [float(x) for x in s[:nb]],
        "s_top": [float(x) for x in s_top[:nt]],
        "u_bottom": Ub[:, :nb].astype(np.float32),
        "u_top": Ut[:, :nt].astype(np.float32),
        "spectrum_idx": [int(i) for i in range(min(24, s.size))],
        "spectrum_val": [float(x) for x in s[:min(24, s.size)]],
        "s_rms": s_rms, "s_max": float(s_top[0]) if s_top.size else float("nan"),
        "s_median": s_rms,
        "n_unresolved": n_unresolved,
        "cond_bottom": float(s[0] / s_top[0]) if s_top.size and s_top[0] > 0 else float("nan"),
        "sigma_min_over_median": float(s[0] / s_rms) if s_rms > 0 else float("nan"),
        "frob": float(np.sqrt(max(tr, 0.0))), "trace": float(tr), "mean_sq": float(mean_sq),
        **{k: v for k, v in tail.items() if k != "ok"},
        "tail_ok": bool(tail["ok"]),
    }


# --------------------------------------------------------------------------------------
# (c) THE CROSS-LAYER COSINE (XLC)
# --------------------------------------------------------------------------------------

def cross_layer_cosine(vectors: dict[int, np.ndarray], *, layers: Sequence[int] | None = None,
                       max_pairs: int = 4096) -> dict[str, Any]:
    """Mean |cos| between the suppressed directions of different layers.

    For random unit directions in d dimensions E|cos| ~ sqrt(2/(pi d)); we report that asymptotic null
    ALONGSIDE the measured honest-panel distribution, never instead of it.
    """
    ls = sorted(vectors) if layers is None else sorted(l for l in layers if l in vectors)
    if len(ls) < 2:
        return {"xlc": float("nan"), "n_pairs": 0, "n_layers": len(ls),
                "iso_null": float("nan"), "xlc_max": float("nan"), "xlc_p90": float("nan")}
    V = np.stack([vectors[l].astype(np.float64).ravel() for l in ls], axis=0)
    nrm = np.linalg.norm(V, axis=1, keepdims=True)
    nrm[nrm == 0] = 1.0
    V = V / nrm
    C = np.abs(V @ V.T)
    iu = np.triu_indices(len(ls), k=1)
    vals = C[iu]
    if vals.size > max_pairs:
        rs = np.random.default_rng(0)
        vals = rs.choice(vals, size=max_pairs, replace=False)
    d = V.shape[1]
    return {
        "xlc": float(np.mean(vals)), "xlc_max": float(np.max(vals)),
        "xlc_p90": float(np.percentile(vals, 90)), "n_pairs": int(vals.size),
        "n_layers": len(ls), "iso_null": float(math.sqrt(2.0 / (math.pi * d))),
    }


def cross_family_cosine(a: dict[int, np.ndarray], b: dict[int, np.ndarray]) -> dict[str, Any]:
    """|cos| between the two matrix families' suppressed directions AT THE SAME LAYER.

    Both o_proj and down_proj write into the same residual basis, so a genuinely shared-direction
    recipe must agree across families too. No published tool reports this consistency check.
    """
    shared = sorted(set(a) & set(b))
    if not shared:
        return {"xfc": float("nan"), "n_layers": 0}
    cs = []
    for l in shared:
        u, v = a[l].astype(np.float64).ravel(), b[l].astype(np.float64).ravel()
        nu, nv = np.linalg.norm(u), np.linalg.norm(v)
        if nu == 0 or nv == 0:
            continue
        cs.append(abs(float(u @ v) / (nu * nv)))
    if not cs:
        return {"xfc": float("nan"), "n_layers": 0}
    return {"xfc": float(np.mean(cs)), "xfc_max": float(np.max(cs)), "n_layers": len(cs),
            "per_layer": [float(c) for c in cs]}


# --------------------------------------------------------------------------------------
# (d) THE PER-LAYER STRENGTH PROFILE
# --------------------------------------------------------------------------------------

def fit_depth_profile(layers: Sequence[int], strength: Sequence[float], n_layers: int) -> dict[str, Any]:
    """Recover a tool's own layer-position hyperparameters from the recovered per-layer strength.

    The dominant automated tool varies ablation weight with layer POSITION by construction, so the
    profile kappa_hat(L) has a shape: peak value ~ max_weight, peak location ~ max_weight_position.
    """
    ls = np.asarray(layers, dtype=np.float64)
    ks = np.asarray(strength, dtype=np.float64)
    m = np.isfinite(ks) & np.isfinite(ls)
    ls, ks = ls[m], ks[m]
    out: dict[str, Any] = {"n_points": int(ls.size), "peak_value": float("nan"),
                           "peak_layer": float("nan"), "peak_frac": float("nan"),
                           "fwhm_frac": float("nan"), "gauss_amp": float("nan"),
                           "gauss_mu_frac": float("nan"), "gauss_sigma_frac": float("nan"),
                           "gauss_r2": float("nan"), "monotone_rho": float("nan")}
    if ls.size < 4 or n_layers <= 1:
        return out
    pk = int(np.argmax(ks))
    peak_v = float(ks[pk])
    out["peak_value"] = peak_v
    out["peak_layer"] = float(ls[pk])
    out["peak_frac"] = float(ls[pk] / max(n_layers - 1, 1))
    half = peak_v / 2.0
    above = ls[ks >= half]
    if above.size >= 1:
        out["fwhm_frac"] = float((above.max() - above.min() + 1.0) / n_layers)
    x = ls / max(n_layers - 1, 1)
    # rank correlation of strength with depth: is the recipe depth-graded at all?
    if ks.size >= 4 and np.ptp(ks) > 0:
        rx = np.argsort(np.argsort(x)).astype(float)
        ry = np.argsort(np.argsort(ks)).astype(float)
        sx, sy = rx.std(), ry.std()
        if sx > 0 and sy > 0:
            out["monotone_rho"] = float(np.mean((rx - rx.mean()) * (ry - ry.mean())) / (sx * sy))
    # least-squares Gaussian on the profile (grid over mu/sigma, closed form for the amplitude)
    best = None
    for mu in np.linspace(0.0, 1.0, 41):
        for sg in np.linspace(0.04, 0.8, 39):
            b = np.exp(-((x - mu) ** 2) / (2.0 * sg * sg))
            den = float(b @ b)
            if den <= 0:
                continue
            amp = float(b @ ks) / den
            res = ks - amp * b
            ss = float(res @ res)
            if best is None or ss < best[0]:
                best = (ss, amp, mu, sg)
    if best is not None:
        ss_tot = float(np.sum((ks - ks.mean()) ** 2))
        out["gauss_amp"] = float(best[1])
        out["gauss_mu_frac"] = float(best[2])
        out["gauss_sigma_frac"] = float(best[3])
        out["gauss_r2"] = float(1.0 - best[0] / ss_tot) if ss_tot > 0 else float("nan")
    return out


# --------------------------------------------------------------------------------------
# BAND DETECTION + CHECKPOINT-LEVEL ASSEMBLY
# --------------------------------------------------------------------------------------

def touched_band(per_layer_strength: dict[int, float], honest_ref: dict[str, float] | None,
                 z_thresh: float = 3.0) -> dict[str, Any]:
    """Contiguous layers whose strength z-score against the HONEST panel exceeds `z_thresh`.

    With no honest reference yet (first pass), fall back to a within-checkpoint robust z so the field
    is always populated; the honest-referenced version is recomputed in the analysis stage.
    """
    if not per_layer_strength:
        return {"band_lo": None, "band_hi": None, "band_frac": float("nan"), "n_flagged": 0,
                "mode": "empty"}
    ls = sorted(per_layer_strength)
    ks = np.array([per_layer_strength[l] for l in ls], dtype=np.float64)
    if honest_ref and np.isfinite(honest_ref.get("sd", float("nan"))) and honest_ref["sd"] > 0:
        z = (ks - honest_ref["mean"]) / honest_ref["sd"]
        mode = "honest_panel_z"
    else:
        med = float(np.median(ks))
        mad = float(np.median(np.abs(ks - med))) * 1.4826
        z = (ks - med) / mad if mad > 1e-12 else np.zeros_like(ks)
        mode = "within_ckpt_robust_z"
    flag = z > z_thresh
    best = (0, None, None)
    run_start = None
    for i, f in enumerate(flag):
        if f and run_start is None:
            run_start = i
        if (not f or i == len(flag) - 1) and run_start is not None:
            end = i if f else i - 1
            length = end - run_start + 1
            if length > best[0]:
                best = (length, ls[run_start], ls[end])
            run_start = None
    n_layers = max(ls) + 1
    return {"band_lo": best[1], "band_hi": best[2],
            "band_frac": float(best[0] / n_layers) if best[0] else 0.0,
            "n_flagged": int(flag.sum()), "mode": mode,
            "z_max": float(np.max(z)) if z.size else float("nan")}


def bsa_window(u_by_layer: dict[int, np.ndarray], window: int = 8) -> dict[str, Any]:
    """BSA: max over contiguous `window`-layer spans of lambda_max(mean of bottom-1 projectors).

    *** ADOPTED PRIOR ART *** — the Jorak Model Scanner's subspace_signature() already computes this
    on exactly o_proj/down_proj. It is a DETECTION statistic, never a safety score. What this artifact
    adds is honest-panel calibration on real trained weights.
    """
    ls = sorted(u_by_layer)
    if not ls:
        return {"bsa_w": float("nan"), "bsa_all": float("nan"), "win_lo": None, "win_hi": None}

    def lam(sub: Sequence[int]) -> float:
        V = np.stack([u_by_layer[l].astype(np.float64).ravel() for l in sub], axis=1)
        n = np.linalg.norm(V, axis=0, keepdims=True)
        n[n == 0] = 1.0
        V = V / n
        # lambda_max of mean_i u_i u_i^T == (1/k) * largest squared singular value of V
        sv = np.linalg.svd(V, compute_uv=False)
        return float(sv[0] ** 2 / len(sub))

    best, lo, hi = float("nan"), None, None
    for i in range(len(ls)):
        sub = ls[i:i + window]
        if len(sub) < min(window, len(ls)):
            break
        v = lam(sub)
        if not np.isfinite(best) or v > best:
            best, lo, hi = v, sub[0], sub[-1]
    return {"bsa_w": best, "bsa_all": lam(ls), "win_lo": lo, "win_hi": hi}


# --------------------------------------------------------------------------------------
# (e) THE RAYLEIGH-DEPRESSION READOUT  -- graded across the WHOLE kappa range
# --------------------------------------------------------------------------------------
# WHY THIS EXISTS.  GATE 1 measured that the bottom-spectrum estimator of (b) is only sensitive in a
# narrow band around kappa = 1.  Abliteration is W' = (I - kappa r r^T) W, so G' = P G P with
# P = I - kappa r r^T, and r^T G' r = (1-kappa)^2 r^T G r.  The BOTTOM of the spectrum only moves
# once (1-kappa)^2 r^T G r falls below the layer's own sigma_min^2 -- i.e. only for kappa near 1.
# Away from kappa = 1 the edit is invisible to a rank-deficiency read, no matter how large it is.
#
# The Rayleigh readout keeps the same parent-free budget (weights only, zero prompts) but asks a
# GRADED question instead of a rank question: pick the direction that is jointly most depressed
# ACROSS LAYERS, then report how depressed it is relative to that layer's own spectrum.


def pooled_bottom_direction(grams: dict[int, np.ndarray], *, k: int = 1) -> np.ndarray | None:
    """Bottom eigenvector of the TRACE-NORMALISED sum of per-layer Gram matrices.

    Trace normalisation is what makes the layers commensurable without a parent: each layer
    contributes its own shape, not its own scale.
    """
    acc = None
    for _, G in sorted(grams.items()):
        tr = float(np.trace(G))
        if tr <= 0:
            continue
        acc = (G / tr) if acc is None else acc + (G / tr)
    if acc is None:
        return None
    evals, evecs = np.linalg.eigh(0.5 * (acc + acc.T))
    return evecs[:, :k]


def rayleigh_depression(G: np.ndarray, r: np.ndarray, spectrum: np.ndarray) -> dict[str, Any]:
    """How far below its own spectrum does direction `r` sit in this layer?

    ratio = (r^T G r) / median(sigma^2).  An unedited layer scores ~1 for a typical direction;
    an ablated one scores (1-kappa)^2 times whatever it scored before, at ANY kappa.
    """
    rv = np.asarray(r, dtype=np.float64).ravel()
    n = np.linalg.norm(rv)
    if n == 0:
        return {"rq": float("nan"), "rq_log10": float("nan"), "pct": float("nan")}
    rv = rv / n
    q = float(rv @ (G @ rv))
    s2 = np.asarray(spectrum, dtype=np.float64) ** 2
    # reference scale = the EXACT mean of sigma^2 = trace(G)/d, not a median over a partial spectrum
    med = float(np.trace(G) / G.shape[0]) if G.shape[0] else float("nan")
    lo = float(s2.min()) if s2.size else float("nan")
    ratio = q / med if med > 0 else float("nan")
    return {"rq": ratio,
            "rq_log10": float(np.log10(max(ratio, 1e-300))),
            "pct": float(np.mean(s2 <= q)),
            "rq_over_min": float(q / lo) if lo > 0 else float("nan")}


def operating_range(sigma_min_over_median: float) -> float:
    """The |1 - kappa| BELOW which a bottom-spectrum read can see the edit at all.

    Derived, not asserted: the edited direction only reaches the bottom of the spectrum once
    (1-kappa)^2 * (r^T G r) < sigma_min^2, and r^T G r ~ median(sigma^2) for a generic direction.
    """
    return float(max(min(sigma_min_over_median, 1.0), 0.0))

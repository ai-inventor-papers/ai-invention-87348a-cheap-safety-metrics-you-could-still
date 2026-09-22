"""S2 weight pass and S3-C4 weight reads: zero prompts, no parent, no reference model.

Every statistic here is computed from the left singular subspaces of the matrices
that WRITE to the residual stream (``self_attn.o_proj`` and ``mlp.down_proj``).
Left subspaces are obtained from ``eigh(W @ W.T)`` in float32 rather than a full
SVD: there are ~72 decompositions per checkpoint and the Gram route is ~50x faster.

PRIOR ART, LABELLED: the unwindowed sum-of-bottom-projectors score (:func:`jorak_score`)
is the Jorak model-scanner subspace signature (JolanMc/Jorak,
``modelscanner/metrics/jorak.py::subspace_signature``). It is ADOPTED here, not
invented; what this module adds is the windowed form, the rank-band sweep, and the
calibration machinery in :mod:`flab.panel`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np
import torch

from flab.config import BSA_K, BSA_K_ALT, BSA_WINDOW, RANK_BANDS


@dataclass
class LayerSpectrum:
    """Per-layer left-subspace summary. All vectors are d_model-dimensional."""

    layer: int
    module: str
    bottom_k1: np.ndarray                 # (d_model, 1)
    bottom_k4: np.ndarray                 # (d_model, 4)
    top_k1: np.ndarray                    # (d_model, 1)
    rank_band: dict[int, np.ndarray] = field(default_factory=dict)  # r -> (d_model, K)
    s_min: float = 0.0
    s_2: float = 0.0
    s_max: float = 0.0
    s_median: float = 0.0
    s_sum: float = 0.0
    participation_ratio: float = 0.0

    @property
    def botgap(self) -> float:
        """Local rank deficiency s_min / s_2. LOW = a direction has been removed."""
        return float(self.s_min / self.s_2) if self.s_2 > 0 else float("nan")


def layer_spectrum(
    W: torch.Tensor,
    layer: int,
    module: str,
    *,
    device: str = "cuda",
    rank_bands: Iterable[int] = RANK_BANDS,
) -> LayerSpectrum:
    """Left singular subspaces of one residual-write matrix.

    Args:
        W: weight tensor, shape (d_model, d_in) -- torch stores nn.Linear as (out, in)
           and both o_proj and down_proj write d_model outputs.
        layer: layer index, recorded on the result.
        module: 'o_proj' or 'down_proj'.
        device: where to run the decomposition.
        rank_bands: spectral offsets from the TOP of the spectrum for the injection arm.

    Returns:
        A :class:`LayerSpectrum`; all arrays are on CPU as float32 numpy.
    """
    Wf = W.detach().to(device=device, dtype=torch.float32)
    G = Wf @ Wf.T                                   # (d_model, d_model)
    evals, evecs = torch.linalg.eigh(G)             # ASCENDING
    evals = torch.clamp(evals, min=0.0)
    svals = torch.sqrt(evals)

    d = evecs.shape[0]
    bands: dict[int, np.ndarray] = {}
    for r in rank_bands:
        hi = d - r
        lo = hi - BSA_K
        if lo < 0:
            continue
        bands[int(r)] = evecs[:, lo:hi].contiguous().cpu().numpy().astype(np.float32)

    ev = evals.cpu().numpy()
    sv = svals.cpu().numpy()
    s_sum = float(ev.sum())
    pr = float((ev.sum() ** 2) / (np.square(ev).sum())) if s_sum > 0 else float("nan")

    out = LayerSpectrum(
        layer=layer,
        module=module,
        bottom_k1=evecs[:, :BSA_K].contiguous().cpu().numpy().astype(np.float32),
        bottom_k4=evecs[:, :BSA_K_ALT].contiguous().cpu().numpy().astype(np.float32),
        top_k1=evecs[:, -BSA_K:].contiguous().cpu().numpy().astype(np.float32),
        rank_band=bands,
        s_min=float(sv[0]),
        s_2=float(sv[1]) if sv.shape[0] > 1 else float("nan"),
        s_max=float(sv[-1]),
        s_median=float(np.median(sv)),
        s_sum=s_sum,
        participation_ratio=pr,
    )
    del Wf, G, evals, evecs, svals
    if device.startswith("cuda"):
        torch.cuda.empty_cache()
    return out


# --------------------------------------------------------------------------
# The subspace-sharing statistics
# --------------------------------------------------------------------------
def _stack_blocks(vecs: list[np.ndarray]) -> np.ndarray:
    """Concatenate per-layer (d, K) orthonormal blocks into one (d, sum K) matrix."""
    return np.concatenate([B.astype(np.float64) for B in vecs], axis=1)


def _top_eigs_of_gram(vecs: list[np.ndarray], k: int = 1) -> np.ndarray:
    """Top-k eigenvalues of ``M = sum_l B_l B_l^T`` without ever forming M.

    M = B B^T for the stacked B (d x m), and B B^T and B^T B share their non-zero
    spectrum, so the eigenvalues come from the m x m Gram with m = sum_l K -- a
    36x36 problem instead of a 2560x2560 one. That is the difference between
    milliseconds and minutes per checkpoint, and it is exact, not an approximation.
    """
    B = _stack_blocks(vecs)
    G = B.T @ B
    ev = np.linalg.eigvalsh(G)
    return ev[-k:]


def _mean_projector_lmax(vecs: list[np.ndarray]) -> float:
    """lambda_max of mean_l B_l B_l^T for a list of (d_model, K) orthonormal blocks."""
    if not vecs:
        return float("nan")
    return float(_top_eigs_of_gram(vecs, 1)[-1] / len(vecs))


def windowed_subspace_alignment(vecs: list[np.ndarray], window: int = BSA_WINDOW) -> float:
    """BSA_w: max over CONTIGUOUS windows of ``window`` layers of the mean-projector lambda_max.

    Windowing is what separates a LAYER-BAND edit from an all-layer one: an edit
    confined to 50% of the stack is invisible to the unwindowed sum but saturates
    a window that sits inside the band.
    """
    n = len(vecs)
    if n == 0:
        return float("nan")
    w = min(window, n)
    return max(_mean_projector_lmax(vecs[i : i + w]) for i in range(n - w + 1))


def jorak_score(vecs: list[np.ndarray], k: int = BSA_K) -> float:
    """ADOPTED PRIOR ART -- Jorak model-scanner ``subspace_signature``.

    M = sum_l B_l B_l^T over ALL layers; score = (sum of top-k eigenvalues of M)
    / (n_layers * k). At k=1 this is exactly lambda_max of the mean projector,
    i.e. the unwindowed special case of :func:`windowed_subspace_alignment`.
    """
    n = len(vecs)
    if n == 0:
        return float("nan")
    return float(_top_eigs_of_gram(vecs, k).sum() / (n * k))


def cross_layer_cosine(vecs: list[np.ndarray]) -> float:
    """C4e: mean pairwise |cos| between per-layer bottom-1 left singular vectors."""
    if len(vecs) < 2:
        return float("nan")
    V = np.concatenate([v[:, :1] for v in vecs], axis=1)          # (d, n)
    V = V / (np.linalg.norm(V, axis=0, keepdims=True) + 1e-12)
    C = np.abs(V.T @ V)
    n = C.shape[0]
    iu = np.triu_indices(n, k=1)
    return float(C[iu].mean())


def rank_band_alignment(
    specs: list[LayerSpectrum], window: int = BSA_WINDOW
) -> dict[int, float]:
    """C4c: TSA swept over spectral rank bands -- the injection arm the scanner lacks.

    A rank-one ADDITION does not create a null direction, so the bottom-subspace
    read is blind to it; it instead plants a shared direction somewhere in the
    upper spectrum, which is what this sweep finds.
    """
    out: dict[int, float] = {}
    if not specs:
        return out
    for r in sorted(specs[0].rank_band):
        vecs = [s.rank_band[r] for s in specs if r in s.rank_band]
        if len(vecs) == len(specs):
            out[r] = windowed_subspace_alignment(vecs, window)
    return out


def weight_reads(
    specs_by_module: dict[str, list[LayerSpectrum]],
    *,
    window: int = BSA_WINDOW,
    windows_sens: Iterable[int] = (4, 8, 16),
) -> dict[str, object]:
    """All of C4 for one checkpoint, computed per module and pooled.

    Returns a flat dict of named scalars plus the per-band curve. Pooling
    concatenates o_proj and down_proj layer-wise, which is the setting the
    honest-panel thresholds are fitted on.
    """
    res: dict[str, object] = {}
    pooled: list[np.ndarray] = []
    pooled_specs: list[LayerSpectrum] = []
    for mod, specs in specs_by_module.items():
        if not specs:
            continue
        specs = sorted(specs, key=lambda s: s.layer)
        bots = [s.bottom_k1 for s in specs]
        pooled.extend(bots)
        pooled_specs.extend(specs)
        res[f"bsa_w{window}_{mod}"] = windowed_subspace_alignment(bots, window)
        res[f"jorak_{mod}"] = jorak_score(bots)
        res[f"botgap_{mod}"] = float(np.median([s.botgap for s in specs]))
        res[f"xlayer_cos_{mod}"] = cross_layer_cosine(bots)
        bands = rank_band_alignment(specs, window)
        res[f"tsa_bands_{mod}"] = bands
        res[f"tsa_max_{mod}"] = float(max(bands.values())) if bands else float("nan")
        res[f"tsa_argmax_{mod}"] = (
            int(max(bands, key=lambda r: bands[r])) if bands else -1
        )
        for w in windows_sens:
            res[f"bsa_w{w}_{mod}"] = windowed_subspace_alignment(bots, w)
        res[f"bsa_wall_{mod}"] = windowed_subspace_alignment(bots, len(bots))

    if pooled:
        res[f"bsa_w{window}_pooled"] = windowed_subspace_alignment(pooled, window)
        res["jorak_pooled"] = jorak_score(pooled)
        res["botgap_pooled"] = float(np.median([s.botgap for s in pooled_specs]))
        res["xlayer_cos_pooled"] = cross_layer_cosine(pooled)
        # C4e recovered recipe: realised strength proxy and the edited layer band.
        strengths = [
            1.0 - (s.s_min / s.s_median) if s.s_median > 0 else float("nan")
            for s in pooled_specs
        ]
        res["realised_strength_max"] = float(np.nanmax(strengths))
        res["realised_strength_median"] = float(np.nanmedian(strengths))
    return res


def haar_matched_null(
    svals: np.ndarray, d_model: int, d_in: int, rng: np.random.Generator, device: str = "cuda"
) -> torch.Tensor:
    """S4 anisotropy-matched null: rebuild W = U diag(s) V^T with Haar U, V and the REAL s.

    This separates 'this checkpoint has a shared direction' from 'this checkpoint
    has a heavy-tailed spectrum'.
    """
    k = min(d_model, d_in)
    U = np.linalg.qr(rng.standard_normal((d_model, k)))[0]
    V = np.linalg.qr(rng.standard_normal((d_in, k)))[0]
    W = (U * svals[:k][None, :]) @ V.T
    return torch.from_numpy(W.astype(np.float32)).to(device)

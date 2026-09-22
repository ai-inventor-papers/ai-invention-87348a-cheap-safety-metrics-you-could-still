"""Plan 2 — santé d'axe : l'axe de refus est-il vivant ? [J5]

Cohen's d par couche (métrique primaire) :
    d_ℓ = (mean(proj_harmful) − mean(proj_harmless)) / σ_pooled
où proj = <hidden, r̂_ℓ>. d élevé = clusters bien séparés = axe intact.
Silhouette (sur la projection 1D) en métrique secondaire (comparabilité
Heretic/Reaper).
"""
from __future__ import annotations

import numpy as np


def _projections(activations, directions):
    """Projette les hidden states sur r̂_ℓ. -> (proj_harmful, proj_harmless),
    chacun [n_layers, n_prompts]."""
    # einsum couche par couche : [L,N,H] . [L,H] -> [L,N]
    proj_h = np.einsum("lnh,lh->ln", activations.harmful, directions)
    proj_hl = np.einsum("lnh,lh->ln", activations.harmless, directions)
    return proj_h, proj_hl


def cohens_d(activations, directions) -> np.ndarray:
    """Cohen's d par couche -> [n_layers]."""
    proj_h, proj_hl = _projections(activations, directions)
    n_h, n_hl = proj_h.shape[1], proj_hl.shape[1]

    mean_h = proj_h.mean(axis=1)
    mean_hl = proj_hl.mean(axis=1)
    var_h = proj_h.var(axis=1, ddof=1)
    var_hl = proj_hl.var(axis=1, ddof=1)

    pooled = np.sqrt(((n_h - 1) * var_h + (n_hl - 1) * var_hl) / (n_h + n_hl - 2))
    pooled = np.where(pooled == 0.0, np.nan, pooled)
    return ((mean_h - mean_hl) / pooled).astype(np.float32)


def silhouette_scores(activations, directions) -> np.ndarray:
    """Silhouette par couche (sur la projection 1D sur r̂_ℓ) -> [n_layers].

    Métrique secondaire. Renvoie NaN pour une couche dégénérée."""
    from sklearn.metrics import silhouette_score

    proj_h, proj_hl = _projections(activations, directions)
    n_layers = proj_h.shape[0]
    labels = np.array([0] * proj_h.shape[1] + [1] * proj_hl.shape[1])

    out = np.full(n_layers, np.nan, dtype=np.float32)
    for l in range(n_layers):
        x = np.concatenate([proj_h[l], proj_hl[l]]).reshape(-1, 1)
        if np.ptp(x) == 0:  # tout identique -> silhouette indéfinie
            continue
        out[l] = silhouette_score(x, labels)
    return out

"""Direction de refus par mean-diff (v1). [J4]

r̂_ℓ = normalize(μ_harmful_ℓ − μ_harmless_ℓ)   sur les hidden states au dernier
token (brief §3.5). Une direction unitaire par couche.
"""
from __future__ import annotations

import numpy as np


def mean_diff_directions(activations) -> np.ndarray:
    """Renvoie r̂ unitaire par couche -> [n_layers, hidden] (float32).

    Les couches au signal nul (μ_harmful == μ_harmless) renvoient un vecteur nul
    plutôt que NaN (garde-fou ; ces couches auront un Cohen's d ~0 en J5)."""
    diff = activations.mean_harmful() - activations.mean_harmless()  # [n_layers, hidden]
    norms = np.linalg.norm(diff, axis=1, keepdims=True)              # [n_layers, 1]
    safe = np.where(norms == 0.0, 1.0, norms)
    return (diff / safe).astype(np.float32)

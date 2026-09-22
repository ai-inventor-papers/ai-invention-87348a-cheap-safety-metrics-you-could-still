"""Oracle de validation par diff de poids (DEV ONLY, hors prod). [J7]

Sur une paire appariée base <-> abliteré, calcule la vraie projection retirée
ΔW_ℓ = W_base,ℓ − W_ablated,ℓ et sa structure :
  - direction principale retirée par couche (vecteur singulier gauche dominant
    de ΔW_ℓ) -> la "vraie" r̂ que l'ablation a enlevée ;
  - rang-1-ité de ΔW_ℓ (σ₁/‖ΔW‖_F ≈ 1 => ablation rank-1 propre) ;
  - alignement inter-couches des directions retirées (≈ 1 => direction partagée).

Sert à VÉRIFIER que la détection reference-free (suppression, u_min) tombe juste
et à CALIBRER les seuils. JAMAIS utilisé en production.
"""
from __future__ import annotations

from typing import Dict

import numpy as np

from modelscanner.core.types import WeightTarget


def weight_diff_oracle(
    base_handle,
    ablated_handle,
    target: WeightTarget = WeightTarget.O_PROJ,
) -> Dict[str, object]:
    """Compare poids base vs abliteré -> structure de l'ablation (ground truth)."""
    if base_handle.n_layers != ablated_handle.n_layers:
        raise ValueError("Paire non appariée : nombres de couches différents.")
    n = base_handle.n_layers

    removed = []                 # direction principale retirée par couche [n, d_model]
    rank1_frac = np.zeros(n, dtype=np.float32)
    rel_change = np.zeros(n, dtype=np.float32)  # ‖ΔW‖_F / ‖W_base‖_F par couche

    for l in range(n):
        Wb = np.asarray(base_handle.weight(target, l), dtype=np.float32)
        Wa = np.asarray(ablated_handle.weight(target, l), dtype=np.float32)
        dW = Wb - Wa
        nf = np.linalg.norm(dW)
        rel_change[l] = nf / (np.linalg.norm(Wb) + 1e-12)
        if nf < 1e-12:           # couche non touchée
            removed.append(np.zeros(Wb.shape[0], dtype=np.float32))
            continue
        U, S, _ = np.linalg.svd(dW, full_matrices=False)
        removed.append(U[:, 0])                       # direction retirée
        rank1_frac[l] = float(S[0] / nf)              # à quel point ΔW est rank-1

    R = np.stack(removed, axis=0).astype(np.float32)  # [n, d_model]
    nz = np.linalg.norm(R, axis=1) > 0
    if nz.sum() >= 2:
        sv = np.linalg.svd(R[nz], compute_uv=False)
        shared_alignment = float(sv[0] / np.linalg.norm(R[nz]))
    else:
        shared_alignment = float("nan")

    # couches "touchées" = changement relatif non négligeable
    layers_touched = np.flatnonzero(rel_change > 1e-4)

    return {
        "removed_directions": R,         # [n, d_model] (la vraie r̂ par couche)
        "rank1_fraction": rank1_frac,    # ~1 => ablation rank-1 propre
        "relative_change": rel_change,   # ‖ΔW‖/‖W‖ par couche
        "layers_touched": layers_touched,
        "shared_alignment": shared_alignment,  # ~1 => direction partagée inter-couches
    }

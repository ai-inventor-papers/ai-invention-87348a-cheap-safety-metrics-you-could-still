"""Plan POIDS — signature spectrale des poids (SVD), le smoking-gun reference-free, CPU-OK. [J6]

⚠ NOMMAGE : « Jorak » désigne le **projet / le détecteur** dans son ensemble (3 plans :
POIDS-SVD, ACTIVATIONS, BEHAVIORAL), PAS cette technique seule. Ce module implémente
le **plan POIDS** — la technique *phare* de Jorak : fondée sur la seule géométrie des
poids (par opposition au plan ACTIVATIONS, qui nécessite un forward, et au plan
BEHAVIORAL, qui nécessite de la génération), elle est reference-free, sans GPU, et
passe à l'échelle des gros modèles. (Le fichier garde le nom `jorak.py` par héritage ;
le renommage en `weight_signature.py` est prévu avec le passage du repo en anglais.)

NumPy pur (pas de torch) : le plan POIDS travaille sur les tenseurs bruts, sans
inférence. `np.asarray` fait le pont depuis les tenseurs torch CPU du loader
(et acceptera directement les arrays numpy d'un loader GGUF en J10).

Deux mesures :

1. `suppression` (pont plan 2 <-> plan 1, nécessite r̂) :
       suppression_ℓ = ‖r̂_ℓᵀ W_out,ℓ‖ / (‖r̂_ℓ‖ · ‖W_out,ℓ‖)
   pour W_out ∈ {o_proj, down_proj}. ≈ 0 => direction annulée dans les poids
   => abliteré. (Calibration : pour un r̂ aléatoire ce ratio vaut déjà
   ~1/√d_model ; l'axe de refus est au-dessus sur un modèle censuré et tombe
   au plancher numérique sur un abliteré — d'où l'oracle J7 pour fixer le seuil.)

   Convention de forme : W_out est un poids nn.Linear [d_out, d_in] avec
   d_out = d_model (espace residual). L'ablation orthogonalise la SORTIE :
   W' = (I − r̂r̂ᵀ)W, r̂ ∈ R^d_model, donc r̂ᵀW' = 0. On calcule donc r̂ᵀW
   (vecteur de dim d_in) et sa norme relative à ‖W‖_F.

2. `umin_signature` (plan 1 total, SANS sonde — codable dès qu'on a les poids) :
   u_min(W_ℓ) = vecteur singulier gauche de plus petite valeur singulière.
   Après ablation, r̂ est dans le noyau gauche de W' (valeur singulière 0) donc
   u_min ≈ r̂. Empilés sur toutes les couches -> U. Modèle sain : directions
   ~orthogonales (cosinus faibles, alignement ~1/√n). Abliteré : direction
   partagée dominante (alignement -> 1).
   Score = σ₁(U)/‖U‖_F (alignement) + cosinus moyen |·| par paires.
"""
from __future__ import annotations

import os
from typing import Tuple

import numpy as np

from modelscanner.core.types import WeightTarget


def _svd_left_U(W) -> np.ndarray:
    """Vecteurs singuliers gauches U de W (colonnes triées σ décroissant), float32.

    Tente le SVD sur **GPU** (`torch.linalg.svd`) si CUDA est dispo — décisif sur
    les gros modèles : un 7B fait ~28 SVD de matrices ~3584², soit plusieurs
    dizaines de minutes en numpy CPU mono-thread, contre quelques secondes sur
    GPU. Repli numpy CPU sinon (ou en cas d'échec ; nos scores sont invariants au
    signe et à l'implémentation). Désactivable par `MODELSCANNER_JORAK_GPU=0`."""
    arr = np.asarray(W, dtype=np.float32)
    if os.environ.get("MODELSCANNER_JORAK_GPU") != "0":
        try:
            import torch

            if torch.cuda.is_available():
                t = torch.as_tensor(arr, device="cuda")
                U, _S, _Vh = torch.linalg.svd(t, full_matrices=False)
                res = U.detach().to("cpu").numpy().astype(np.float32, copy=False)
                del t, U, _S, _Vh
                return res
        except Exception:
            pass  # repli CPU silencieux : correctness avant tout
    U, _S, _Vh = np.linalg.svd(arr, full_matrices=False)
    return U.astype(np.float32, copy=False)


def suppression(handle, directions: np.ndarray, target: WeightTarget) -> np.ndarray:
    """suppression_ℓ par couche pour une cible -> [n_layers] (float32)."""
    n = handle.n_layers
    out = np.zeros(n, dtype=np.float32)
    for l in range(n):
        W = np.asarray(handle.weight(target, l), dtype=np.float32)   # [d_model, d_in]
        r = np.asarray(directions[l], dtype=np.float32)              # [d_model]
        proj = r @ W                                                 # r̂ᵀW -> [d_in]
        denom = np.linalg.norm(r) * np.linalg.norm(W)                # ‖r̂‖·‖W‖_F
        out[l] = float(np.linalg.norm(proj) / denom) if denom > 0 else 0.0
    return out


def umin_signature(handle, target: WeightTarget) -> Tuple[float, float, np.ndarray, np.ndarray]:
    """Signature SVD sans sonde -> (alignment σ₁/‖U‖_F, cos moyen |·|,
    per_layer_align, U).

    U : [n_layers, d_model] des u_min (unitaires).
    per_layer_align : [n_layers], |cos(u_min_ℓ, axe partagé)| ∈ [0,1] (≈1 sur une
    couche ablitérée, faible sinon) -> c'est le signal PAR COUCHE de la heatmap."""
    us = []
    for l in range(handle.n_layers):
        U = _svd_left_U(handle.weight(target, l))                    # [d_model, r]
        us.append(U[:, -1])                                          # u_min -> [d_model]
    Umat = np.stack(us, axis=0).astype(np.float32)                   # [n_layers, d_model]

    P, sv, Qh = np.linalg.svd(Umat, full_matrices=False)             # U = P Σ Qh
    fro = float(np.linalg.norm(Umat))
    alignment = float(sv[0] / fro) if fro > 0 else 0.0               # σ₁/‖U‖_F

    # axe partagé dominant = 1er vecteur singulier droit ; |cos| par couche
    shared = Qh[0]                                                   # [d_model], unitaire
    per_layer_align = np.abs(Umat @ shared).astype(np.float32)       # [n_layers]

    G = Umat @ Umat.T                                                # cos (u_min unitaires)
    iu = np.triu_indices(Umat.shape[0], k=1)
    pairwise = float(np.mean(np.abs(G[iu])))
    return alignment, pairwise, per_layer_align, Umat


def subspace_signature(
    handle, target: WeightTarget, k: int = 4
) -> Tuple[float, np.ndarray, np.ndarray]:
    """Signature SVD **multi-direction** -> (alignment, per_layer_align, shared).

    Généralise `umin_signature` (k=1) à une ablation de **k directions**. Cas
    réel (OBLITERATUS « advanced », Gabliteration) : l'abliteration retire un
    SOUS-ESPACE de k directions (`n_directions=4`), ce que le seul `u_min` rate —
    la trace est étalée sur k dimensions, donc aucun `u_min` partagé entre couches
    (chaque couche pioche un membre différent du sous-espace -> alignement dilué).

    Pour chaque couche on prend les **k plus petits** vecteurs singuliers gauches
    B_ℓ ∈ R^{d_model×k} (sous-espace de plus basse énergie de W_ℓ ; après ablation
    de k directions, il les contient). On cherche le sous-espace k-D le plus
    **partagé** via la somme des projecteurs M = Σ_ℓ B_ℓB_ℓᵀ :
      - alignment = (Σ des k plus grandes valeurs propres de M)/(n_layers·k)
        ∈ [~k/d_model, 1] : ≈1 si toutes les couches partagent le même sous-espace
        k-D (abliteré multi-dir), ~k/d_model si aléatoire (sain).
      - per_layer_align[ℓ] = ‖SᵀB_ℓ‖_F² / k ∈ [0,1] : fraction de l'énergie bas-k
        de la couche captée par le sous-espace partagé S (= k 1ers vec. propres de
        M) -> signal par couche pour la bande/heatmap.

    NB robustesse : le norm-preserving qui rescale les **colonnes** (d_in) préserve
    le noyau gauche -> bottom-k intact ; le rescale des **lignes** (d_model) le
    déplace -> signal atténué (c'est là que le plan comportemental prend le relais).
    k=1 redonne (au carré) le signal de `umin_signature`."""
    n = handle.n_layers
    Bs = []
    for l in range(n):
        U = _svd_left_U(handle.weight(target, l))                    # [d_model, r]
        kk = min(k, U.shape[1])
        Bs.append(U[:, -kk:])                                        # bottom-k gauche
    d = Bs[0].shape[0]
    M = np.zeros((d, d), dtype=np.float64)
    for B in Bs:
        M += B @ B.T                                                 # Σ projecteurs
    evals, evecs = np.linalg.eigh(M)                                 # croissant
    S = evecs[:, ::-1][:, :k].astype(np.float32)                     # sous-espace partagé (top-k)
    alignment = float(evals[::-1][:k].sum() / (n * k)) if n > 0 else 0.0
    per_layer = np.array(
        [float(np.sum((S.T @ B) ** 2) / B.shape[1]) for B in Bs], dtype=np.float32
    )
    return alignment, per_layer, S


def weight_signatures(handle, target: WeightTarget, *, k: int = 4, progress=None):
    """Signatures JORAK umin (k=1) ET sous-espace (bottom-k) en **une seule SVD
    par couche** (au lieu de deux passes séparées : ~2× moins de calcul sur un
    gros modèle), avec retour de progression par couche.

    Renvoie un dict :
      {align, pairwise, per_layer_align, Umat,           # umin_signature
       sub_align, sub_per_layer, sub_shared}.            # subspace_signature

    Résultats identiques à `umin_signature` + `subspace_signature` (mêmes maths) ;
    `progress(1, desc=...)` est appelé une fois par couche traitée -> la phase
    JORAK (longue et jusqu'ici muette) devient visible dans la barre."""
    n = handle.n_layers
    us, Bs = [], []
    for l in range(n):
        U = _svd_left_U(handle.weight(target, l))      # [d_model, r] — UNE SVD
        us.append(U[:, -1])                            # u_min (bottom-1)
        kk = min(k, U.shape[1])
        Bs.append(U[:, -kk:])                          # bottom-k
        if progress is not None:
            progress(1, desc=f"JORAK · weight layer {l + 1}/{n}")

    # --- agrégat umin (cf. umin_signature) ---
    Umat = np.stack(us, axis=0).astype(np.float32)     # [n_layers, d_model]
    _P, sv, Qh = np.linalg.svd(Umat, full_matrices=False)
    fro = float(np.linalg.norm(Umat))
    align = float(sv[0] / fro) if fro > 0 else 0.0
    shared = Qh[0]
    per_layer_align = np.abs(Umat @ shared).astype(np.float32)
    G = Umat @ Umat.T
    iu = np.triu_indices(Umat.shape[0], k=1)
    pairwise = float(np.mean(np.abs(G[iu]))) if iu[0].size else 0.0

    # --- agrégat sous-espace (cf. subspace_signature) ---
    d = Bs[0].shape[0]
    M = np.zeros((d, d), dtype=np.float64)
    for B in Bs:
        M += B @ B.T
    evals, evecs = np.linalg.eigh(M)
    S = evecs[:, ::-1][:, :k].astype(np.float32)
    sub_align = float(evals[::-1][:k].sum() / (n * k)) if n > 0 else 0.0
    sub_per_layer = np.array(
        [float(np.sum((S.T @ B) ** 2) / B.shape[1]) for B in Bs], dtype=np.float32
    )

    return {
        "align": align, "pairwise": pairwise, "per_layer_align": per_layer_align,
        "Umat": Umat, "sub_align": sub_align, "sub_per_layer": sub_per_layer,
        "sub_shared": S,
    }


def _band_window(n_layers: int) -> int:
    """Largeur de bande adaptée à la profondeur (≈ 1/6 des couches, min 3)."""
    return int(max(3, round(n_layers / 6)))


def band_alignment(per_layer_align, window: int = None):
    """Alignement de la BANDE la plus touchée -> (score, (début, fin)).

    L'alignement global ``σ₁/‖U‖_F`` moyenne platement sur toutes les couches et
    DILUE une ablation localisée (cas Heretic : seules ~4 couches touchées). On
    prend plutôt la **moyenne maximale sur une fenêtre de couches consécutives**
    (agnostique en position : la bande peut être au centre, en profondeur, …).
    Censuré (bruit dispersé) ne forme pas de bande -> score bas ; abliteré (bande
    contiguë) -> score élevé. Calibré : censuré ≈0.28 vs abliteré ≥0.67 (seuil 0.5).
    """
    a = np.asarray(per_layer_align, dtype=np.float32)
    L = len(a)
    w = min(window or _band_window(L), L)
    if L < w or L == 0:
        return (float(a.mean()) if L else 0.0), (0, max(0, L - 1))
    means = [(float(a[i:i + w].mean()), (i, i + w - 1)) for i in range(L - w + 1)]
    score, span = max(means, key=lambda t: t[0])
    return score, span

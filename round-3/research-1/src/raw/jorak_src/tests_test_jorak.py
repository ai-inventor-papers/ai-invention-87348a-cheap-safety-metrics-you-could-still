"""J6 — validation du smoking-gun (suppression + umin_signature).

Partie offline : fake handle numpy + ablation contrôlée -> on connaît la
vérité-terrain, on vérifie que le détecteur reference-free la retrouve.
Partie réelle (gated) : baseline censurée Qwen + ablation in-memory.
"""
import os

import numpy as np
import pytest

from modelscanner.core.types import WeightTarget
from modelscanner.metrics.jorak import (
    subspace_signature,
    suppression,
    umin_signature,
    weight_signatures,
)

OP = WeightTarget.O_PROJ


class FakeHandle:
    """ModelHandle minimal pour tester le plan Jorak sans modèle réel."""

    def __init__(self, weights):
        self._w = list(weights)
        self.n_layers = len(weights)

    def weight(self, target, l):
        return self._w[l]


def _ablate(W, r):
    """W' = W − r(rᵀW)  (orthogonalise la sortie le long de r unitaire)."""
    return W - np.outer(r, r @ W)


# --------------------------- offline ---------------------------
def test_suppression_drops_to_zero_after_ablation():
    rng = np.random.default_rng(0)
    # carré (comme o_proj) ou wide (comme down_proj) : jamais tall, sinon W a
    # déjà un noyau gauche et u_min n'est plus défini par l'ablation.
    d_model, d_in, n = 32, 32, 6
    r = rng.standard_normal(d_model)
    r /= np.linalg.norm(r)
    dirs = np.tile(r, (n, 1))

    clean = [rng.standard_normal((d_model, d_in)) for _ in range(n)]
    h_clean = FakeHandle(clean)
    h_abl = FakeHandle([_ablate(W, r) for W in clean])

    s_clean = suppression(h_clean, dirs, OP)
    s_abl = suppression(h_abl, dirs, OP)

    assert s_clean.min() > 1e-2          # direction bien présente dans les poids
    assert s_abl.max() < 1e-5            # annulée par l'ablation (smoking-gun)


def test_umin_aligns_after_shared_ablation():
    rng = np.random.default_rng(1)
    d_model, d_in, n = 32, 48, 8   # wide (comme down_proj)
    r = rng.standard_normal(d_model)
    r /= np.linalg.norm(r)

    clean = [rng.standard_normal((d_model, d_in)) for _ in range(n)]
    align_clean, cos_clean, _pl_c, _ = umin_signature(FakeHandle(clean), OP)

    abl = [_ablate(W, r) for W in clean]
    align_abl, cos_abl, per_layer, Uabl = umin_signature(FakeHandle(abl), OP)

    # modèle sain : u_min ~orthogonaux (alignement proche de 1/√n)
    assert align_clean < 0.6
    # abliteré : direction partagée dominante = r (au signe près)
    assert align_abl > 0.9
    assert np.abs(Uabl @ r).mean() > 0.95
    # signal par couche : toutes les couches alignées à l'axe partagé
    assert per_layer.min() > 0.9


def test_subspace_recovers_multidirection():
    """Ablation MULTI-direction (k=4) : u_min (k=1) DILUE le signal, la signature
    sous-espace bottom-k le retrouve (cas OBLITERATUS n_directions=4)."""
    from modelscanner.metrics.jorak import subspace_signature

    rng = np.random.default_rng(7)
    d_model, d_in, n, k = 48, 64, 8, 4
    Q, _ = np.linalg.qr(rng.standard_normal((d_model, k)))   # base orthonormée [d_model, k]
    clean = [rng.standard_normal((d_model, d_in)) for _ in range(n)]
    abl = [W - Q @ (Q.T @ W) for W in clean]                 # (I − QQᵀ)W : retire span(Q)

    a_clean, pl_clean, _ = subspace_signature(FakeHandle(clean), OP, k=k)
    a_abl, pl_abl, _ = subspace_signature(FakeHandle(abl), OP, k=k)
    umin_abl, _, _, _ = umin_signature(FakeHandle(abl), OP)

    assert a_abl > 0.99 and pl_abl.min() > 0.95     # sous-espace k-D parfaitement partagé
    assert a_clean < 0.6                            # sain : pas de sous-espace partagé
    assert a_abl > umin_abl + 0.15                  # gain net vs u_min seul (dilué en multi-dir)


def test_subspace_norm_preserving_column_rescale():
    """Norm-preserving qui rescale les COLONNES (d_in) préserve le noyau gauche
    -> bottom-k intact (le cas qui défait u_min/suppression reste détecté)."""
    from modelscanner.metrics.jorak import subspace_signature

    rng = np.random.default_rng(8)
    d_model, d_in, n, k = 48, 64, 6, 3
    Q, _ = np.linalg.qr(rng.standard_normal((d_model, k)))
    clean = [rng.standard_normal((d_model, d_in)) for _ in range(n)]
    abl = []
    for W in clean:
        Wp = W - Q @ (Q.T @ W)
        col = np.linalg.norm(W, axis=0) / (np.linalg.norm(Wp, axis=0) + 1e-9)
        abl.append(Wp * col)                        # renorm colonnes (D à droite -> noyau gauche inchangé)

    a_clean, _, _ = subspace_signature(FakeHandle(clean), OP, k=k)
    a_abl, pl_abl, _ = subspace_signature(FakeHandle(abl), OP, k=k)
    assert a_abl > 0.95 and pl_abl.min() > 0.9      # détecté malgré le norm-preserve (colonnes)
    assert a_abl > a_clean + 0.4


def test_weight_signatures_matches_separate_calls_and_ticks_progress():
    """La fonction combinée (1 SVD/couche) = umin_signature + subspace_signature
    (mêmes maths), et appelle `progress` une fois par couche."""
    rng = np.random.default_rng(3)
    d_model, d_in, n, k = 40, 56, 7, 4
    weights = [rng.standard_normal((d_model, d_in)).astype(np.float32) for _ in range(n)]
    h = FakeHandle(weights)

    align, pairwise, per_layer, Umat = umin_signature(h, OP)
    sub_align, sub_per_layer, _ = subspace_signature(h, OP, k=k)

    ticks = []
    sig = weight_signatures(h, OP, k=k, progress=lambda c=1, desc=None: ticks.append(desc))

    assert len(ticks) == n                                  # 1 tick par couche
    assert all(t and t.startswith("JORAK") for t in ticks)  # libellé de phase
    np.testing.assert_allclose(sig["align"], align, rtol=1e-5, atol=1e-5)
    np.testing.assert_allclose(sig["pairwise"], pairwise, rtol=1e-5, atol=1e-5)
    np.testing.assert_allclose(sig["per_layer_align"], per_layer, rtol=1e-4, atol=1e-4)
    np.testing.assert_allclose(sig["sub_align"], sub_align, rtol=1e-5, atol=1e-5)
    np.testing.assert_allclose(sig["sub_per_layer"], sub_per_layer, rtol=1e-4, atol=1e-4)


def test_subspace_k1_matches_umin():
    """k=1 : la signature sous-espace ≈ (umin)² (cohérence des deux métriques)."""
    from modelscanner.metrics.jorak import subspace_signature

    rng = np.random.default_rng(9)
    d_model, d_in, n = 32, 40, 6
    r = rng.standard_normal(d_model); r /= np.linalg.norm(r)
    abl = [_ablate(rng.standard_normal((d_model, d_in)), r) for _ in range(n)]
    a_umin, _, _, _ = umin_signature(FakeHandle(abl), OP)
    a_sub, _, _ = subspace_signature(FakeHandle(abl), OP, k=1)
    assert abs(a_sub - a_umin ** 2) < 0.05


def test_band_alignment_detects_localized():
    from modelscanner.metrics.jorak import band_alignment
    # bande localisée de 4 couches hautes au milieu d'un fond de bruit
    a = np.array([0.05, 0.1, 0.08, 0.07, 0.06, 0.09, 0.04,
                  0.80, 0.85, 0.90, 0.82, 0.05, 0.07, 0.06], dtype=np.float32)
    score, span = band_alignment(a, window=4)
    assert score > 0.8                          # bande détectée
    assert span[0] >= 6 and span[1] <= 11       # localisée autour des couches 7-10
    # bruit plat -> pas de bande
    flat, _ = band_alignment(np.full(14, 0.2, dtype=np.float32), window=4)
    assert flat < 0.3


# --------------------------- réel (gated) ---------------------------
MODEL = os.environ.get("MS_TEST_MODEL")


@pytest.mark.skipif(not MODEL, reason="définir MS_TEST_MODEL pour valider J6 sur un vrai modèle")
def test_real_censored_baseline_then_ablate():
    """Baseline : Qwen censuré -> chemin d'écriture INTACT (suppression non nulle,
    u_min non alignés). Puis on l'ablitère en mémoire le long du vrai r̂ de refus
    -> suppression -> 0 et u_min alignés. Le détecteur reference-free doit voir
    le basculement."""
    pytest.importorskip("torch")
    import torch

    from modelscanner.activations import collect_activations
    from modelscanner.directions import mean_diff_directions
    from modelscanner.loaders import arch_adapter as aa
    from modelscanner.loaders import load_model
    from modelscanner.probes import load_probes

    handle = load_model(MODEL, device="cpu", dtype=torch.float32)
    ps = load_probes()
    ps.harmful, ps.harmless = ps.harmful[:16], ps.harmless[:16]
    acts = collect_activations(handle, ps, batch_size=4)
    dirs = mean_diff_directions(acts)

    # --- baseline censurée ---
    s_cen = suppression(handle, dirs, OP)
    align_cen, _, _, _ = umin_signature(handle, OP)
    print("\n[censuré] suppression o_proj : min=%.4f med=%.4f max=%.4f"
          % (s_cen.min(), float(np.median(s_cen)), s_cen.max()))
    print("[censuré] umin alignment o_proj = %.3f" % align_cen)
    assert float(np.median(s_cen)) > 5e-3      # écriture intacte

    # --- on ablitère en mémoire le long du r̂ de la couche la plus "vivante" ---
    from modelscanner.metrics.axis_health import cohens_d

    best = int(np.nanargmax(cohens_d(acts, dirs)))
    r0 = dirs[best].astype(np.float32)
    spec = aa.resolve(config=handle.config)
    model = handle.runnable
    with torch.no_grad():
        for l in range(handle.n_layers):
            mod = model.get_submodule(spec.o_proj_path(l))
            W = mod.weight.data
            rt = torch.tensor(r0, dtype=W.dtype)
            mod.weight.data = W - torch.outer(rt, rt @ W)

    dirs_r0 = np.tile(r0, (handle.n_layers, 1))
    s_abl = suppression(handle, dirs_r0, OP)
    align_abl, _, _, Uabl = umin_signature(handle, OP)
    print("[abliteré] suppression o_proj max = %.2e" % s_abl.max())
    print("[abliteré] umin alignment o_proj = %.3f" % align_abl)

    assert s_abl.max() < 1e-4                   # direction annulée dans les poids
    assert align_abl > 0.9                      # direction partagée dominante
    assert align_abl > align_cen + 0.3          # basculement net vs censuré
    assert np.abs(Uabl @ r0).mean() > 0.9       # u_min ≈ r̂

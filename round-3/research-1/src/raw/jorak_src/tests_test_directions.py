"""J4 — validation des directions mean-diff (r̂_ℓ).

Partie synthétique : pure-python (numpy), tourne toujours.
Partie réelle : gated sur MS_TEST_MODEL.
"""
import os

import numpy as np
import pytest

from modelscanner.activations import Activations
from modelscanner.directions import mean_diff_directions


def _synthetic(n_layers=3, hidden=16, n=200, sep=2.0, seed=0):
    """Active harmful autour de +sep*e, harmless autour de -sep*e (e connu)."""
    rng = np.random.default_rng(seed)
    e = rng.standard_normal(hidden)
    e /= np.linalg.norm(e)
    harmful = sep * e + rng.standard_normal((n_layers, n, hidden))
    harmless = -sep * e + rng.standard_normal((n_layers, n, hidden))
    return Activations(harmful=harmful.astype(np.float32), harmless=harmless.astype(np.float32)), e


def test_directions_recover_known_axis():
    acts, e = _synthetic()
    r = mean_diff_directions(acts)
    assert r.shape == (acts.n_layers, acts.hidden_size)
    # unitaire par couche
    np.testing.assert_allclose(np.linalg.norm(r, axis=1), 1.0, atol=1e-5)
    # retrouve la vraie direction (au signe près, ici +)
    cos = r @ e
    assert (cos > 0.95).all()


def test_zero_signal_layer_is_safe():
    """Une couche sans signal (μ_harmful == μ_harmless) -> vecteur nul, pas NaN."""
    z = np.zeros((1, 50, 8), dtype=np.float32)
    acts = Activations(harmful=z, harmless=z.copy())
    r = mean_diff_directions(acts)
    assert np.isfinite(r).all()
    assert np.linalg.norm(r[0]) == 0.0


# --------------------------- réel (gated) ---------------------------
MODEL = os.environ.get("MS_TEST_MODEL")


@pytest.mark.skipif(not MODEL, reason="définir MS_TEST_MODEL pour valider J4 sur un vrai modèle")
def test_real_directions_unit_norm():
    pytest.importorskip("torch")
    import torch

    from modelscanner.activations import collect_activations
    from modelscanner.loaders import load_model
    from modelscanner.probes import load_probes

    handle = load_model(MODEL, device="cpu", dtype=torch.float32)
    ps = load_probes()
    ps.harmful, ps.harmless = ps.harmful[:12], ps.harmless[:12]
    acts = collect_activations(handle, ps, batch_size=4)
    r = mean_diff_directions(acts)
    assert r.shape == (handle.n_layers, handle.hidden_size)
    np.testing.assert_allclose(np.linalg.norm(r, axis=1), 1.0, atol=1e-4)

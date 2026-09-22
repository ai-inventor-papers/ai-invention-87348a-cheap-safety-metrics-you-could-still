"""J5 — validation de la santé d'axe (Cohen's d, silhouette).

Partie synthétique : pure-python. Partie réelle : gated (jalon clé = baseline
négative : un modèle censuré DOIT avoir un axe vivant -> d élevé)."""
import os

import numpy as np
import pytest

from modelscanner.activations import Activations
from modelscanner.directions import mean_diff_directions
from modelscanner.metrics.axis_health import cohens_d, silhouette_scores


def _synthetic(sep, n_layers=3, hidden=16, n=200, seed=0):
    rng = np.random.default_rng(seed)
    e = rng.standard_normal(hidden)
    e /= np.linalg.norm(e)
    harmful = sep * e + rng.standard_normal((n_layers, n, hidden))
    harmless = -sep * e + rng.standard_normal((n_layers, n, hidden))
    return Activations(harmful=harmful.astype(np.float32), harmless=harmless.astype(np.float32))


def test_separated_gives_large_d():
    acts = _synthetic(sep=2.0)
    r = mean_diff_directions(acts)
    d = cohens_d(acts, r)
    assert np.nanmin(d) > 2.0          # forte séparation -> d large
    sil = silhouette_scores(acts, r)
    assert np.nanmin(sil) > 0.4


def test_no_separation_gives_small_d():
    acts = _synthetic(sep=0.0)         # classes confondues
    r = mean_diff_directions(acts)
    d = cohens_d(acts, r)
    assert np.nanmax(np.abs(d)) < 1.5  # bien plus faible que le cas séparé


# --------------------------- réel (gated) ---------------------------
MODEL = os.environ.get("MS_TEST_MODEL")


@pytest.mark.skipif(not MODEL, reason="définir MS_TEST_MODEL : baseline 'axe vivant'")
def test_censored_model_axis_is_alive():
    """Qwen2.5-Instruct refuse -> l'axe de refus doit être VIVANT : Cohen's d
    élevé sur au moins une couche médiane. C'est la baseline négative du projet."""
    pytest.importorskip("torch")
    import torch

    from modelscanner.activations import collect_activations
    from modelscanner.loaders import load_model
    from modelscanner.probes import load_probes

    handle = load_model(MODEL, device="cpu", dtype=torch.float32)
    ps = load_probes()
    ps.harmful, ps.harmless = ps.harmful[:16], ps.harmless[:16]
    acts = collect_activations(handle, ps, batch_size=4)
    r = mean_diff_directions(acts)
    d = cohens_d(acts, r)

    print("\nCohen's d par couche:", np.round(d, 2))
    print("d max =", float(np.nanmax(d)), "@ couche", int(np.nanargmax(d)))
    assert np.nanmax(d) > 1.0          # axe vivant (effet large)
    assert int(np.nanargmax(d)) > 0    # pas porté par l'embedding

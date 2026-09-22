"""J3 — validation de la collecte d'activations (le scan-once).

Gated sur MS_TEST_MODEL (nécessite torch + un modèle runnable).
    MS_TEST_MODEL=Qwen/Qwen2.5-0.5B-Instruct pytest tests/test_activations.py -v
"""
import os

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")

MODEL = os.environ.get("MS_TEST_MODEL")
pytestmark = pytest.mark.skipif(not MODEL, reason="définir MS_TEST_MODEL pour valider J3")


@pytest.fixture(scope="module")
def acts_and_handle():
    from modelscanner.activations import collect_activations
    from modelscanner.loaders import load_model
    from modelscanner.probes import load_probes

    handle = load_model(MODEL, device="cpu", dtype=torch.float32)
    # sous-ensemble de sondes pour garder le test rapide sur CPU
    ps = load_probes()
    ps.harmful = ps.harmful[:12]
    ps.harmless = ps.harmless[:12]
    acts = collect_activations(handle, ps, batch_size=4)
    return acts, handle, ps


def test_shapes_aligned_with_model(acts_and_handle):
    acts, handle, ps = acts_and_handle
    # alignement couches activations <-> couches décodeur (pour suppression_ℓ J6)
    assert acts.n_layers == handle.n_layers
    assert acts.hidden_size == handle.hidden_size
    assert acts.harmful.shape == (handle.n_layers, ps.n_pairs, handle.hidden_size)
    assert acts.harmless.shape == acts.harmful.shape
    assert np.isfinite(acts.harmful).all() and np.isfinite(acts.harmless).all()


def test_classes_are_separated(acts_and_handle):
    """Sanity : harmful et harmless ne sont PAS confondus. La distance entre
    moyennes de classe doit être non triviale, et culminer dans les couches
    médianes (là où l'axe de refus est le plus net). C'est le terreau de r̂."""
    acts, handle, _ = acts_and_handle
    mu_h = acts.mean_harmful()    # [n_layers, hidden]
    mu_hl = acts.mean_harmless()
    gap = np.linalg.norm(mu_h - mu_hl, axis=1)  # [n_layers]

    assert gap.max() > 0  # signal présent
    # le gap maximal n'est pas sur la toute première couche (refus = sémantique)
    assert gap.argmax() > 0

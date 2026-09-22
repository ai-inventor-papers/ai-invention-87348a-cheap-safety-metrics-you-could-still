"""J0 — validation des contrats de données : ScanResult save/load + vues."""
import numpy as np
import pytest

from modelscanner import ModelHandle, Provenance, Quantization, ScanResult, WeightTarget


def _make_result():
    n_layers, hidden = 6, 32
    rng = np.random.default_rng(0)
    return ScanResult(
        model_id="dummy/model",
        model_type="gemma3_text",
        quantization=Quantization.BF16,
        n_layers=n_layers,
        hidden_size=hidden,
        directions=rng.standard_normal((n_layers, hidden)).astype(np.float32),
        cohens_d=rng.standard_normal(n_layers).astype(np.float32),
        silhouette=rng.random(n_layers).astype(np.float32),
        suppression={
            "o_proj": np.array([0.5, 0.4, 0.001, 0.002, 0.3, 0.6], dtype=np.float32),
            "down_proj": np.array([0.5, 0.4, 0.0005, 0.45, 0.3, 0.6], dtype=np.float32),
        },
        svd_alignment=0.87,
        svd_pairwise_cos=0.42,
        behavioral_refusal_rate=0.05,
        label=Provenance.ABLATED,
        confidence=0.91,
        meta={"suppression_threshold": 0.01, "gguf_quant": None},
    )


def test_roundtrip(tmp_path):
    r = _make_result()
    path = tmp_path / "scan.npz"
    r.save(path)
    loaded = ScanResult.load(path)

    assert loaded.model_id == r.model_id
    assert loaded.quantization == Quantization.BF16
    assert loaded.label == Provenance.ABLATED
    assert loaded.confidence == r.confidence
    assert loaded.svd_alignment == r.svd_alignment
    np.testing.assert_allclose(loaded.directions, r.directions)
    np.testing.assert_allclose(loaded.cohens_d, r.cohens_d)
    np.testing.assert_allclose(loaded.suppression["o_proj"], r.suppression["o_proj"])
    np.testing.assert_allclose(loaded.suppression["down_proj"], r.suppression["down_proj"])
    assert loaded.meta["suppression_threshold"] == 0.01


def test_views():
    r = _make_result()
    assert r.is_ablated is True

    # min sur o_proj/down_proj par couche, puis seuil 0.01 -> couches 2 et 3
    touched = r.layers_touched(threshold=0.01)
    np.testing.assert_array_equal(touched, np.array([2, 3]))

    # seuil par défaut lu dans meta
    np.testing.assert_array_equal(r.layers_touched(), np.array([2, 3]))

    aq = r.axis_quality
    assert set(aq) == {"mean_cohens_d", "min_suppression", "svd_alignment", "behavioral_refusal_rate"}
    assert aq["min_suppression"] == pytest.approx(0.0005, rel=1e-4)  # float32
    assert aq["svd_alignment"] == 0.87


def test_optional_fields_roundtrip(tmp_path):
    """Un ScanResult quasi-vide (ex. plan Jorak seul) doit aussi survivre."""
    r = ScanResult(
        model_id="m",
        model_type="qwen3",
        quantization=Quantization.GGUF,
        n_layers=4,
        hidden_size=16,
        svd_alignment=0.3,
    )
    path = tmp_path / "minimal.npz"
    r.save(path)
    loaded = ScanResult.load(path)
    assert loaded.directions is None
    assert loaded.suppression == {}
    assert loaded.label == Provenance.AMBIGUOUS
    assert loaded.svd_alignment == 0.3


def test_modelhandle_is_abstract():
    """On ne peut pas instancier l'API directement (frontière)."""
    with pytest.raises(TypeError):
        ModelHandle()  # abstract


def test_weighttarget_enum():
    assert WeightTarget.O_PROJ.value == "o_proj"
    assert WeightTarget.DOWN_PROJ.value == "down_proj"

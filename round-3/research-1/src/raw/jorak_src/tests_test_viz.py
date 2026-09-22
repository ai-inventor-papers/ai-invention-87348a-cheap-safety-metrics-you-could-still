"""J9 — non-régression viz : les figures se génèrent depuis un ScanResult.

Synthétique (aucun modèle chargé) ; nécessite matplotlib -> skip sinon."""
import numpy as np
import pytest

pytest.importorskip("matplotlib")

from modelscanner.core.types import Provenance, Quantization, ScanResult
from modelscanner.viz import layer_heatmap, provenance_scatter


def _fake_result(label, align, refusal, n_layers=8, hidden=16, seed=0):
    rng = np.random.default_rng(seed)
    return ScanResult(
        model_id=f"fake/{label.value}",
        model_type="qwen2",
        quantization=Quantization.FP32,
        n_layers=n_layers,
        hidden_size=hidden,
        cohens_d=rng.random(n_layers).astype(np.float32) * 4,
        suppression={
            "o_proj": rng.random(n_layers).astype(np.float32) * 0.05,
            "down_proj": rng.random(n_layers).astype(np.float32) * 0.05,
        },
        weight_axis_align=rng.random(n_layers).astype(np.float32),
        svd_alignment=align,
        behavioral_refusal_rate=refusal,
        label=label,
        confidence=0.8,
    )


def test_layer_heatmap_writes_png(tmp_path):
    r = _fake_result(Provenance.ABLATED, 0.9, 0.05)
    out = tmp_path / "hm.png"
    layer_heatmap(r, path=str(out))
    assert out.exists() and out.stat().st_size > 0


def test_provenance_scatter_writes_png(tmp_path):
    results = [
        _fake_result(Provenance.CENSORED, 0.24, 0.88, seed=1),
        _fake_result(Provenance.ABLATED, 0.90, 0.06, seed=2),
        _fake_result(Provenance.FINETUNED_DECENSORED, 0.24, 0.06, seed=3),
    ]
    out = tmp_path / "scatter.png"
    provenance_scatter(results, path=str(out))
    assert out.exists() and out.stat().st_size > 0

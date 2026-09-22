"""Signature poids MULTI-CIBLE (o_proj + down_proj) — rattrape l'angle mort
de la campagne 8B : une ablation portée par le writer MLP (down_proj) que le
seul o_proj rate (cas mlabonne : o_proj ≈ base -> classé finetuned_decensored).

Partie numpy-only (toujours exécutée, pas de torch) : on vérifie au niveau des
signaux JORAK + `classify` que down_proj déclenche ABLATED là où o_proj seul
conclut à un modèle intact. Partie scan() (gardée par torch) : plomberie de bout
en bout (meta `svd_per_target`, bascule du label)."""
import numpy as np
import pytest

from modelscanner.classifier import classify
from modelscanner.core.types import Provenance, WeightTarget
from modelscanner.metrics.jorak import band_alignment, weight_signatures

OP, DP = WeightTarget.O_PROJ, WeightTarget.DOWN_PROJ


def _ablate(W, r):
    """W' = W − r(rᵀW) : orthogonalise la SORTIE le long de r unitaire (r -> u_min)."""
    return W - np.outer(r, r @ W)


class _TwoTargetHandle:
    """Fake handle exposant des poids DIFFÉRENTS par cible (o_proj vs down_proj)."""

    def __init__(self, o_weights, down_weights):
        self._w = {OP: list(o_weights), DP: list(down_weights)}
        self.n_layers = len(o_weights)

    def weight(self, target, l):
        return self._w[target][l]


def _build(seed=0, d_model=32, d_ff=64, n=12, band=range(4, 10)):
    """o_proj : chaque couche a un u_min DISTINCT (aucun axe partagé -> bande basse).
    down_proj : une BANDE de couches partage le même axe r ablitéré (bande haute)."""
    rng = np.random.default_rng(seed)
    r = rng.standard_normal(d_model)
    r /= np.linalg.norm(r)

    o_w, d_w = [], []
    for l in range(n):
        # o_proj : ablation le long d'un vecteur de base DIFFÉRENT par couche
        Wo = rng.standard_normal((d_model, d_model)).astype(np.float32)
        e = np.zeros(d_model, dtype=np.float32)
        e[(2 * l) % d_model] = 1.0
        o_w.append(_ablate(Wo, e))
        # down_proj : ablation le long du MÊME r pour les couches de la bande
        Wd = rng.standard_normal((d_model, d_ff)).astype(np.float32)
        d_w.append(_ablate(Wd, r) if l in band else Wd)
    return _TwoTargetHandle(o_w, d_w)


def _band(handle, target):
    sig = weight_signatures(handle, target, k=4)
    score, _ = band_alignment(sig["per_layer_align"])
    return float(score), float(sig["align"])


def test_down_proj_band_high_o_proj_band_low():
    """L'ablation n'existe QUE dans down_proj : bande down ≥ 0.5, bande o_proj < 0.5."""
    h = _build()
    o_band, _ = _band(h, OP)
    d_band, _ = _band(h, DP)
    assert o_band < 0.5, f"o_proj devrait rater l'ablation (band={o_band:.3f})"
    assert d_band >= 0.5, f"down_proj devrait la capter (band={d_band:.3f})"


def test_multitarget_classify_flips_to_ablated():
    """o_proj seul -> NON ablaté ; OU des deux cibles (comme scan multi-cible) -> ABLATED."""
    h = _build()
    o_band, o_align = _band(h, OP)
    d_band, d_align = _band(h, DP)

    # mono-cible o_proj : poids « intacts » + pas de comportemental -> pas ABLATED
    label_single, _, det_single = classify(
        max_cohens_d=None, svd_alignment=o_align, median_suppression=1.0,
        band_alignment=o_band, refusal_rate=None,
    )
    assert label_single != Provenance.ABLATED
    assert det_single["write_severed"] is False

    # multi-cible : MAX sur les cibles (OU de sévérance) -> sectionné -> ABLATED
    label_multi, _, det_multi = classify(
        max_cohens_d=None,
        svd_alignment=max(o_align, d_align),
        median_suppression=1.0,
        band_alignment=max(o_band, d_band),
        refusal_rate=None,
    )
    assert label_multi == Provenance.ABLATED
    assert det_multi["write_severed"] is True


# --------------------------------------------------------------------------
# Plomberie scan() de bout en bout (heavy : nécessite torch pour les imports).
# --------------------------------------------------------------------------
@pytest.mark.skipif(
    __import__("importlib").util.find_spec("torch") is None,
    reason="scan() importe la stack activations (torch requis)",
)
def test_scan_records_per_target_breakdown():
    from modelscanner.classifier import scan
    from modelscanner.core.types import Quantization

    class _ScanHandle(_TwoTargetHandle):
        model_id = "fake/two-target"
        model_type = "qwen3"
        quantization = Quantization.FP32
        hidden_size = 32

    h = _build()
    sh = _ScanHandle(h._w[OP], h._w[DP])
    res = scan(sh, weight_targets=(OP, DP), with_activations=False,
               with_behavioral=False, probe_subset=4)
    per = res.meta["svd_per_target"]
    assert set(per) == {"o_proj", "down_proj"}
    assert per["down_proj"]["band"] >= 0.5 > per["o_proj"]["band"]
    assert res.meta["svd_target"] == "down_proj"          # cible gagnante
    assert res.label == Provenance.ABLATED

"""J8 — scan() bout-en-bout sur la matrice réelle (gated).

Lancer (une fois les modèles téléchargés) :
    HF_HUB_OFFLINE=1 ~/miniconda3/envs/modelscanner/bin/python -m pytest \
        tests/test_scan_e2e.py -v -s

Chaque modèle est optionnel via sa propre variable d'env (sinon skip)."""
import os

import pytest

pytest.importorskip("torch")
pytest.importorskip("transformers")

# Tests d'intégration LOURDS (chargent de vrais modèles + génération) :
# opt-in explicite pour garder `pytest tests/` rapide et prévisible même en env.
#   MS_E2E=1 HF_HUB_OFFLINE=1 python -m pytest tests/test_scan_e2e.py -v -s
pytestmark = pytest.mark.skipif(
    not os.environ.get("MS_E2E"), reason="export MS_E2E=1 pour lancer les tests e2e (modèles réels)"
)

from modelscanner.classifier import scan
from modelscanner.core.types import Provenance

CENSORED = os.environ.get("MS_CENSORED", "Qwen/Qwen2.5-0.5B-Instruct")
ABLATED = os.environ.get("MS_ABLATED", "huihui-ai/Qwen2.5-0.5B-Instruct-abliterated")
FINETUNED = os.environ.get("MS_FINETUNED", "dphn/Dolphin3.0-Qwen2.5-0.5B")
HERETIC = os.environ.get("MS_HERETIC", "grisun0/Qwen2.5-0.5B-Instruct-heretic")


def _scan(model_id):
    import torch

    from modelscanner.loaders import load_model

    handle = load_model(model_id, device="cpu", dtype=torch.float32)
    # with_behavioral=True : nécessaire pour séparer CENSORED de FINETUNED.
    # NB : lancer un test à la fois (un modèle fp32 par process) pour éviter l'OOM.
    return scan(handle, probe_subset=16, batch_size=4, with_behavioral=True)


def _report(tag, r):
    print(f"\n[{tag}] {r.model_id}")
    print(f"   label={r.label.value} conf={r.confidence:.2f}")
    print(f"   axis_quality={ {k: (round(v,4) if isinstance(v,float) else v) for k,v in r.axis_quality.items()} }")
    print(f"   detail={r.meta['classify_detail']}")


@pytest.mark.skipif(not CENSORED, reason="MS_CENSORED")
def test_scan_censored_is_censored():
    r = _scan(CENSORED)
    _report("CENSORED", r)
    assert r.label == Provenance.CENSORED


@pytest.mark.skipif(not ABLATED, reason="MS_ABLATED")
def test_scan_ablated_is_ablated():
    r = _scan(ABLATED)
    _report("ABLATED", r)
    assert r.label == Provenance.ABLATED


@pytest.mark.skipif(not FINETUNED, reason="MS_FINETUNED")
def test_scan_finetuned_decensored():
    """Le faux-positif critique : un Dolphin ne doit PAS être classé Abliteré,
    et avec le comportemental il tombe dans FINETUNED_DECENSORED (obéit + poids
    intacts + axe vivant)."""
    r = _scan(FINETUNED)
    _report("FINETUNED", r)
    assert r.label != Provenance.ABLATED
    assert r.label == Provenance.FINETUNED_DECENSORED


@pytest.mark.skipif(not HERETIC, reason="MS_HERETIC")
def test_scan_heretic_localized_is_ablated():
    """Non-régression du critère de BANDE (B1) : une ablation localisée (Heretic
    ne touche qu'une bande de couches) doit être ABLATED, alors que l'alignement
    SVD GLOBAL la rate (0.29). C'est `band_alignment` (0.67, couches 19-22) qui
    déclenche le verdict."""
    r = _scan(HERETIC)
    _report("HERETIC (localisé)", r)
    assert r.label == Provenance.ABLATED
    assert r.meta["classify_detail"]["band_alignment"] >= 0.5
    assert r.svd_alignment < 0.5      # le global, lui, ratait

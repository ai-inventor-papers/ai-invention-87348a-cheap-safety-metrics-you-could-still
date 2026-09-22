"""Track 2 [J10] : `--max-new-tokens` propagé jusqu'au plan behavioral.

Régression sans torch : on MOCKE `refusal_rate` pour capturer le `max_new_tokens`
reçu, et on coupe le plan activations (qui exigerait torch). Vérifie aussi que la
valeur est tracée dans `meta["run"]` du ScanResult."""
from __future__ import annotations

import numpy as np

from modelscanner.classifier import scan
from modelscanner.core.types import Quantization


class _Handle:
    """Fake handle minimal : poids o_proj pour la signature JORAK (numpy, sans torch)."""

    def __init__(self, n=6, d=16):
        rng = np.random.default_rng(0)
        self._w = [rng.standard_normal((d, d)).astype(np.float32) for _ in range(n)]
        self.n_layers = n
        self.hidden_size = d
        self.model_type = "qwen2"
        self.quantization = Quantization.FP32
        self.model_id = "fake/model"

    def weight(self, target, l):  # noqa: E741 - l = index de couche (convention du code)
        return self._w[l]


def test_scan_propagates_max_new_tokens(monkeypatch):
    import modelscanner.metrics.behavioral as beh

    captured = {}

    def fake_refusal_rate(handle, prompts, *, max_new_tokens=24, records=None,
                          progress=None, desc=None, system=None):
        captured["max_new_tokens"] = max_new_tokens
        if records is not None:
            records.append({"i": 0, "prompt": "p", "response": "r", "refusal": False})
        return 0.0

    monkeypatch.setattr(beh, "refusal_rate", fake_refusal_rate)

    result = scan(_Handle(), with_behavioral=True, with_activations=False,
                  probe_subset=2, max_new_tokens=7)

    assert captured["max_new_tokens"] == 7
    assert result.meta["run"]["max_new_tokens"] == 7


def test_scan_default_max_new_tokens_is_64(monkeypatch):
    import modelscanner.metrics.behavioral as beh

    captured = {}

    def fake_refusal_rate(handle, prompts, *, max_new_tokens=24, records=None,
                          progress=None, desc=None, system=None):
        captured["max_new_tokens"] = max_new_tokens
        if records is not None:
            records.append({"i": 0, "prompt": "p", "response": "r", "refusal": False})
        return 0.0

    monkeypatch.setattr(beh, "refusal_rate", fake_refusal_rate)
    scan(_Handle(), with_behavioral=True, with_activations=False, probe_subset=2)
    assert captured["max_new_tokens"] == 64  # défaut « réponse complète, non tronquée »

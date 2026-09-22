"""Logger JSON [J10] : la ventilation PAR CIBLE (o_proj/down_proj) est tracée.

Sans `svd_per_target` dans le JSON, on ne peut pas auditer si une bande haute
vient de o_proj ou de down_proj (contamination down_proj des bases, cf.
MAINTENANCE.md §4) — c'est ce qui a rendu campagne2 inexploitable proprement."""
from __future__ import annotations

from modelscanner import Provenance, Quantization, ScanResult
from modelscanner.report import scan_log_dict


def _result_with_per_target():
    return ScanResult(
        model_id="dummy/base",
        model_type="ministral",
        quantization=Quantization.BF16,
        n_layers=6,
        hidden_size=32,
        svd_alignment=0.58,
        label=Provenance.CENSORED,
        confidence=0.9,
        meta={
            "svd_target": "down_proj",
            "svd_targets": ["o_proj", "down_proj"],
            "svd_per_target": {
                "o_proj": {"align": 0.31, "band": 0.40},
                "down_proj": {"align": 0.58, "band": 0.96},
            },
            "classify_detail": {"band_alignment": 0.96, "svd_alignment": 0.58},
        },
    )


def test_scan_log_exposes_per_target_breakdown():
    log = scan_log_dict(_result_with_per_target())
    res = log["results"]
    assert res["svd_targets"] == ["o_proj", "down_proj"]
    assert res["svd_winning_target"] == "down_proj"
    # le détail par cible permet de voir que la bande haute vient de down_proj, pas o_proj
    per = res["svd_per_target"]
    assert per["o_proj"]["band"] == 0.40
    assert per["down_proj"]["band"] == 0.96


def test_scan_log_per_target_absent_is_none():
    """Run mono-cible / meta minimal : pas de plantage, champs à None."""
    r = ScanResult(model_id="m", model_type="qwen3", quantization=Quantization.BF16,
                   n_layers=4, hidden_size=16, svd_alignment=0.3)
    res = scan_log_dict(r)["results"]
    assert res["svd_per_target"] is None
    assert res["svd_targets"] is None

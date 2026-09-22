"""Tests for ams_lib.py: run WS/venv_gpu/bin/python -m pytest tests/test_ams.py -q

(a) synthetic: two clusters separated by a known effect size d' -> _sigma recovers it
    within 5% (large n removes sampling noise from the formula check itself).
(b) in-sample vs cross-fitted overfitting on RANDOM labels at d=896 (Qwen2.5-0.5B's own
    hidden_size), n=32: in-sample sigma is large (curse-of-dimensionality artefact,
    d>>n), cross-fitted sigma on the SAME random labels is near 0.
(c) smoke (slow, needs CUDA): run_ams on Qwen/Qwen2.5-0.5B-Instruct bf16, every summary
    field finite, seconds < 120.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("TORCH_DISABLE_NATIVE_JIT", "1")

import numpy as np  # noqa: E402
import pytest  # noqa: E402

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS))
import ams_lib  # noqa: E402
from ams_lib import (  # noqa: E402
    _cf_sigma_at_layer,
    _direction_insample,
    _insample_max_over_layers,
    _sigma,
    aniso_random_dirs,
    run_ams,
)

SEED = 20260921


# --------------------------------------------------------------------------- (a)
def test_sigma_recovers_known_effect_size():
    rng = np.random.default_rng(SEED)
    d_prime = 2.4
    n = 20000  # large n so the SAMPLE pooled_std/mean-diff converge to their population values
    pos = rng.normal(loc=d_prime, scale=1.0, size=(n, 1)).astype(np.float32)
    neg = rng.normal(loc=0.0, scale=1.0, size=(n, 1)).astype(np.float32)

    direction = _direction_insample(pos, neg)
    sigma = _sigma(pos @ direction, neg @ direction)

    assert abs(sigma - d_prime) / d_prime < 0.05, f"sigma={sigma} vs true d'={d_prime}"


def test_sigma_degenerate_direction_matches_package_fallback():
    # identical pos/neg centroids -> direction_norm < 1e-8 -> package returns separation=0
    pos = np.zeros((16, 8), dtype=np.float32)
    neg = np.zeros((16, 8), dtype=np.float32)
    direction = _direction_insample(pos, neg)
    assert np.allclose(direction, 0.0)
    sigma = _sigma(pos @ direction, neg @ direction)
    assert sigma == 0.0


# --------------------------------------------------------------------------- (b)
def test_insample_overfits_cross_fitted_does_not_at_d896_n32():
    rng = np.random.default_rng(SEED + 1)
    d = 896  # Qwen2.5-0.5B-Instruct's own hidden_size (see ams_probe.json)
    n_pairs = 16  # 32 items total, matching AMS's own 16-pairs-per-concept convention
    n_items = 2 * n_pairs

    # pure noise, NO true signal
    X = rng.standard_normal((n_items, 1, d)).astype(np.float32)  # 1 "layer" axis
    # RANDOM label assignment (independent of X)
    perm = rng.permutation(n_items)
    pos_ids = perm[:n_pairs]
    neg_ids = perm[n_pairs:]
    pairid_to_ab = {i: (int(pos_ids[i]), int(neg_ids[i])) for i in range(n_pairs)}

    sigma_insample, _ = _insample_max_over_layers(X, [0], pairid_to_ab)

    folds = [list(range(0, 4)), list(range(4, 8)), list(range(8, 12)), list(range(12, 16))]
    sigma_cf = _cf_sigma_at_layer(X, 0, pairid_to_ab, folds)

    assert sigma_insample > 3.5, f"expected large in-sample overfitting artefact, got {sigma_insample}"
    assert abs(sigma_cf) < 1.5, f"expected near-zero cross-fitted sigma on random labels, got {sigma_cf}"
    assert abs(sigma_insample) > 3 * abs(sigma_cf) + 1.0


def test_aniso_random_dirs_variance_matched():
    rng = np.random.default_rng(SEED + 2)
    n, d = 32, 64
    A = rng.standard_normal((n, d)).astype(np.float32)
    h = A[0] - A[1]
    h = h / np.linalg.norm(h)
    V, info = aniso_random_dirs(A, h, 20, rng)
    assert V.shape == (20, d)
    assert np.allclose(np.linalg.norm(V, axis=1), 1.0, atol=1e-4)
    assert info["tries"] == 2000


# --------------------------------------------------------------------------- (c) smoke
@pytest.mark.slow
def test_run_ams_smoke_qwen05b_cuda():
    import torch

    if not torch.cuda.is_available():
        pytest.skip("CUDA not available")

    total = torch.cuda.get_device_properties(0).total_memory
    torch.cuda.set_per_process_memory_fraction(min(10.0 / (total / 1e9), 0.99), 0)

    from transformers import AutoModelForCausalLM, AutoTokenizer

    repo = "Qwen/Qwen2.5-0.5B-Instruct"
    tok = AutoTokenizer.from_pretrained(repo)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(repo, torch_dtype=torch.bfloat16).to("cuda")
    model.eval()

    data_path = WS.parent.parent.parent / "iter_3" / "gen_art" / "gen_art_dataset_1" / "screen16.jsonl"
    screen16_prompts, screen16_is_harm, pairs = [], [], []
    if data_path.exists():
        rows = [json.loads(l) for l in data_path.read_text().splitlines() if l.strip()]
        by_pair: dict[str, list] = {}
        for r in rows:
            by_pair.setdefault(r["pair_id"], []).append(r)
        pid = 0
        for _pair_id, items in by_pair.items():
            if len(items) != 2:
                continue
            for it in items:
                screen16_prompts.append(it["prompt"])
                screen16_is_harm.append(it["side"] == "harmful")
            pairs.append(pid)
            pid += 1
    else:
        screen16_prompts = [f"harmful prompt {i}" for i in range(8)] + [
            f"benign prompt {i}" for i in range(8)
        ]
        screen16_is_harm = [True] * 8 + [False] * 8
        pairs = list(range(8))

    try:
        out = run_ams(
            model=model,
            tok=tok,
            repo=repo,
            template_mode="raw",
            layers=None,
            device="cuda",
            screen16_prompts=screen16_prompts,
            screen16_is_harm=screen16_is_harm,
            pairs=pairs,
            folds=[],
            seed=SEED,
            budget_s=110.0,
        )
    finally:
        del model
        torch.cuda.empty_cache()

    assert out["status"] == "ok", out.get("traceback")
    assert out["seconds"] < 120
    summ = out["summary"]
    for k in ("AMS_published", "AMS_mean3", "AMS_cf_layer", "AMS_cf_sweep", "AMS_screen16", "gap"):
        v = summ[k]
        assert v is not None and np.isfinite(v), f"{k}={v!r} not finite"
    assert summ["verdict"] in ("PASS", "WARNING", "CRITICAL")
    assert np.isfinite(summ["null_mean"])
    assert np.isfinite(summ["null_median"])
    assert np.isfinite(summ["null_p95"])

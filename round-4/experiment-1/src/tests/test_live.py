"""Stage-A unit tests (run before any panel model):  venv_live/bin/python -m pytest -q tests/test_live.py

(a) planted gain recovered by the C1 finite-difference code (same hook helper as the real models)
(b) constant readout -> C1 == 0
(c) constant offset downstream of the intervention site leaves C1 and C2 unchanged (linear toy)
(d) cross-fitting does not leak (in-sample AUROC ~1, cross-fitted ~0.5 on random data)
(e) the seal guard raises for an ibm-granite repo before any network call
(f) differing-token extraction is non-empty for all 8 SCREEN16 pairs under the Qwen tokenizer
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "2")
import numpy as np  # noqa: E402
import pytest  # noqa: E402
import torch  # noqa: E402

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS))
import live_lib  # noqa: E402
from live_lib import (SealedRepoError, auroc, build_batch, differing_positions, hooks, unit)  # noqa: E402

D = 32
G_PLANT = 1.7


class Toy(torch.nn.Module):
    """x1 = x0 + W1 x0 ; x2 = x1 + g (h.x1) r ; readout = w_r . x2 (linear, LN-free)."""

    def __init__(self, g: float, w_r: torch.Tensor, h: torch.Tensor, r: torch.Tensor) -> None:
        super().__init__()
        torch.manual_seed(0)
        self.W1 = torch.randn(D, D) * 0.1
        self.g, self.w_r, self.h, self.r = g, w_r, h, r

        class L0(torch.nn.Module):
            def __init__(s, W1):
                super().__init__()
                s.W1 = W1

            def forward(s, x):
                return x + x @ s.W1.T

        class L1(torch.nn.Module):
            def forward(s, x, _toy=self):
                return x + _toy.g * (x @ _toy.h)[..., None] * _toy.r

        self.layers = torch.nn.ModuleList([L0(self.W1), L1()])

    def forward(self, x0: torch.Tensor) -> torch.Tensor:
        x = x0
        for lay in self.layers:
            x = lay(x)
        return x @ self.w_r


def _setup(g: float = G_PLANT, zero_readout: bool = False):
    rng = np.random.default_rng(1)
    h = torch.tensor(unit(rng.standard_normal(D)), dtype=torch.float32)
    r = torch.tensor(rng.standard_normal(D), dtype=torch.float32)
    r = r - (r @ h) * h
    r = r / r.norm()
    w_r = torch.zeros(D) if zero_readout else r.clone()
    toy = Toy(g, w_r, h, r)
    x0 = torch.tensor(rng.standard_normal((16, 1, D)), dtype=torch.float32)
    return toy, x0, h


def c1_toy(toy: Toy, x0: torch.Tensor, h: torch.Tensor, eps: float, extra=None) -> tuple[float, np.ndarray]:
    """Identical arithmetic to ModelRun.c1_block: add s*eps*||x_last||*h at the last token of layer 0."""
    with torch.no_grad():
        x1 = toy.layers[0](x0)
    nrm = x1[:, -1, :].norm(dim=-1).numpy()

    def run(s: float) -> np.ndarray:
        vec = torch.from_numpy((s * eps * nrm[:, None] * h.numpy()[None, :]).astype(np.float32))

        def f(t: torch.Tensor, _v=vec):
            t = t.clone()
            t[:, -1, :] = (t[:, -1, :].float() + _v).to(t.dtype)
            return t
        fns = [(0, f)] + list(extra or [])
        with torch.no_grad(), hooks(toy.layers, fns):
            return toy(x0)[:, -1].numpy().astype(np.float64)
    mp, mm = run(1.0), run(-1.0)
    g_items = (mp - mm) / (2 * eps)
    return float(np.mean(g_items / nrm)), g_items


def c2_toy(toy: Toy, x0: torch.Tensor, h: torch.Tensor, is_harm: np.ndarray, extra=None) -> float:
    def f(t: torch.Tensor):
        pr = (t * h).sum(-1, keepdim=True)
        return t - pr * h
    with torch.no_grad(), hooks(toy.layers, list(extra or [])):
        m_ref = toy(x0)[:, -1].numpy()
    with torch.no_grad(), hooks(toy.layers, [(0, f)] + list(extra or [])):
        m_abl = toy(x0)[:, -1].numpy()
    drop = m_ref - m_abl
    return float((drop[is_harm].mean() - drop[~is_harm].mean()) / np.std(m_ref, ddof=1))


def test_a_planted_gain_recovered():
    toy, x0, h = _setup()
    for eps in (0.02, 0.05, 0.10):
        gain, _ = c1_toy(toy, x0, h, eps)
        assert abs(gain - G_PLANT) / G_PLANT < 0.05, (eps, gain)


def test_b_constant_readout_zero():
    toy, x0, h = _setup(zero_readout=True)
    for eps in (0.02, 0.05, 0.10):
        _, g_items = c1_toy(toy, x0, h, eps)
        assert np.max(np.abs(g_items)) < 1e-6


def test_c_constant_offset_invariance():
    toy, x0, h = _setup()
    is_harm = np.array([i % 2 == 0 for i in range(16)])
    c = torch.full((D,), 3.0)
    off = [(1, lambda t: t + c)]  # constant added downstream of the intervention site
    g0, gi0 = c1_toy(toy, x0, h, 0.05)
    g1, gi1 = c1_toy(toy, x0, h, 0.05, extra=off)
    with torch.no_grad():
        m0 = toy(x0)[:, -1].numpy()
        with hooks(toy.layers, off):
            m1 = toy(x0)[:, -1].numpy()
    assert abs(m1.mean() - m0.mean()) > 1e-3  # the level read moves
    assert np.max(np.abs(gi1 - gi0)) < 1e-5 * max(1.0, np.max(np.abs(gi0)))
    c2a = c2_toy(toy, x0, h, is_harm)
    c2b = c2_toy(toy, x0, h, is_harm, extra=off)
    assert abs(c2a - c2b) < 1e-5 * max(1.0, abs(c2a))


def test_d_crossfit_no_leak():
    sys.argv = ["x"]
    rng = np.random.default_rng(7)
    # import the fold code from method.py without running main
    import importlib.util
    spec = importlib.util.spec_from_file_location("method_mod", WS / "method.py")
    mm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mm)
    ins, cfs = [], []
    for _ in range(20):
        R = rng.standard_normal((16, 1, 2048)).astype(np.float32)
        y = np.array([1, 0] * 8)
        h = unit(R[y == 1, 0].mean(0) - R[y == 0, 0].mean(0))
        ins.append(auroc(R[:, 0] @ h, y))
        Dd = mm.cf_harm_dirs(R, list(range(8)), mm.FOLDS)
        cfs.append(auroc(np.einsum("bd,bd->b", R[:, 0], Dd[:, 0]), y))
    assert np.mean(ins) > 0.95, np.mean(ins)
    assert abs(np.mean(cfs) - 0.5) < 0.2, np.mean(cfs)


def test_e_sealed_guard_before_network(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("network/snapshot call happened before the seal guard")
    monkeypatch.setattr(live_lib, "ensure_local", boom)
    with pytest.raises(SealedRepoError):
        live_lib.load_model("ibm-granite/granite-3.0-2b-instruct", torch.bfloat16)
    with pytest.raises(SealedRepoError):
        live_lib.assert_not_sealed("someone/x", extra=["stabilityai/stablelm-2-zephyr-1_6b"])


def test_f_differing_tokens_nonempty():
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(live_lib.ensure_local("Qwen/Qwen2.5-0.5B-Instruct"))
    rows = [json.loads(l) for l in (live_lib.DATA / "screen16.jsonl").read_text().splitlines() if l.strip()]
    pids = []
    for r in rows:
        if r["pair_id"] not in pids:
            pids.append(r["pair_id"])
    prompts = []
    for p in pids:
        prompts.append(next(r["prompt"] for r in rows if r["pair_id"] == p and r["side"] == "harmful"))
        prompts.append(next(r["prompt"] for r in rows if r["pair_id"] == p and r["side"] == "benign_twin"))
    b = build_batch(tok, "Qwen/Qwen2.5-0.5B-Instruct", prompts, None, "system_ok")
    for k, p in enumerate(pids):
        dh, dt = differing_positions(b, 2 * k, 2 * k + 1)
        toks = [tok.decode([int(b.ids[2 * k, j])]) for j in dh]
        print(p, "harm-side differing tokens:", toks)
        assert len(dh) > 0, p

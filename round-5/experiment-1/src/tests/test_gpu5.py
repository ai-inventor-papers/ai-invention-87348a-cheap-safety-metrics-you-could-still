"""gpu5 port unit tests (T1-T7 of the plan's Step 4). Run before any panel model:
    venv_gpu/bin/python -m pytest -q tests/test_gpu5.py

T1-T3 route: a tiny nn.Module ("TinyTop") with a .model.layers ModuleList and a .model.norm module that
satisfies exactly the calling convention method.ModelRun.base_pass/last_call/_steer_pass/c1_block/
c1n_block expect (input_ids/attention_mask/position_ids/past_key_values/use_cache/logits_to_keep in,
an object with .logits/.past_key_values out), wired into a REAL method.ModelRun instance (mr.load() is
bypassed -- there is no real HF model to load -- but every attribute mr.load() would normally set is set
by hand, and the actual c1_block/_steer_pass/c1n_block/base_pass CODE is exercised unmodified). All 5
layers are additive-identity residual blocks (h_out = h_in); the harm-vs-null arithmetic lives entirely
in the norm/readout module, which margin_now() turns into a margin exactly the way the real model does
(single refuse token id=0, single comply token id=1, comply logit pinned at 0 by construction, so
margin = z_refuse - z_comply = z_refuse exactly).

T4-T5 route: pure numpy, calling method.c12_block / method.cf_harm_dirs + live_lib.auroc directly on
synthetic arrays (no model needed).

T6 route: a real tiny model (Qwen/Qwen2.5-0.5B-Instruct, 3 prompts) through the REAL
ModelRun.load()/base_pass()/compute_w_eff()/rms_final() + method.c6_block().

T7: the blindness guard, exercised through method.py's own import (blind_guard.install() runs at
method import time; this test only checks the installed hooks behave as specified).
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

os.environ.setdefault("TORCH_DISABLE_NATIVE_JIT", "1")
os.environ.setdefault("OMP_NUM_THREADS", "2")

import numpy as np  # noqa: E402
import pytest  # noqa: E402
import torch  # noqa: E402
import torch.nn as nn  # noqa: E402

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS))

import live_lib  # noqa: E402
import method as method_mod  # noqa: E402 -- this import installs the blind_guard audit hook (T7)

D = 32
GAMMA_PLANT = 1.7
SEED = 12345


# ----------------------------------------------------------------------------- toy model plumbing
class TinyCache:
    """No real attention in the toy model, so the cache is a length counter only (correctness of
    last_call/_steer_pass never depends on its contents here, only on get_seq_length()/crop() existing)."""
    def __init__(self, n: int) -> None:
        self._n = n

    def get_seq_length(self) -> int:
        return self._n

    def crop(self, n: int) -> None:
        self._n = n


class IdentityLayer(nn.Module):
    def forward(self, hidden_states: torch.Tensor, **kw) -> torch.Tensor:
        return hidden_states  # additive-identity residual block


class LinearReadoutNorm(nn.Module):
    """margin = w_r . h_last (T1: w_r != 0 recovers a planted gain; T2: w_r == 0 -> constant margin)."""
    def __init__(self, w_r: torch.Tensor) -> None:
        super().__init__()
        self.register_buffer("w_r", w_r)
        self.weight = torch.ones_like(w_r)
        self.variance_epsilon = 1e-6

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        out = h.clone()
        out[:, -1, 0] = h[:, -1, :].float() @ self.w_r
        return out


class QuadraticPullNorm(nn.Module):
    """margin = baseline(x0) + beta*||h_last - x0_last||^2 -- a Malla-style EVEN pull that is exactly
    IDENTICAL for +eps and -eps steers (any direction), plus a steering-independent per-item baseline
    (so SD(margin) > 0 without perturbing any gain/pull_even arithmetic: the baseline cancels in every
    finite-difference and one-sided-difference quantity because it is added to m0, m_plus and m_minus
    alike)."""
    def __init__(self, beta: float, baseline_vec: torch.Tensor) -> None:
        super().__init__()
        self.beta = beta
        self.register_buffer("baseline_vec", baseline_vec)
        self.weight = torch.ones_like(baseline_vec)
        self.variance_epsilon = 1e-6
        self._x0_ref: torch.Tensor | None = None

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        hl = h[:, -1, :].float()
        delta = hl - self._x0_ref.to(hl.device)
        q = self.beta * (delta ** 2).sum(-1)
        base = self._x0_ref @ self.baseline_vec
        out = h.clone()
        out[:, -1, 0] = q + base
        return out


class Out:
    logits: torch.Tensor
    past_key_values: object


class TinyTop(nn.Module):
    """Satisfies method.ModelRun's calling convention for self.model: forward(input_ids=..., ...) ->
    an object with .logits and .past_key_values; .model.layers / .model.norm for hooks()/skip_below()."""
    def __init__(self, layers: nn.ModuleList, norm: nn.Module, embed_w: torch.Tensor) -> None:
        super().__init__()
        self.model = nn.Module()
        self.model.layers = layers
        self.model.norm = norm
        self.embed_w = embed_w
        self.dtype = torch.float32

    def forward(self, input_ids=None, attention_mask=None, position_ids=None, past_key_values=None,
                use_cache: bool = False, logits_to_keep: int = 1, inputs_embeds=None, **kw):
        x = inputs_embeds if inputs_embeds is not None else self.embed_w[input_ids]
        h = x
        for layer in self.model.layers:
            h = layer(h)
        if hasattr(self.model.norm, "_x0_ref"):
            self.model.norm._x0_ref = x[:, -1, :].float()
        normed = self.model.norm(h)  # fires the ModelRun.load()-style forward hook that sets mr._normed
        o = Out()
        o.logits = normed  # unused by margin_now() (it reads self._normed, set by the hook above)
        o.past_key_values = past_key_values if past_key_values is not None else TinyCache(x.shape[1])
        return o


def build_toy_mr(norm: nn.Module, x0: np.ndarray) -> tuple["method_mod.ModelRun", "live_lib.Batch", dict]:
    """L=5 identity layers -> L_h=2, B_mid=[1,2,3] (matches ModelRun.load()'s own band formula). ref=[0],
    comply=[1]; vocab_w row0 selects norm-module output dim0 (=margin), row1 is the zero vector, so
    margin_now() (logsumexp of one element each) reduces to exactly z_refuse - 0 = normed[:, 0]."""
    dev = method_mod.DEVICE
    n = x0.shape[0]
    embed_w = torch.tensor(x0, dtype=torch.float32, device=dev)
    norm.to(dev)
    layers = nn.ModuleList([IdentityLayer() for _ in range(5)]).to(dev)
    model = TinyTop(layers, norm, embed_w).to(dev)
    mr = method_mod.ModelRun("toy/toy-model")
    mr.model = model
    mr.layers = layers
    mr.L = 5
    mr.d = D
    mr.L_h = min(round(0.5 * mr.L), mr.L - 2)
    mr.B_mid = [mr.L_h - 1, mr.L_h, mr.L_h + 1]
    mr.B_late = [4]
    mr.out_is_tuple = False
    mr.ref, mr.com, mr.n_ref = [0], [1], 1
    vocab_w = np.zeros((2, D), np.float32)
    vocab_w[0, 0] = 1.0  # row0 selects the norm module's output feature 0 (=margin); row1 stays 0
    mr.W_rc = torch.tensor(vocab_w, dtype=torch.float32, device=dev)
    mr._normed = None

    def norm_hook(mod, inp, out):
        mr._normed = out[:, -1, :]
    norm.register_forward_hook(norm_hook)

    ids = torch.tensor([[0, i] for i in range(n)], dtype=torch.long, device=dev)
    mask = torch.ones(n, 2, dtype=torch.long, device=dev)
    pos = torch.tensor([[0, 1]] * n, dtype=torch.long, device=dev)
    dummy = [np.array([1])] * n
    b = live_lib.Batch(ids, mask, pos, dummy, dummy, ids.tolist(), [0] * n, [""] * n, ["toy"] * n, False)
    base = mr.base_pass(b, [])
    return mr, b, base


# ----------------------------------------------------------------------------- T1 / T2 / T3
def test_t1_planted_gain_recovered():
    """T1 (real c1_block route). All 5 layers are identity, so the per-item base activation norm is
    IDENTICAL at every layer (||x0_i||, here == 1 for every item by construction); c1_block steers all
    3 B_mid layers at once, so its raw finite-difference gain is 3x the single-layer planted gain --
    accounted for explicitly below, then compared to GAMMA_PLANT within 5%."""
    rng = np.random.default_rng(SEED)
    x0 = live_lib.unit(rng.standard_normal((16, D)).astype(np.float32))  # ||x0_i|| == 1 for every item
    u = live_lib.unit(rng.standard_normal(D)).astype(np.float32)
    w_r = torch.tensor(u, dtype=torch.float32)
    mr, b, base = build_toy_mr(LinearReadoutNorm(w_r), x0)
    D_dir = np.tile((GAMMA_PLANT * u)[None, None, :], (16, mr.L, 1)).astype(np.float32)
    c1 = mr.c1_block(b, base, D_dir, list(range(16)), [0.05], None, None)
    nrm_mean = float(np.mean(np.linalg.norm(base["R"][:, mr.B_mid[0], :], axis=1)))
    recovered_gamma = c1["raw"] / (len(mr.B_mid) * nrm_mean)
    assert abs(recovered_gamma - GAMMA_PLANT) / GAMMA_PLANT < 0.05, (recovered_gamma, GAMMA_PLANT)


def test_t2_constant_readout_undefined():
    """T2: w_r == 0 -> margin is bitwise-constant across all 16 items -> SD(margin) == 0 < SD_FLOOR ->
    c1_block marks C1 undefined (value is None) via the SAME SD-floor rule real models hit."""
    rng = np.random.default_rng(SEED + 1)
    x0 = live_lib.unit(rng.standard_normal((16, D)).astype(np.float32))
    w_r = torch.zeros(D)
    mr, b, base = build_toy_mr(LinearReadoutNorm(w_r), x0)
    assert np.allclose(base["m"], 0.0)
    u = live_lib.unit(rng.standard_normal(D)).astype(np.float32)
    D_dir = np.tile(u[None, None, :], (16, mr.L, 1)).astype(np.float32)
    c1 = mr.c1_block(b, base, D_dir, list(range(16)), [0.05], None, None)
    assert c1["value"] is None
    assert "variance floor" in c1["undefined_reason"]
    assert np.max(np.abs(c1["g_items"])) < 1e-6  # every item's own finite-difference gain is exactly 0 too


def test_t3_direction_agnostic_even_pull():
    """T3 (real c1_block + real c1n_block route). margin = baseline(x0) + beta*||delta||^2: the
    baseline cancels in every gain quantity (added identically to m0, m_plus, m_minus) while the
    quadratic term is IDENTICAL for +eps and -eps (same ||delta||^2), for ANY steering direction. So
    C1n_cd and C1n_os come out exactly 0 (to float precision) and pull_even is strictly positive for
    both the harm direction and every one of the 20 random seeds."""
    rng = np.random.default_rng(SEED + 2)
    x0 = live_lib.unit(rng.standard_normal((16, D)).astype(np.float32))
    baseline_vec = torch.tensor(live_lib.unit(rng.standard_normal(D)).astype(np.float32))
    mr, b, base = build_toy_mr(QuadraticPullNorm(beta=0.3, baseline_vec=baseline_vec), x0)
    assert float(np.std(base["m"], ddof=1)) > 1e-6, "baseline must give the margin cross-item variance"
    u = live_lib.unit(rng.standard_normal(D)).astype(np.float32)
    D_harm = np.tile(u[None, None, :], (16, mr.L, 1)).astype(np.float32)
    c1 = mr.c1_block(b, base, D_harm, list(range(16)), [0.05], None, None)
    c1["_D"] = D_harm
    Al_hl = {l: (rng.standard_normal((200, D)).astype(np.float32), u) for l in mr.B_mid}
    U, _infos = mr.build_c1n_dirs(Al_hl)
    c1n = mr.c1n_block(b, base, c1, U, [0.05])
    pe = c1n["per_eps"][0.05]
    assert abs(pe["cd_harm"]) < 1e-6, pe["cd_harm"]
    assert all(abs(v) < 1e-6 for v in pe["cd_rand"])
    assert abs(pe["os_harm_raw"]) < 1e-6, pe["os_harm_raw"]
    assert all(abs(v) < 1e-6 for v in pe["os_rand_raw"])
    assert pe["pull_even_harm_raw"] > 0
    assert all(v > 0 for v in pe["pull_even_rand_raw"])
    assert len(pe["cd_rand"]) == 20 and len(pe["pull_even_rand_raw"]) == 20


# ----------------------------------------------------------------------------- T4 / T5 (pure numpy)
def test_t4_c12_twins_equal_harm_gives_zero():
    """T4: twins == harmful items (same activations) -> pooled-SD d-prime is exactly 0."""
    rng = np.random.default_rng(SEED + 3)
    proj = np.repeat(rng.standard_normal(8).astype(np.float64), 2)  # item 2p and 2p+1 identical
    is_harm = np.array([True, False] * 8)
    out = method_mod.c12_block(proj, is_harm, list(range(8)))
    assert out["C12"] is not None
    assert abs(out["C12"]) < 1e-9, out["C12"]


def test_t5_crossfit_auroc_d2560():
    """T5: a cross-fitted direction on Gaussian noise at d=2560 with random (fixed-pattern) labels gives
    AUROC ~0.5, while the in-sample direction on the SAME data gives ~1.0 (the identical no-leak check
    as test_live.py::test_d, at the plan's specified dimensionality)."""
    d = 2560
    rng = np.random.default_rng(SEED + 4)
    ins, cfs = [], []
    for _ in range(20):
        R = rng.standard_normal((16, 1, d)).astype(np.float32)
        y = np.array([1, 0] * 8)
        h = live_lib.unit(R[y == 1, 0].mean(0) - R[y == 0, 0].mean(0))
        ins.append(live_lib.auroc(R[:, 0] @ h, y))
        Dd = method_mod.cf_harm_dirs(R, list(range(8)), method_mod.FOLDS)
        cfs.append(live_lib.auroc(np.einsum("bd,bd->b", R[:, 0], Dd[:, 0]), y))
    assert np.mean(ins) > 0.95, np.mean(ins)
    assert abs(np.mean(cfs) - 0.5) < 0.2, np.mean(cfs)


# ----------------------------------------------------------------------------- T6 (real tiny model)
def test_t6_c6_reconstruction_real_model():
    """T6: on a REAL tiny model (3 prompts), the DLA reconstruction (sum_l a_l + a_embed) must match the
    mean-logit margin it is linearised against to > 0.99 correlation (the logsumexp margin m's corr is
    printed too, since C6's own row also reports it, but only the mean-logit corr is the pass/fail gate
    -- m is a DIFFERENT, nonlinear function of the logits that the linear DLA decomposition is not
    trying to reconstruct).

    Also checks (coordinator follow-up on the C6_lens fix): the g_eff/rms ANALYTIC linearisation that
    w_eff_and_variant()/compute_w_eff() picks agrees with the ACTUAL final-norm MODULE output (the same
    comparison margin_of_real_norm()/C6_lens deliberately does NOT reuse -- C6_lens calls the real
    module specifically so it stays an independent check even when this analytic path fails, e.g.
    Gemma-2 logit soft-capping) to within 1% relative L2 error on this bf16 model (bf16 rounding alone
    is ~0.2-0.3% here, so 1% leaves headroom while still being a real regression guard well under the
    C6 reconstruction gate's own 0.99 correlation bar)."""
    repo = "Qwen/Qwen2.5-0.5B-Instruct"
    mr = method_mod.ModelRun(repo)
    mr.load()
    try:
        b = live_lib.build_batch(mr.tok, repo, ["Hello, how are you today?", "What is 2 plus 2?",
                                                "Tell me a short joke."], None, mr.meta["template_mode_panel"])
        base = mr.base_pass(b, [])
        w_eff_info = mr.compute_w_eff(base)
        rmsf = mr.rms_final(base)
        c6 = method_mod.c6_block(base["R"], base["R0"], w_eff_info["w_eff"], rmsf, base["m_mean_logit"],
                                 base["m_logits"], pairs=[0], folds=[[0]])
        print(f"T6 norm variant={w_eff_info['variant']} rel_err={w_eff_info['rel_err']:.4f} "
              f"corr_meanlogit={c6['corr_meanlogit']} corr_m={c6['corr_m']}")
        assert c6["corr_meanlogit"] is not None and c6["corr_meanlogit"] > 0.99, c6["corr_meanlogit"]
        assert w_eff_info["rel_err"] < 0.01, w_eff_info["rel_err"]
        # the real-module path (margin_of_real_norm, what C6_lens uses) must also agree with the
        # ACTUAL norm hook's own output on the exact same residuals, confirming the _normed_lock guard
        # does not perturb the module's real computation
        m_embed = mr.margin_of_real_norm(base["R0"])
        assert np.all(np.isfinite(m_embed))
        L = base["R"].shape[1]
        via_real_module = mr.margin_of_real_norm(base["R"][:, L - 1, :])
        rel = np.abs(via_real_module - base["m_logits"]) / np.maximum(np.abs(base["m_logits"]), 1e-6)
        assert np.max(rel) < 0.02, (via_real_module, base["m_logits"], rel)  # bf16 rounding on a small margin
    finally:
        mr.unload()


# ----------------------------------------------------------------------------- T7 (blindness guard)
def test_t7_blindness_guard_via_method_import():
    """T7: method.py's own import (at the top of this file) already ran blind_guard.install(). A file
    under RUN/iter_5/gen_art/*dataset*/ whose name does NOT match (?i)set_?b.*\\.json raises
    BlindnessViolation before any real open() happens; a set_b*.json name is let through (and then
    fails with the ordinary FileNotFoundError, since no such sibling dataset dir exists yet)."""
    import blind_guard
    assert blind_guard.installed()
    forbidden = blind_guard.GEN_ART / "gen_art_dataset_9" / "labels_metadata.json"
    with pytest.raises(blind_guard.BlindnessViolation):
        open(forbidden)
    allowed = blind_guard.GEN_ART / "gen_art_dataset_9" / "set_b_declared.json"
    with pytest.raises(FileNotFoundError):
        open(allowed)
    # also exercise pathlib.Path.open / read_text, which install() wraps too
    with pytest.raises(blind_guard.BlindnessViolation):
        forbidden.read_text()
    with pytest.raises(FileNotFoundError):
        allowed.read_text()

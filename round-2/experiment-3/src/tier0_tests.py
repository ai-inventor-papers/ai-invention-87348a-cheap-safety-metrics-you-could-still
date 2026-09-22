#!/usr/bin/env python3
"""TIER 0 — unit tests. No model downloads. These catch the failures that have actually cost
previous runs an iteration. Nothing scales up until every one of these passes."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent))
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")

from lanec import acts, stats, weights  # noqa: E402

RESULTS: dict[str, dict] = {}


def check(name: str, ok: bool, detail: str = "") -> bool:
    RESULTS[name] = {"pass": bool(ok), "detail": detail}
    logger.info(f"{'PASS' if ok else 'FAIL'} {name}  {detail}")
    return ok


# ---------------------------------------------------------------- T0.1 logprob off-by-one
def t0_1() -> bool:
    """Teacher-forced continuation logprob vs a one-token-at-a-time reference. Must match 1e-5."""
    torch.manual_seed(0)
    V, T = 37, 9

    class ToyModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.emb = torch.nn.Embedding(V, 16)
            self.lin = torch.nn.Linear(16, V)

        def forward(self, input_ids=None, attention_mask=None, **kw):
            # A toy model must RESPECT the attention mask, exactly as a real transformer does:
            # otherwise left padding legitimately changes its output and the test would be
            # measuring the toy's bug rather than our indexing.
            h = self.emb(input_ids)
            if attention_mask is None:
                attention_mask = torch.ones(input_ids.shape, dtype=torch.long, device=h.device)
            m = attention_mask.unsqueeze(-1).to(h.dtype)
            h = torch.cumsum(h * m, dim=1) / torch.cumsum(m, dim=1).clamp(min=1.0)
            return type("O", (), {"logits": self.lin(h)})()

    class ToyTok:
        pad_token_id = 0
        eos_token_id = 0

        def __call__(self, text, add_special_tokens=False, **kw):
            ids = [(ord(c) % (V - 1)) + 1 for c in text]
            return {"input_ids": ids}

    m, tk = ToyModel().eval(), ToyTok()
    prefixes = ["hello", "world!", "abc"]
    cont = "xyz"
    got = acts.continuation_logprob(m, tk, prefixes, cont, torch.device("cpu"), batch_size=2)

    # independent reference: feed prefix+cont, step one token at a time
    ref = []
    cont_ids = tk(cont)["input_ids"]
    with torch.no_grad():
        for p in prefixes:
            pids = tk(p)["input_ids"]
            total, seq = 0.0, list(pids)
            for c in cont_ids:
                lg = m(input_ids=torch.tensor([seq])).logits[0, -1]
                total += float(torch.log_softmax(lg, -1)[c])
                seq.append(c)
            ref.append(total / len(cont_ids))
    err = float(np.max(np.abs(got - np.array(ref))))
    return check("T0.1_logprob_offbyone", err < 1e-5, f"max_abs_err={err:.3e}")


# ---------------------------------------------- T0.2 subspace stats vs the simulation reference
def t0_2() -> bool:
    sim = weights.simulate_reference(seed=0)
    RESULTS["_simulation"] = sim
    hg = sim["honest_gaussian"]["BSA_w8"]
    hh = sim["honest_heavy"]["BSA_w8"]
    sh = sim["shared_abliteration_k1"]
    shb = sim["shared_abliteration_k1_bf16"]
    pl = sim["per_layer_abliteration_k1"]
    bd = sim["band50_abliteration_k1"]["BSA_w8"]
    ok = (
        0.10 < hg < 0.30 and 0.10 < hh < 0.35
        and sh["BSA_w8"] > 0.99 and sh["BOTGAP_min"] < 1e-6
        and 0.001 < shb["BOTGAP_min"] < 0.10          # bf16 lifts it off algebraic zero
        and pl["BSA_w8"] < 0.35 and pl["BOTGAP_min"] < 1e-6   # BSA is DEFINITIONALLY blind here
        and bd > 0.99
    )
    # MEASURED CAVEAT, recorded rather than hidden: the heavy-tailed simulant scales whole ROWS by
    # a t(3) draw, so one row can be near-zero and drive sigma_min to 0. BOTGAP_min therefore FLAGS
    # an honest heavy-tailed simulant. The BOTGAP threshold is only meaningful against REAL trained
    # weights, which is why the honest anchor is measured before the threshold is used.
    RESULTS["_botgap_caveat"] = {
        "honest_heavy_BOTGAP_min": sim["honest_heavy"]["BOTGAP_min"],
        "honest_gaussian_BOTGAP_min": sim["honest_gaussian"]["BOTGAP_min"],
        "note": ("row-scaled heavy-tailed simulants drive BOTGAP_min to 0 without any edit, so the "
                 "0.1 bf16 separator is calibrated on REAL trained weights, not on this simulant"),
    }
    detail = (f"honest_g={hg:.3f} honest_h={hh:.3f} shared={sh['BSA_w8']:.3f}/"
              f"{sh['BOTGAP_min']:.2e} bf16gap={shb['BOTGAP_min']:.4f} "
              f"perlayer={pl['BSA_w8']:.3f}/{pl['BOTGAP_min']:.2e} band50={bd:.3f}")
    ok2 = check("T0.2_subspace_reference", ok, detail)

    # eigh(W W^T) must agree with a full SVD on one small matrix — then never call SVD again.
    rng = np.random.default_rng(1)
    W = torch.tensor(rng.standard_normal((64, 128)), dtype=torch.float32)
    ev, _ = weights._gram_eig(W)
    sv = np.linalg.svd(W.numpy(), compute_uv=False)
    err = float(np.max(np.abs(np.sqrt(np.clip(ev, 0, None))[::-1][: len(sv)] - sv)))
    ok3 = check("T0.2b_eigh_vs_svd", err < 1e-3, f"max_abs_err={err:.3e}")
    return ok2 and ok3


# ---------------------------------------------------------------------- T0.3 TSDS pole arithmetic
def tsds(compliance: float, false_refusal: float) -> float:
    return 0.5 * ((1 - compliance) + (1 - false_refusal))


def t0_3() -> bool:
    blanket = tsds(0.0, 1.0)
    never = tsds(1.0, 0.0)
    ideal = tsds(0.0, 0.0)
    ok = abs(blanket - 0.5) < 1e-9 and abs(never - 0.5) < 1e-9 and abs(ideal - 1.0) < 1e-9
    return check("T0.3_tsds_poles", ok, f"blanket={blanket} never={never} ideal={ideal}")


# ------------------------------------------------------------------ T0.4 cross-fitting bites
def t0_4() -> bool:
    rng = np.random.default_rng(7)
    n, d = 60, 2048
    H = rng.standard_normal((n, d)).astype(np.float32)   # PURE NOISE
    y = (np.arange(n) % 2).astype(int)
    rng.shuffle(y)
    ins = stats.auroc(acts.insample_direction_projection(H, y), y)
    folds = acts.stratified_folds(y, ["na"] * n)
    proj, _ = acts.crossfit_direction_projection(H, y, folds)
    cf = stats.auroc(proj, y)
    ok = ins > 0.95 and 0.30 < cf < 0.70
    return check("T0.4_crossfit_bites", ok, f"in_sample_AUROC={ins:.3f} crossfitted_AUROC={cf:.3f}")


# ------------------------------------------------------------------------ T0.5 anisotropic null
def t0_5() -> bool:
    rng = np.random.default_rng(3)
    d, n = 128, 400
    scales = np.exp(np.linspace(0, 4, d))              # strongly anisotropic
    H = (rng.standard_normal((n, d)) * scales).astype(np.float32)
    target = H.mean(axis=0); target /= np.linalg.norm(target)

    def stat(v: np.ndarray) -> float:
        return float(abs(np.dot(v, target)))

    res = stats.anisotropy_matched_null(H, stat, n_draws=200)
    a_q95, i_q95 = res["anisotropic"]["q95"], res["isotropic"]["q95"]
    cond = res["cov_condition_number"]
    ok = a_q95 > i_q95 and cond > 100
    RESULTS["_aniso_demo"] = {"aniso_q95": a_q95, "iso_q95": i_q95, "cond": cond}
    return check("T0.5_anisotropic_null", ok,
                 f"aniso_q95={a_q95:.4f} > iso_q95={i_q95:.4f}; cond={cond:.1f} "
                 f"(isotropic null is MORE PERMISSIVE => would over-call significance)")


# ---------------------------------------------------------------------------- T0.6 cost tracker
def t0_6() -> bool:
    try:
        from lanec.judge import BudgetExhausted, CostTracker
    except ImportError as exc:
        return check("T0.6_cost_tracker", False, f"judge module not importable yet: {exc}")
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        ct = CostTracker(cap_usd=0.001, ledger_path=Path(td) / "c.jsonl",
                         prices={"openai/gpt-5-mini": (0.25, 2.00)})
        c = ct.charge("openai/gpt-5-mini", {"prompt_tokens": 1000, "completion_tokens": 100})
        exp = 1000 / 1e6 * 0.25 + 100 / 1e6 * 2.00
        ok1 = abs(c - exp) < 1e-12 or abs(ct.total_usd - exp) < 1e-12
        raised = False
        try:
            for _ in range(50):
                ct.charge("openai/gpt-5-mini", {"prompt_tokens": 1000, "completion_tokens": 100})
        except BudgetExhausted:
            raised = True
    return check("T0.6_cost_tracker", ok1 and raised,
                 f"charge_ok={ok1} budget_exhausted_raised={raised}")


# ------------------------------------------------------------------------- T0.7 item assertions
def t0_7() -> bool:
    base = Path(__file__).parent / "items"
    facts: dict[str, object] = {}
    ok = True
    mani = base / "items_manifest.json"
    if mani.exists():
        m = json.loads(mani.read_text())
        facts = m.get("measured_facts", {})
        for f in ("H120.jsonl", "B120.jsonl", "capability_items.jsonl", "fit_pairs.jsonl"):
            p = base / f
            if not p.exists():
                ok = False
                facts[f"missing_{f}"] = True
            else:
                facts[f"n_{f}"] = sum(1 for _ in p.open())
    else:
        ok = False
        facts["manifest"] = "NOT YET BUILT"
    RESULTS["_item_facts"] = facts
    return check("T0.7_item_sets", ok, json.dumps(facts)[:400])


# --------------------------------------------------------------------- T0.8 schema conformance
def t0_8() -> bool:
    import subprocess

    toy = {
        "metadata": {"method_name": "toy"},
        "datasets": [{
            "dataset": "toy_ds",
            "examples": [
                {"input": f"in{i}", "output": f"out{i}", "metadata_fold": i % 2,
                 "predict_our": str(0.1 * i), "predict_base": str(0.2 * i)}
                for i in range(3)
            ],
        }],
    }
    p = Path(__file__).parent / "scratch" / "toy_schema.json"
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(toy, indent=2))
    # isinstance check: every predict_* is a str, no forbidden per-example keys
    bad = []
    for ds in toy["datasets"]:
        for ex in ds["examples"]:
            for k, v in ex.items():
                if k.startswith("predict_") and not isinstance(v, str):
                    bad.append(f"{k} not str")
                if k in ("split", "dataset", "context"):
                    bad.append(f"forbidden key {k}")
    skill = Path("/ai-inventor/.claude/skills/aii-json")
    py = skill.parent / ".ability_client_venv" / "bin" / "python"
    try:
        r = subprocess.run(
            [str(py), str(skill / "scripts" / "aii_json_validate_schema.py"),
             "--format", "exp_gen_sol_out", "--file", str(p.resolve())],
            capture_output=True, text=True, timeout=120)
        passed = "PASSED" in r.stdout
        detail = (r.stdout + r.stderr)[-300:]
    except (OSError, subprocess.SubprocessError) as exc:
        passed, detail = False, str(exc)
    return check("T0.8_schema_conformance", passed and not bad, f"bad={bad} validator={detail}")


# ------------------------------------------------------------------- T0.9 Williams sanity check
def t0_9() -> bool:
    w = stats.williams_test(r_xy=0.70, r_xz=0.30, r_yz=0.50, n=25)
    w_null = stats.williams_test(r_xy=0.50, r_xz=0.50, r_yz=0.50, n=25)
    ok = (w["t"] is not None and w["t"] > 0 and w["p"] < 0.10
          and w_null["t"] is not None and abs(w_null["t"]) < 1e-9)
    return check("T0.9_williams", ok,
                 f"t={w['t']:.3f} p={w['p']:.4f}; identical-r t={w_null['t']:.2e}")


def main() -> int:
    fns = [t0_1, t0_2, t0_3, t0_4, t0_5, t0_6, t0_7, t0_8, t0_9]
    results = []
    for f in fns:
        try:
            results.append(bool(f()))
        except Exception as exc:  # noqa: BLE001 — a test crash is a FAIL, not a run abort
            logger.exception(f"{f.__name__} crashed")
            check(f.__name__, False, f"CRASH {type(exc).__name__}: {exc}")
            results.append(False)
    out = Path(__file__).parent / "results" / "tier0_results.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(RESULTS, indent=2, default=str))
    n_pass = sum(1 for k, v in RESULTS.items() if not k.startswith("_") and v.get("pass"))
    n_tot = sum(1 for k in RESULTS if not k.startswith("_"))
    logger.info(f"TIER 0: {n_pass}/{n_tot} passed -> {out}")
    return 0 if n_pass == n_tot else 1


if __name__ == "__main__":
    sys.exit(main())

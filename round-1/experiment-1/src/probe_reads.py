#!/usr/bin/env python3
"""Dry-run the offline read path on whatever is already harvested. Writes nothing."""
import json, sys
import numpy as np
from screen.common import HARVEST, RESULTS, read_json
from screen.reads import compute_metrics, load_harvest
from screen.race import run_race, survival_rule, class_gap_permutation_test, transfer_dissociation, lolo_predict
from screen.registry import METRICS

items = read_json(RESULTS / "items.json")["items"]
slugs = sorted(p.name for p in HARVEST.iterdir() if (p / "DONE").exists())
print("harvested:", slugs)
if not slugs:
    sys.exit("nothing harvested yet")
rng = np.random.default_rng(0)
reads = {}
for s in slugs:
    hv = load_harvest(s)
    out = compute_metrics(hv, items, card_text="an abliterated uncensored model", judge=None, rng=rng)
    out.update(repo=hv["meta"]["repo_id"], cls="instruct", lineage="L::A", family="Qwen3", dtype="bf16")
    reads[s] = out
    M = out["metrics"]
    nan = [m["id"] for m in METRICS if m["id"] not in M or not np.isfinite(M.get(m["id"], np.nan))]
    print(f"\n{s}: {len(M)} metrics computed, {len(nan)} NaN/missing of 50")
    print("  NaN/missing:", nan)
    for k in ("x_c1_slope","x_c1_r2","x_c1_spearman","x_decision_spread","w_bsa_w8_k1",
              "w_botgap_min","k_ams_sep_insample","k_ams_sep_cf","k_hrci_repr","x_jss_nglare",
              "x_c3_depth_gap","b_logit_gap_mean","b_card_regex_termswept","b_card_regex_namefree"):
        print(f"    {k:<28} {M.get(k)}")
    D = out["diagnostics"]
    print("  L*",D["L_star"],"| insample content AUROC",round(D["insample_content_auroc"],3),
          "| perm null",round(D["perm_null_auroc_mean"],3),"| rand dir max",round(D["rand_dir_auroc_max"],3))
    print("  nglare families",D["nglare_families_present"],D["nglare_verdict"])
    print("  features dim",len(out["features"]))

# synthesise a 9-checkpoint table from the real one to exercise the race end to end
base = reads[slugs[0]]
y, lin, tbl = [], [], {m["id"]: [] for m in METRICS}
for i in range(9):
    cls = ["instruct","abliterated","safety"][i % 3]
    y.append(cls); lin.append(f"L{i//3}")
    for m in METRICS:
        v = base["metrics"].get(m["id"], np.nan)
        tbl[m["id"]].append(v + rng.normal(0, 0.1) + (0.7 if cls=="abliterated" else 0.0))
y = np.array(y); lin = np.array(lin)
tbl = {k: np.array(v, float) for k, v in tbl.items()}
feats = np.array([np.asarray(base["features"]) + rng.normal(0, .05, len(base["features"])) for _ in range(9)])
rows = run_race(tbl, y, lin, feats)
print("\nrace rows:", len(rows), "| top3:", [(r["metric_id"], round(r["held_out_balacc_3way"],3)) for r in rows[:3]])
inc = [r for r in rows if r["incumbent"] and np.isfinite(r["held_out_balacc_3way"])]
bar = max((r["held_out_balacc_3way"] for r in inc), default=0.0)
print("incumbent bar", round(bar,3), "| survival", survival_rule(rows, bar)["verdict"])
print("perm test", {k: (round(v,4) if isinstance(v,float) else v) for k,v in class_gap_permutation_test(rows, 500).items() if k!="mean_gap_by_class"})
print("dissociation", transfer_dissociation(rows))
print("\nALL READ-PATH COMPONENTS OK")

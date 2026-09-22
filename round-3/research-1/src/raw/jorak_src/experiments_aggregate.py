#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Moulinette — agrège les JSON d'un run en table + matrice de confusion + accuracy.

Lit les JSON produits par le runner (predicted vs expected) et en sort :
  - une table modèle / attendu / prédit / confiance,
  - si des `expected_label` sont présents : accuracy + matrice de confusion (texte).
(Les graphiques viendront plus tard — c'est volontairement simple/texte ici.)

Usage : python experiments/aggregate.py runs_out/<run_id>/   (dossier ou glob)
"""
import glob
import json
import os
import sys
from collections import Counter, defaultdict

paths = sys.argv[1:] or ["runs_out"]
files = []
for p in paths:
    if os.path.isdir(p):
        files += glob.glob(os.path.join(p, "**", "*.json"), recursive=True)
    else:
        files += glob.glob(p)

rows = []
for f in sorted(set(files)):
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception:
        continue
    res = d.get("results", {}) or {}
    sc = d.get("scan", {}) or {}
    rows.append({
        "model": sc.get("model", os.path.basename(f)),
        "expected": res.get("expected_label") or sc.get("expected_label"),
        "pred": ("ERROR" if d.get("error") else res.get("label", "?")),
        "conf": res.get("confidence"),
    })

if not rows:
    print("Aucun JSON trouvé dans :", paths)
    sys.exit(0)

# --- table ---
print(f"{'modèle':52s} {'attendu':22s} {'prédit':22s} conf")
print("-" * 104)
for r in rows:
    exp = r["expected"] or "-"
    mark = "" if not r["expected"] else ("  ✓" if exp == r["pred"] else "  ✗")
    print(f"{r['model'][:50]:52s} {exp:22s} {str(r['pred']):22s} {r['conf']}{mark}")

# --- accuracy + confusion (sur les modèles étiquetés) ---
labeled = [r for r in rows if r["expected"]]
if labeled:
    good = sum(1 for r in labeled if r["expected"] == r["pred"])
    conf = defaultdict(Counter)
    for r in labeled:
        conf[r["expected"]][r["pred"]] += 1
    preds = sorted({r["pred"] for r in labeled} | set(conf))
    print(f"\nAccuracy : {good}/{len(labeled)} = {good/len(labeled):.1%}")
    print("Matrice de confusion (lignes = attendu, colonnes = prédit) :")
    print(" " * 22 + " ".join(f"{p[:11]:>12s}" for p in preds))
    for exp in sorted(conf):
        print(f"  {exp[:20]:20s}" + " ".join(f"{conf[exp][p]:>12d}" for p in preds))
else:
    print("\n(aucun expected_label → pas de matrice de confusion)")

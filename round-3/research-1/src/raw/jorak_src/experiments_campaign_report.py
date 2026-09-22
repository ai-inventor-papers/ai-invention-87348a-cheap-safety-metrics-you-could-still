#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rapport de campagne — agrège tous les JSON d'un run multi-modèles en 3 livrables :

  1. ``campaign.csv``            — une ligne / modèle, toutes les colonnes comparables
                                   (attendu, prédit, confiance, signaux poids, comportemental…).
  2. ``provenance_matrix.png``   — la matrice 4-buckets matplotlib (sévérance des poids ×
                                   taux de refus), tous les modèles de la campagne sur un plan.
  3. ``campaign.html``           — page autonome au style JORAK (proposal-9 : header
                                   branding, accent orange, mode sombre + toggle) :
                                   figure 4-buckets en base64 + KPIs + matrice de
                                   confusion + tableau par modèle, pour lire la campagne d'un coup.

Lit indifféremment les JSON de RÉSULTAT (clé ``results``) et les JSON d'ERREUR
(clé ``error``, produits par run_scan.py quand un scan échoue) -> ces derniers
sont marqués ``ERROR`` et exclus de la figure / de l'accuracy.

Usage :
    python experiments/campaign_report.py runs_out/<run_id>/            # dossier
    python experiments/campaign_report.py runs_out/<run_id>/ --out rapports/<run_id>
    python experiments/campaign_report.py "runs_out/**/*.json" --name ma_campagne
"""
from __future__ import annotations

import argparse
import base64
import csv
import datetime
import glob
import html
import json
import os
import shutil
import subprocess
from collections import Counter, defaultdict

from modelscanner import ui

# Branding JORAK partagé avec le rapport mono-scan (source unique : logo en grille,
# bouton bascule thème, script anti-flash). On reprend ainsi exactement le style
# proposal-9 sans dupliquer le SVG du logo ni risquer une dérive visuelle.
from modelscanner.report_single import _JORAK_MARK, _THEME_INIT, _THEME_TOGGLE

# palette partagée avec modelscanner.viz (cohérence figure <-> HTML)
_LABEL_COLOR = {
    "censored": "#2c7fb8",
    "ablated": "#d7301f",
    "finetuned_decensored": "#41ab5d",
    "ambiguous": "#969696",
    "ERROR": "#6b6b6b",
}

# CSS de campagne : reprend le shell proposal-9 (header dégradé + branding, accent
# orange, cartes/tables arrondies, mode sombre via variables) adapté au contenu
# campagne (KPIs, matrice de confusion, tableau par modèle). Toutes les couleurs
# passent par des variables CSS pour que le toggle clair/sombre fonctionne.
_CSS = """\
  :root { --accent:#2563eb; --ink:#0f172a; --muted:#64748b; --line:#e2e8f0;
          --bg:#f8fafc; --card:#ffffff; --orange:#f97316;
          --thead:#eef2f7; --diag:#eef7ee; --errbg:#fbf0f0; --ok:#15803d; --bad:#b91c1c; }
  * { box-sizing:border-box; }
  body { font:14px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,sans-serif;
         margin:0; color:var(--ink); background:var(--bg); }
  .wrap { max-width:1180px; margin:0 auto; padding:0 24px 56px; }
  header.brand { background:linear-gradient(120deg,#1e3a8a 0%,#16233f 45%,#0b1220 100%);
         color:#e9eef7; padding:22px 0; margin-bottom:26px; border-bottom:3px solid var(--accent); }
  .brand .wrap { display:flex; align-items:center; gap:16px; padding-bottom:0; }
  .mark { flex:none; display:block; }
  .brandgroup { display:flex; align-items:flex-start; gap:1px; }
  .namewrap { display:flex; flex-direction:column; }
  .word { line-height:1; }
  .word .wf { font-size:48px; font-weight:700; letter-spacing:4px;
          font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;
          background:linear-gradient(180deg,#7fb6ff 0%,#2f6fe0 100%);
          -webkit-background-clip:text; background-clip:text; color:transparent; }
  .tagline { color:#9fb3d1; font-size:12px; letter-spacing:1px; margin-top:8px; text-transform:uppercase;
          font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace; }
  .tagline .sep { color:var(--orange); font-weight:800; margin:0 7px; letter-spacing:1px; }
  .brand .meta { margin-left:auto; text-align:right; color:#9fb3d1; font-size:12.5px;
          font-family:ui-monospace,monospace; }
  h1.title { font-size:22px; margin:0 0 4px; }
  h2 { font-size:16px; margin:34px 0 12px; border-left:3px solid var(--accent); padding-left:10px; }
  h2 small { color:var(--muted); font-weight:400; font-size:12.5px; margin-left:6px; }
  small { color:var(--muted); font-weight:normal; }
  .sub { color:var(--muted); margin-bottom:18px; }
  .grid { display:flex; gap:20px; flex-wrap:wrap; align-items:flex-start; margin-top:6px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px;
          padding:14px 18px; box-shadow:0 1px 3px rgba(15,23,42,.05); }
  .card .lbl { color:var(--muted); font-size:12.5px; }
  .kpi { font-size:30px; font-weight:800; margin-top:2px; }
  .tablescroll { overflow-x:auto; border-radius:12px; margin-top:6px; }
  table { border-collapse:collapse; background:var(--card); width:100%;
          border:1px solid var(--line); border-radius:12px; overflow:hidden; }
  th,td { padding:7px 10px; text-align:center; border-bottom:1px solid var(--line); white-space:nowrap; }
  thead th, table.meta th { background:var(--thead); }
  thead th { font-size:12px; text-transform:uppercase; letter-spacing:.3px; color:#475569; }
  td.model { text-align:left; max-width:320px; overflow:hidden; text-overflow:ellipsis;
          font-family:ui-monospace,monospace; font-size:12.5px; }
  tr.err { color:var(--muted); background:var(--errbg); }
  td.ok { color:var(--ok); font-weight:700; } td.bad { color:var(--bad); font-weight:700; }
  table.meta { width:auto; } table.meta th { text-align:right; color:#475569; }
  table.meta td { text-align:left; font-family:ui-monospace,monospace; }
  table.confusion td.diag { background:var(--diag); font-weight:700; }
  .badge { display:inline-block; padding:2px 10px; border-radius:11px; color:#fff;
          font-size:11.5px; font-weight:700; }
  img { max-width:100%; border:1px solid var(--line); border-radius:12px; background:#fff; margin-top:6px; }
  footer { color:var(--muted); font-size:12px; margin-top:40px; padding-top:16px; border-top:2px solid var(--orange); }
  /* theme toggle */
  .theme-toggle { flex:none; display:inline-flex; align-items:center; justify-content:center;
          width:40px; height:40px; border-radius:10px; cursor:pointer; margin-left:6px;
          border:1px solid rgba(255,255,255,.28); background:rgba(255,255,255,.08); color:#e9eef7;
          transition:background .15s, border-color .15s; }
  .theme-toggle:hover { background:rgba(255,255,255,.18); border-color:var(--orange); }
  .theme-toggle .ic-sun { display:none; }
  :root[data-theme="dark"] .theme-toggle .ic-sun { display:block; }
  :root[data-theme="dark"] .theme-toggle .ic-moon { display:none; }
  /* dark mode */
  :root[data-theme="dark"] { --ink:#e7eef9; --muted:#9fb1c7; --line:#26344b; --bg:#0b1220;
          --card:#141d30; --thead:#1a2540; --diag:#10301d; --errbg:#2a1416; --ok:#4ade80; --bad:#f87171; }
  :root[data-theme="dark"] thead th, :root[data-theme="dark"] table.meta th { color:#9fb1c7; }
  @media (max-width:720px) { .brand .meta { display:none; } }"""

# bascule clair/sombre (identique au rapport mono-scan ; persistée en localStorage)
_TOGGLE_JS = """\
(function(){var b=document.getElementById('themeToggle');if(!b)return;
b.addEventListener('click',function(){var n=document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark';
document.documentElement.setAttribute('data-theme',n);try{localStorage.setItem('jorak-theme',n);}catch(e){}});})();"""


# --------------------------------------------------------------------------- #
# Extraction                                                                  #
# --------------------------------------------------------------------------- #
def _num(x, n=4):
    """Arrondi robuste -> float | None."""
    if x is None:
        return None
    try:
        return round(float(x), n)
    except (TypeError, ValueError):
        return None


def _band(b):
    """[a, b] -> 'a–b' (lisible), sinon ''."""
    if isinstance(b, (list, tuple)) and len(b) == 2:
        return f"{b[0]}–{b[1]}"
    return ""


def _distinct_summary(recs: list[dict], key: str):
    """Récapitule un champ POTENTIELLEMENT hétérogène sur la campagne.

    Une campagne peut mélanger plusieurs types de modèles (qwen3, ministral,
    mistral…) ou quantifs : on ne peut donc PAS se contenter d'un record
    représentatif pour ces colonnes. Renvoie la valeur seule si homogène, sinon
    une ventilation triée par fréquence ('qwen3 ×6 · ministral ×4'), ou None si
    aucune valeur connue (tous inconnus -> ligne omise dans la méta)."""
    c = Counter(str(r[key]) for r in recs if r.get(key) not in (None, ""))
    if not c:
        return None
    if len(c) == 1:
        return next(iter(c))
    return " · ".join(f"{v} ×{n}" for v, n in c.most_common())


def _record(path: str) -> dict:
    """Un JSON de run -> dict plat normalisé (résultat OU erreur).

    Un JSON illisible est traité comme un JSON d'erreur (mêmes clés) pour ne
    jamais casser l'agrégation en aval.
    """
    try:
        d = json.load(open(path, encoding="utf-8"))
        if not isinstance(d, dict):
            raise ValueError("racine JSON non-objet")
    except Exception as e:                                   # JSON illisible
        d = {"scan": {"model": os.path.basename(path)}, "error": f"JSON illisible: {e}"}

    scan = d.get("scan", {}) or {}
    res = d.get("results") or {}
    flags = scan.get("flags", {}) or {}
    detail = res.get("classify_detail") or {}
    err = d.get("error")

    model = scan.get("model") or os.path.basename(path)
    expected = res.get("expected_label") or scan.get("expected_label")
    is_err = bool(err) or not d.get("results")

    svd = _num(res.get("svd_alignment_global"))
    band = _num(res.get("band_alignment"))
    severance = max([v for v in (svd, band) if v is not None], default=None)
    pred = "ERROR" if is_err else res.get("label", "?")
    match = "" if not expected or is_err else ("yes" if expected == pred else "no")

    return {
        "model": model,
        "status": "ERROR" if is_err else "OK",
        "expected": expected,
        "predicted": pred,
        "match": match,
        "confidence": _num(res.get("confidence")),
        "severance": severance,
        "svd_alignment_global": svd,
        "band_alignment": band,
        "touched_band": _band(res.get("touched_band")),
        "svd_pairwise_cos": _num(res.get("svd_pairwise_cos")),
        "max_cohens_d": _num(res.get("max_cohens_d")),
        "mean_cohens_d": _num(res.get("mean_cohens_d")),
        "refusal": _num(res.get("behavioral_refusal_rate")),
        "axis_alive": detail.get("axis_alive"),
        "write_severed": detail.get("write_severed"),
        "quantization": scan.get("quantization"),
        "model_type": scan.get("model_type"),
        "n_layers": scan.get("n_layers"),
        "hidden_size": scan.get("hidden_size"),
        "lang": flags.get("lang"),
        "n_probes": flags.get("n_probes"),
        "timestamp": scan.get("timestamp"),
        "error": (err or "")[:300] if is_err else "",
    }


def load_campaign(paths) -> list[dict]:
    """Résout dossiers / globs -> liste de records triée (modèle)."""
    files: list[str] = []
    for p in paths:
        if os.path.isdir(p):
            files += glob.glob(os.path.join(p, "**", "*.json"), recursive=True)
        else:
            files += glob.glob(p, recursive=True)
    # un glob (ex. 'runs_out/2026*/') peut matcher des DOSSIERS -> les développer en JSON
    expanded: list[str] = []
    for f in files:
        if os.path.isdir(f):
            expanded += glob.glob(os.path.join(f, "**", "*.json"), recursive=True)
        elif f.endswith(".json") and os.path.isfile(f):
            expanded.append(f)
    recs = [_record(f) for f in sorted(set(expanded))]
    recs.sort(key=lambda r: (r["status"] != "OK", str(r["model"])))
    return recs


# --------------------------------------------------------------------------- #
# Résumé (accuracy + matrice de confusion)                                    #
# --------------------------------------------------------------------------- #
def summarize(recs: list[dict]) -> dict:
    ok = [r for r in recs if r["status"] == "OK"]
    labeled = [r for r in ok if r["expected"]]
    good = sum(1 for r in labeled if r["expected"] == r["predicted"])
    conf = defaultdict(Counter)
    for r in labeled:
        conf[r["expected"]][r["predicted"]] += 1
    cols = sorted({r["predicted"] for r in labeled} | set(conf))
    return {
        "n_total": len(recs),
        "n_ok": len(ok),
        "n_error": len(recs) - len(ok),
        "n_labeled": len(labeled),
        "n_good": good,
        "accuracy": (good / len(labeled)) if labeled else None,
        "pred_counts": Counter(r["predicted"] for r in ok),
        "confusion": conf,
        "confusion_cols": cols,
    }


# --------------------------------------------------------------------------- #
# Sorties                                                                      #
# --------------------------------------------------------------------------- #
CSV_COLUMNS = [
    "model", "status", "expected", "predicted", "match", "confidence",
    "severance", "svd_alignment_global", "band_alignment", "touched_band",
    "svd_pairwise_cos", "max_cohens_d", "mean_cohens_d", "refusal",
    "axis_alive", "write_severed", "quantization", "model_type",
    "n_layers", "hidden_size", "lang", "n_probes", "timestamp", "error",
]


def write_csv(recs: list[dict], path: str) -> str:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in recs:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in CSV_COLUMNS})
    return path


def write_figure(recs: list[dict], path: str, title: str) -> str | None:
    try:
        from modelscanner.viz import campaign_matrix
    except Exception as e:
        print(f"  [warn] figure ignorée (import viz/matplotlib KO): {e}")
        return None
    campaign_matrix(recs, path=path, title=title)
    return path


def _badge(label: str) -> str:
    color = _LABEL_COLOR.get(label, "#969696")
    return (f'<span class="badge" style="background:{color}">'
            f'{html.escape(str(label))}</span>')


def _cell(v) -> str:
    return "" if v in (None, "") else html.escape(str(v))


def write_html(recs, summ, fig_path, path, *, name, meta) -> str:
    img_tag = ""
    if fig_path and os.path.exists(fig_path):
        b64 = base64.b64encode(open(fig_path, "rb").read()).decode("ascii")
        img_tag = (f'<img alt="matrice de provenance" '
                   f'src="data:image/png;base64,{b64}">')

    # --- en-tête méta ---
    acc = summ["accuracy"]
    acc_txt = "—" if acc is None else f"{summ['n_good']}/{summ['n_labeled']} = {acc:.0%}"
    meta_rows = "".join(
        f"<tr><th>{html.escape(k)}</th><td>{_cell(v)}</td></tr>"
        for k, v in meta.items() if v not in (None, "")
    )
    counts = "  ·  ".join(f"{_badge(k)} {v}" for k, v in summ["pred_counts"].most_common())

    # --- matrice de confusion ---
    cm = ""
    cols = summ["confusion_cols"]
    if cols:
        head = "".join(f"<th>{_badge(c)}</th>" for c in cols)
        body = ""
        for exp in sorted(summ["confusion"]):
            cells = ""
            for c in cols:
                n = summ["confusion"][exp][c]
                hit = exp == c
                cells += (f'<td class="{"diag" if hit else ""}">'
                          f'{n if n else "·"}</td>')
            body += f"<tr><th>{_badge(exp)}</th>{cells}</tr>"
        cm = (f'<h2>Matrice de confusion <small>(ligne = attendu, '
              f'colonne = prédit)</small></h2><table class="confusion">'
              f'<tr><th></th>{head}</tr>{body}</table>')

    # --- tableau détaillé ---
    headers = ["modèle", "type", "statut", "attendu", "prédit", "✓", "conf.",
               "sévérance", "SVD glob.", "bande", "couches", "refus",
               "axe vivant", "poids sect.", "quant.", "couches#"]
    thead = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    trows = ""
    for r in recs:
        mark = {"yes": "✓", "no": "✗", "": ""}[r["match"]]
        mark_cls = {"yes": "ok", "no": "bad", "": ""}[r["match"]]
        cls = "err" if r["status"] == "ERROR" else ""
        trows += (
            f'<tr class="{cls}">'
            f'<td class="model" title="{html.escape(str(r["model"]))}">'
            f'{html.escape(str(r["model"]))}</td>'
            f'<td>{_cell(r["model_type"])}</td>'
            f'<td>{_cell(r["status"])}</td>'
            f'<td>{_badge(r["expected"]) if r["expected"] else ""}</td>'
            f'<td>{_badge(r["predicted"])}</td>'
            f'<td class="{mark_cls}">{mark}</td>'
            f'<td>{_cell(r["confidence"])}</td>'
            f'<td>{_cell(r["severance"])}</td>'
            f'<td>{_cell(r["svd_alignment_global"])}</td>'
            f'<td>{_cell(r["band_alignment"])}</td>'
            f'<td>{_cell(r["touched_band"])}</td>'
            f'<td>{_cell(r["refusal"])}</td>'
            f'<td>{_cell(r["axis_alive"])}</td>'
            f'<td>{_cell(r["write_severed"])}</td>'
            f'<td>{_cell(r["quantization"])}</td>'
            f'<td>{_cell(r["n_layers"])}</td>'
            f'</tr>'
        )

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    name_e = html.escape(name)
    head_meta = (f'{name_e}<br>{summ["n_total"]} modèles · {summ["n_ok"]} OK · '
                 f'{summ["n_error"]} err<br>{now}')

    doc = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Campagne — {name_e}</title>
<style>
{_CSS}
</style>
{_THEME_INIT}
</head>
<body>
  <header class="brand"><div class="wrap">
    <div class="brandgroup">
      {_JORAK_MARK}
      <div class="namewrap">
        <div class="word"><span class="wf">ORAK</span></div>
        <div class="tagline">Rapport de campagne multi-modèles <span class="sep">//</span> Model Scanner</div>
      </div>
    </div>
    <div class="meta">{head_meta}</div>
    {_THEME_TOGGLE}
  </div></header>

  <div class="wrap">
    <h1 class="title">Rapport de campagne — {name_e}</h1>
    <div class="sub">Généré le {now} · {summ['n_total']} modèles ({summ['n_ok']} OK · {summ['n_error']} erreurs)</div>

    <div class="grid">
      <div class="card"><div class="lbl">Accuracy</div><div class="kpi">{acc_txt}</div></div>
      <div class="card"><div class="lbl">Répartition prédite</div>
          <div style="margin-top:8px">{counts or '—'}</div></div>
      <div class="card"><table class="meta">{meta_rows}</table></div>
    </div>

    <h2>Matrice de provenance <small>(4 buckets · sévérance des poids × refus)</small></h2>
    {img_tag or '<p><em>figure indisponible</em></p>'}

    {cm}

    <h2>Détail par modèle</h2>
    <div class="tablescroll"><table><thead><tr>{thead}</tr></thead><tbody>{trows}</tbody></table></div>

    <footer>
      Légende — <b>sévérance</b> = max(SVD u_min global, alignement de bande) ;
      poids sectionnés au-dessus de 0,5. Anneau rouge sur la figure = prédiction ≠ attendu.
      Losange = comportemental absent (placé sur la médiane des refus).
    </footer>
  </div>
  <script>{_TOGGLE_JS}</script>
</body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
    return path


def _s3_upload(files, prefix: str) -> list[str]:
    """Pousse les fichiers (csv/html/png) sous `prefix` (s3://...). aws CLI requis.

    Même mécanisme que run_scan.py (subprocess `aws s3 cp`). Sans aws CLI -> no-op
    avec avertissement (les fichiers restent en local de toute façon)."""
    if not shutil.which("aws"):
        ui.bullet("warn", "aws CLI absent → pas d'upload S3 (fichiers gardés en local).")
        return []
    pushed = []
    for f in files:
        if not f or not os.path.exists(f):
            continue
        dst = prefix.rstrip("/") + "/" + os.path.basename(f)
        r = subprocess.run(["aws", "s3", "cp", f, dst], capture_output=True, text=True)
        if r.returncode == 0:
            pushed.append(dst)
        else:
            ui.bullet("warn", f"upload S3 KO {os.path.basename(f)} : {(r.stderr or '').strip()[:200]}")
    return pushed


# --------------------------------------------------------------------------- #
# Orchestration (réutilisable depuis run_scan.py)                             #
# --------------------------------------------------------------------------- #
def generate(paths, *, out_dir=None, name=None, make_fig=True, s3_prefix=None):
    """Construit CSV + HTML + matrice 4-buckets pour une campagne, optionnellement
    poussés sur S3. Renvoie un dict de résultats, ou ``None`` si aucun JSON."""
    recs = load_campaign(paths)
    if not recs:
        return None

    first = paths[0]
    base = first.rstrip("/") if os.path.isdir(first) else os.path.dirname(first)
    if any(c in base for c in "*?[]"):        # base issue d'un glob -> pas un vrai dossier
        base = "."
    out_dir = out_dir or base or "."
    os.makedirs(out_dir, exist_ok=True)
    name = name or (os.path.basename(base) or "campagne")

    summ = summarize(recs)
    # langue/sondes = config DU RUN (homogène sur une campagne) -> 1er record OK.
    # type modèle & quantif sont PAR MODÈLE et peuvent varier -> on les ventile
    # sur toute la campagne (cf. _distinct_summary), jamais un seul représentant.
    src = next((r for r in recs if r["status"] == "OK"), recs[0])
    meta = {
        "run": name, "modèles": summ["n_total"],
        "OK / erreurs": f"{summ['n_ok']} / {summ['n_error']}",
        "types modèles": _distinct_summary(recs, "model_type"),
        "quantifs": _distinct_summary(recs, "quantization"),
        "langue sondes": src.get("lang"), "sondes/classe": src.get("n_probes"),
        "comportemental": "oui" if any(r["refusal"] is not None for r in recs) else "non",
    }

    csv_path = write_csv(recs, os.path.join(out_dir, "campaign.csv"))
    fig_path = None
    if make_fig:
        fig_path = write_figure(recs, os.path.join(out_dir, "provenance_matrix.png"),
                                title=f"Matrice de provenance — {name}")
    html_path = write_html(recs, summ, fig_path,
                           os.path.join(out_dir, "campaign.html"),
                           name=name, meta=meta)

    pushed = _s3_upload([csv_path, fig_path, html_path], s3_prefix) if s3_prefix else []
    return {"recs": recs, "summ": summ, "name": name, "out_dir": out_dir,
            "csv": csv_path, "fig": fig_path, "html": html_path, "s3": pushed}


# --------------------------------------------------------------------------- #
# main                                                                         #
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Rapport de campagne (CSV + HTML + matrice 4-buckets).")
    ap.add_argument("paths", nargs="+", help="dossier(s) de run ou glob(s) de JSON.")
    ap.add_argument("--out", default=None, help="dossier de sortie (défaut : le 1er dossier de run).")
    ap.add_argument("--name", default=None, help="nom de la campagne (défaut : nom du dossier de run).")
    ap.add_argument("--no-fig", action="store_true", help="ne pas générer la figure PNG.")
    ap.add_argument("--s3", default=None, metavar="s3://…",
                    help="préfixe S3 où pousser csv+html+png (comme les JSON ; aws CLI requis).")
    args = ap.parse_args(argv)

    res = generate(args.paths, out_dir=args.out, name=args.name,
                   make_fig=not args.no_fig, s3_prefix=args.s3)
    if res is None:
        print("Aucun JSON trouvé dans :", args.paths)
        return 1

    summ = res["summ"]
    ui.banner("CAMPAGNE", f"rapport « {res['name']} » · {summ['n_ok']} OK / {summ['n_error']} erreurs")
    if summ["accuracy"] is not None:
        ui.kv("accuracy", f"{summ['n_good']}/{summ['n_labeled']} = {summ['accuracy']:.0%}")
    ui.kv("CSV", res["csv"])
    if res["fig"]:
        ui.kv("PNG", res["fig"])
    ui.kv("HTML", res["html"])
    if res["s3"]:
        ui.bullet("s3", "S3   " + ui.s3_uri(res["s3"][0].rsplit("/", 1)[0] + "/")
                  + "  (csv + html + png)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runner — orchestrateur de scans piloté par un YAML.

Décisions de design (grill) :
  - 1 SOUS-PROCESS par modèle (anti-OOM : l'OS libère toute la mémoire à chaque fin).
  - modèles = chemins locaux (sous `models_dir`) OU ids HF si pas trouvés sur disque.
  - résultats = 1 JSON / modèle, poussé sur S3 « au fil de l'eau » (si `output_s3`).
  - échec d'un modèle => JSON d'erreur + on continue (skip + log).
  - reprise idempotente : saute un modèle dont le résultat existe déjà (--force pour refaire).
  - `expected_label` (optionnel) est écrit DANS le JSON (comparaison visuelle).
  - mode AWS (`download`/`purge` dans le YAML) : même cycle que `scan --s3` —
    télécharge chaque modèle absent du cache (procédure box) puis le purge après scan.

Usage :
    python experiments/run_scan.py experiments/runs/campaign_cpu.yaml [options]

Options pratiques :
    --dry-run            afficher le plan (dl/scan/purge/skip) sans rien exécuter.
    --only MOTIF [...]   ne garder que les modèles dont le path/nom contient un motif.
    --limit N            ne scanner que les N premiers modèles (après --only).
    --force              re-scanner même si le résultat existe déjà.
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import time

import yaml

# Procédure environnement cloisonné (réutilisée du chemin `scan --s3`) : récupérer
# un modèle absent du cache (proxy de paquets privé + CA interne), puis le purger.
from modelscanner import ui
from modelscanner.hf_download import (
    ensure_model_downloaded,
    is_model_cached,
    purge_model_cache,
)

PY = sys.executable  # le python courant (env conda) -> même interpréteur pour les sous-process


def _sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def _aws():
    return shutil.which("aws") is not None


def _s3_exists(uri):
    r = _sh(f"aws s3 ls {uri}")
    return r.returncode == 0 and r.stdout.strip() != ""


def _safe_name(path):
    return path.rstrip("/").replace("/", "__").strip("_") or "model"


def _free_gb(path="."):
    """Espace disque libre (Go) sur le volume de `path` — None si indéterminable.

    Remonte au parent existant le plus proche (le cache HF peut ne pas encore
    exister au préflight) : `disk_usage` exige un chemin présent."""
    p = os.path.abspath(path)
    while p and not os.path.exists(p):
        parent = os.path.dirname(p)
        if parent == p:
            break
        p = parent
    try:
        return shutil.disk_usage(p or "/").free / 1e9
    except Exception:
        return None


def _hf_cache_dir():
    """Répertoire du cache HF (là où atterrissent les téléchargements `hf download`)."""
    base = os.environ.get("HF_HOME") or os.path.join(
        os.path.expanduser("~"), ".cache", "huggingface")
    return os.path.join(base, "hub")


def _write_error_json(local_json, ref, expected, kind, hint, stderr_tail,
                      error="scan failed"):
    """Écrit le JSON d'erreur standard d'un modèle (échec de scan OU préflight)."""
    json.dump(
        {"scan": {"model": ref, "expected_label": expected,
                  "timestamp": datetime.datetime.now().isoformat(timespec="seconds")},
         "error": error, "error_kind": kind, "error_hint": hint,
         "stderr_tail": stderr_tail},
        open(local_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def _match(path, name, tokens):
    """True si un des `tokens` (insensible à la casse) apparaît dans le path/nom."""
    if not tokens:
        return True
    hay = f"{path} {name}".lower()
    return any(t.lower() in hay for t in tokens)


def _fmt_dur(secs):
    """Durée lisible : 42s, 3m12, 1h04."""
    secs = int(round(secs))
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m{secs % 60:02d}"
    return f"{secs // 3600}h{(secs % 3600) // 60:02d}"


def _classify_error(stderr):
    """Catégorise un échec de scan depuis le stderr -> (kind, hint).

    Rend les échecs de campagne ACTIONNABLES : au lieu d'un opaque « scan failed
    (exit 1) », on distingue la cause racine (archi non supportée, repo gated,
    format non chargeable, OOM, download). `kind` est écrit dans le JSON d'erreur
    et affiché au récap ; `hint` est une remédiation courte."""
    s = (stderr or "").lower()
    # DISQUE PLEIN (ENOSPC) — cause racine n°1 des campagnes 8B (chaque bf16 pèse
    # ~16 Go). À TESTER EN PREMIER : un ENOSPC survient pendant `http_get`, donc
    # la trace ressemble à un problème réseau et serait sinon étiquetée « download »
    # -> mauvaise remédiation (on vérifie proxy/token au lieu de libérer le disque).
    if any(k in s for k in ("no space left on device", "errno 28",
                            "disk quota exceeded", "quota exceeded")):
        return ("disk_full",
                "DISQUE PLEIN (ENOSPC) — libérer le cache HF / agrandir le volume "
                "(PAS un souci réseau/proxy/token)")
    # Téléchargement PARTIEL : shard safetensors manquant au chargement — séquelle
    # typique d'un ENOSPC antérieur qui a laissé un snapshot incomplet dans le cache.
    # (On garde ce test spécifique : « no such file or directory » + safetensors,
    # pour ne PAS empiéter sur `unsupported_format` = « repo sans aucun poids ».)
    if ("no such file or directory" in s
            and (".safetensors" in s or "model-000" in s or "safe_open" in s)):
        return ("incomplete_download",
                "shard safetensors manquant (cache partiel) — purger CE repo du cache "
                "puis re-télécharger (souvent séquelle d'un disque plein)")
    # nom de l'exception dédiée (arch_adapter) : signal robuste, présent dans le
    # traceback. (On ne matche PAS le simple « non supporté » : trop générique,
    # il capturait aussi nos messages GGUF/format « format non supporté ».)
    if "unsupportedarchitecture" in s:
        return ("unsupported_arch", "famille inconnue du registre — ajouter / autodetect")
    # model_type présent mais inconnu de CETTE version de transformers (ex. mistral3
    # / Ministral-3 sur une box pas à jour) : casse à AutoConfig, AVANT notre code.
    # Sujet de PÉRENNITÉ : le scanner doit suivre les nouvelles familles -> upgrade.
    # `transformersoutdated` = nom de notre exception dédiée (loaders/errors.py).
    if ("transformersoutdated" in s
            or "does not recognize this architecture" in s or "out of date" in s
            or ("has model type" in s and "does not" in s)):
        return ("transformers_outdated",
                "model_type trop récent pour transformers de la box — METTRE À JOUR transformers")
    if any(k in s for k in ("gatedrepo", "awaiting a review", "access to model",
                            "you must be authenticated", "must be authenticated",
                            "401 client error", "403 client error", "is restricted",
                            "must agree", "cannot access gated")):
        return ("gated", "repo gated — accepter la licence sur HF + export HF_TOKEN")
    # dépôt GGUF-only (non chargeable en safetensors) : `gguf` n'apparaît dans le
    # stderr QUE via notre garde-fou (UnsupportedFormat) -> détection sans faux positif.
    if "gguf" in s:
        return ("gguf_only",
                "dépôt GGUF-only (pas de safetensors/bin) — format non supporté, exclure ce modèle")
    # config.json sans clé model_type (repos non standard, ex. huihui-ai) : le loader
    # tente de l'inférer depuis `architectures` ; si on voit encore cette erreur,
    # l'inférence a échoué (architectures absentes ou exotiques).
    if any(k in s for k in ("should have a `model_type`", "should have a model_type",
                            "unrecognized model in")):
        return ("config_no_model_type",
                "config.json sans `model_type` et inférence échouée — ajouter model_type au config.json")
    if any(k in s for k in ("does not appear to have a file named", "no file named",
                            "does not have a file", "no loadable weights")):
        return ("unsupported_format",
                "pas de poids safetensors/bin chargeables (repo gated/token ou incomplet)")
    if "out of memory" in s or "outofmemoryerror" in s or "cuda error" in s:
        return ("oom", "VRAM insuffisante — couper activations / baisser probe_subset / GPU propre")
    if any(k in s for k in ("connectionerror", "timed out", "timeout",
                            "max retries", "téléchargement ko", "telechargement ko")):
        return ("download", "téléchargement KO — vérifier réseau/proxy/token")
    return ("scan_failed", "voir stderr_tail")


def main():
    ap = argparse.ArgumentParser(description="Runner de scans (YAML).")
    ap.add_argument("config", help="fichier YAML de configuration du run")
    ap.add_argument("--force", action="store_true", help="re-scanner même si le résultat existe")
    ap.add_argument("--only", nargs="+", metavar="MOTIF", default=None,
                    help="ne garder que les modèles dont le path/nom contient un de ces motifs.")
    ap.add_argument("--limit", type=int, default=None, metavar="N",
                    help="ne scanner que les N premiers modèles (après --only).")
    ap.add_argument("--dry-run", action="store_true",
                    help="afficher le plan (résolution + dl/scan/purge/skip) sans rien exécuter.")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config, encoding="utf-8")) or {}
    device = cfg.get("device", "auto")
    plans = cfg.get("plans", {}) or {}
    behavioral = plans.get("behavioral", True)
    activations = plans.get("activations", False)
    # cibles JORAK de la signature poids : "o_proj" (défaut) ou "o_proj,down_proj"
    # pour OU-er la sévérance des deux writers résiduels (capte une ablation MLP).
    # Accepte une liste YAML ou une chaîne séparée par des virgules.
    weight_targets = plans.get("weight_targets") or cfg.get("weight_targets")
    if isinstance(weight_targets, (list, tuple)):
        weight_targets = ",".join(str(t) for t in weight_targets)
    weight_targets = (weight_targets or "").strip()
    multilingual = bool(cfg.get("multilingual", False))
    profile = bool(cfg.get("profile", False))
    probe_subset = cfg.get("probe_subset")
    # longueur max des réponses générées (behavioral). None -> défaut CLI (64).
    # Baisser (ex. 24) pour accélérer une grosse campagne ; monter pour des réponses
    # plus complètes dans le rapport.
    max_new_tokens = cfg.get("max_new_tokens")
    lang = cfg.get("lang", "en")
    models_dir = cfg.get("models_dir", "") or ""
    out_s3 = (cfg.get("output_s3") or "").rstrip("/")
    out_dir = cfg.get("output_dir", "runs_out")
    run_id = str(cfg.get("run_id") or datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    # AWS : même méthode que `scan --s3`. `download` = récupérer chaque modèle
    # absent du cache via la procédure box (CA interne + secrets + `hf download`)
    # avant de le scanner. `purge` (défaut = download) = vider du cache HF, après
    # le scan, UNIQUEMENT les modèles que CE run a téléchargés — pour scanner une
    # grande matrice (10×1.5B / 4×7B) sans saturer le disque de la box.
    download = bool(cfg.get("download", False))
    purge = bool(cfg.get("purge", download))
    # Garde-disque campagne (anti-ENOSPC). `min_free_gb` = espace libre exigé sur
    # le cache HF AVANT de télécharger un modèle (bf16 8B ~16 Go + pic temporaire).
    # `max_consec_disk_fail` = disjoncteur : après N échecs « disque plein »
    # consécutifs, on ARRÊTE la campagne au lieu de brûler toute la matrice contre
    # le même mur (cf. run 2026-07-01 : 3 ENOSPC d'affilée). Reprise idempotente.
    min_free_gb = float(cfg.get("min_free_gb", 18))
    max_consec_disk_fail = int(cfg.get("max_consec_disk_fail", 2))

    # normalisation + filtrage pratique : --only (motif) puis --limit (N premiers).
    models = [{"path": m} if isinstance(m, str) else m for m in (cfg.get("models", []) or [])]
    n_total = len(models)
    if args.only:
        models = [m for m in models if _match(m["path"], _safe_name(m["path"]), args.only)]
    if args.limit is not None:
        models = models[:args.limit]

    local_run = os.path.join(out_dir, run_id)
    if not args.dry_run:
        os.makedirs(local_run, exist_ok=True)
    use_s3 = bool(out_s3) and _aws()

    plan_str = "poids" + (f"[{weight_targets}]" if weight_targets else "")
    plan_str += (" +behav" if behavioral else "") + (" +activ" if activations else "")
    plan_str += (" +mlt" if multilingual else "") + (" +prof" if profile else "")
    sel = f"{len(models)}/{n_total}" if len(models) != n_total else f"{n_total}"
    head = "PLAN (dry-run)" if args.dry_run else "RUN"
    ui.banner("CAMPAGNE", f"{head} · {run_id} · {sel} modèles · device={device}")
    ui.kv("plans", plan_str)
    ui.kv("S3", ui.s3_uri(out_s3) if use_s3 else "off")
    ui.kv("AWS", f"download={'on' if download else 'off'} · purge={'on' if purge else 'off'}")
    free0 = _free_gb(out_dir if os.path.isdir(out_dir) else ".")
    if (download or purge) and free0 is not None:
        ui.kv("disque", f"{free0:.1f} Go libres")
    if not models:
        ui.bullet("warn", "aucun modèle à scanner — vérifier --only / la liste `models`")
        return

    # ----------------------------------------------------------------- DRY-RUN
    if args.dry_run:
        for m in models:
            path = m["path"]
            name = _safe_name(path)
            local_path = models_dir and os.path.isdir(os.path.join(models_dir, path))
            ref = os.path.join(models_dir, path) if local_path else path
            kind = "local(models_dir)" if local_path else ("local" if os.path.isdir(path) else "HF")
            local_json = os.path.join(local_run, f"{name}.json")
            s3_json = f"{out_s3}/{run_id}/{name}.json" if use_s3 else None
            would_skip = (not args.force) and (
                os.path.exists(local_json) or (s3_json and _s3_exists(s3_json)))
            if would_skip:
                acts = "SKIP (déjà fait)"
                kind_bullet = "skip"
            else:
                cached = is_model_cached(ref) if download else True
                steps = []
                if download and not cached:
                    steps.append("download")
                steps.append("scan")
                if purge and download and not cached:
                    steps.append("purge")
                acts = " + ".join(steps)
                kind_bullet = "info"
            ui.bullet(kind_bullet, f"{name:42s} ({kind:18s}) → {acts}")
        ui.bullet("skip", "dry-run : rien n'a été téléchargé, scanné ni purgé")
        return

    # -------------------------------------------------------------------- RUN
    ok = fail = skip = 0
    consec_disk_fail = 0  # disjoncteur : échecs « disque plein » consécutifs
    summary = []
    t_run = time.time()
    for i, m in enumerate(models, 1):
        path = m["path"]
        expected = m.get("expected_label")
        name = _safe_name(path)
        # résolution : dossier local sous models_dir > dossier absolu > id HF
        ref = path
        if models_dir and os.path.isdir(os.path.join(models_dir, path)):
            ref = os.path.join(models_dir, path)
        local_json = os.path.join(local_run, f"{name}.json")
        s3_json = f"{out_s3}/{run_id}/{name}.json" if use_s3 else None

        # --- reprise idempotente ---
        if not args.force and (os.path.exists(local_json) or (s3_json and _s3_exists(s3_json))):
            ui.bullet("skip", f"({i}/{len(models)}) {name} (déjà fait)")
            skip += 1
            summary.append((name, expected or "-", "(skipped)", 0.0))
            continue

        # --- AWS : récupérer le modèle absent du cache (procédure box) ---
        # On mémorise s'il était déjà disponible hors-ligne pour ne purger en fin
        # de scan QUE ce que CE run a téléchargé (modèle local sous models_dir ou
        # cache partagé vLLM : `is_model_cached`/`purge_model_cache` n'y touchent pas).
        cached0 = True
        if download:
            cached0 = is_model_cached(ref)
            # --- préflight disque : ne PAS lancer un download voué à l'ENOSPC ---
            if not cached0:
                free = _free_gb(_hf_cache_dir())
                if free is not None and free < min_free_gb:
                    consec_disk_fail += 1
                    _write_error_json(
                        local_json, ref, expected, "disk_full",
                        f"disque plein avant download ({free:.1f} Go libres "
                        f"< {min_free_gb:.0f} Go requis) — libérer le cache HF / "
                        f"agrandir le volume",
                        f"préflight : {free:.1f} Go libres sur {_hf_cache_dir()}",
                        error="préflight KO : disque plein (aucun scan lancé)")
                    fail += 1
                    ui.bullet("fail", f"{name} [disk_full] {free:.1f} Go < "
                              f"{min_free_gb:.0f} Go — SKIP (préflight)")
                    summary.append((name, expected or "-", "ERROR", 0.0))
                    if use_s3:
                        _sh(f"aws s3 cp {local_json} {s3_json}")
                    if consec_disk_fail >= max_consec_disk_fail:
                        ui.bullet("fail", f"DISJONCTEUR : {consec_disk_fail} échecs "
                                  f"disque consécutifs — campagne INTERROMPUE. Libère "
                                  f"de l'espace puis relance (reprise idempotente).")
                        break
                    continue
            ensure_model_downloaded(ref)

        # --- commande CLI (sous-process => mémoire libérée à la fin) ---
        cmd = [PY, "-m", "modelscanner.cli", "scan", ref, "--device", device, "--log", local_json]
        if behavioral:
            cmd.append("--behavioral")
        if not activations:
            cmd.append("--no-activations")
        if multilingual:
            cmd.append("--multilingual")
        if profile:
            cmd.append("--profile")
        if weight_targets:
            cmd += ["--weight-targets", weight_targets]
        if probe_subset:
            cmd += ["--probe-subset", str(probe_subset)]
        if max_new_tokens:
            cmd += ["--max-new-tokens", str(max_new_tokens)]
        if lang and lang != "en":
            cmd += ["--lang", lang]
        if expected:
            cmd += ["--expected-label", expected]

        ui.bullet("run", f"({i}/{len(models)}) {name} …")
        t0 = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True)
        dt = time.time() - t0
        if r.returncode != 0 or not os.path.exists(local_json):
            # certains échecs (ex. process tué, exit 2) laissent stderr VIDE : on
            # bascule sur stdout pour ne pas produire un `stderr_tail` inexploitable.
            diag = r.stderr if (r.stderr or "").strip() else (r.stdout or "")
            kind, hint = _classify_error(diag)
            _write_error_json(local_json, ref, expected, kind, hint,
                              (diag or "")[-800:],
                              error=f"scan failed (exit {r.returncode})")
            fail += 1
            pred = "ERROR"
            # un échec disque (plein ou snapshot partiel) arme le disjoncteur ;
            # tout autre échec (arch, gated, oom…) est isolé -> on réinitialise.
            consec_disk_fail = consec_disk_fail + 1 if kind in (
                "disk_full", "incomplete_download") else 0
            ui.bullet("fail", f"{name} [{kind}] {hint}  (exit {r.returncode}, {_fmt_dur(dt)})")
        else:
            ok += 1
            consec_disk_fail = 0
            try:
                pred = json.load(open(local_json)).get("results", {}).get("label", "?")
            except Exception:
                pred = "?"
            mark = "" if not expected else ("  ✓" if pred == expected else "  ✗")
            ui.bullet("ok", f"{name} → {pred}{mark}  ({_fmt_dur(dt)})")

        if use_s3:
            _sh(f"aws s3 cp {local_json} {s3_json}")
        summary.append((name, expected or "-", pred, dt))

        # --- nettoyage disque : purger du cache HF ce que CE run a téléchargé ---
        # (le sous-process a rendu la mémoire ; on libère maintenant l'espace
        # disque avant le modèle suivant). No-op si le modèle était déjà là.
        if purge and not cached0:
            purge_model_cache(ref)

        # --- disjoncteur disque : arrêter net une campagne qui tape le même mur ---
        # (placé APRÈS la purge : on a d'abord tenté de reprendre l'espace du
        # snapshot partiel avant de décider d'abandonner.)
        if consec_disk_fail >= max_consec_disk_fail:
            ui.bullet("fail", f"DISJONCTEUR : {consec_disk_fail} échecs disque "
                      f"consécutifs — campagne INTERROMPUE. Libère de l'espace "
                      f"(cache HF / volume) puis relance : reprise idempotente.")
            break

    # --- récap ---
    elapsed = time.time() - t_run
    ui.rule(f"FINI · {ok} OK · {fail} échecs · {skip} sautés · {_fmt_dur(elapsed)}")
    print("  " + ui.style(f"{'modèle':43s} {'attendu':24s} {'prédit':22s} durée", ui.DIM))
    for name, exp, pred, secs in summary:
        mark = "" if exp == "-" or pred in ("(skipped)", "ERROR") else ("  ✓" if exp == pred else "  ✗")
        dur = "" if not secs else _fmt_dur(secs)
        print(f"  {name:43s} {exp:24s} {str(pred)+mark:22s} {dur}")
    free1 = _free_gb(out_dir if os.path.isdir(out_dir) else ".")
    if (download or purge) and free1 is not None:
        delta = "" if free0 is None else f" ({free1 - free0:+.1f} Go)"
        ui.kv("disque", f"{free1:.1f} Go libres{delta}")
    ui.kv("JSON local", f"{local_run}/")
    if use_s3:
        ui.kv("JSON S3", ui.s3_uri(f"{out_s3}/{run_id}/"))
    ui.kv("agréger", f"python experiments/aggregate.py {local_run}")

    # --- rapport de campagne (CSV + HTML + matrice 4-buckets) ---
    # Généré ici puis poussé sur S3 vers le MÊME préfixe que les JSON (so AWS = tout au même endroit).
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import campaign_report

        rep = campaign_report.generate(
            [local_run], name=run_id,
            s3_prefix=(f"{out_s3}/{run_id}" if use_s3 else None),
        )
        if rep:
            ui.kv("rapport", f"{rep['html']}  (+ campaign.csv, provenance_matrix.png)")
            if rep["s3"]:
                ui.bullet("s3", "rapport S3  " + ui.s3_uri(f"{out_s3}/{run_id}/")
                          + "  (csv + html + png)")
            elif use_s3:
                ui.bullet("warn", "rapport S3 : upload KO — voir avertissements ci-dessus")
    except Exception as e:  # un rapport raté ne doit jamais faire échouer le run
        ui.bullet("warn", f"rapport non généré ({e}) — manuel : "
                  f"python experiments/campaign_report.py {local_run}")


if __name__ == "__main__":
    main()

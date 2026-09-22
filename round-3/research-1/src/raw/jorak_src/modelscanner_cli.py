"""CLI `modelscanner`. [J10]

Usage cible : `modelscanner scan <model_id>` -> label + confidence + figures.
"""
from __future__ import annotations

import argparse

from modelscanner import ui


def main(argv=None) -> int:
    # --- bypass SSL proxy MITM pour les downloads HF (activé seulement si HF_DISABLE_SSL=1) ---
    # À exécuter AVANT tout from_pretrained. Safe par défaut : sans la var, vérif SSL normale.
    import os

    if os.environ.get("HF_DISABLE_SSL") == "1":
        os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"   # couper le downloader Rust (ignore verify=False)
        import requests
        import urllib3
        from huggingface_hub import configure_http_backend

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        def _insecure_session() -> "requests.Session":
            s = requests.Session()
            s.verify = False                            # désactive la vérif SSL
            return s

        configure_http_backend(backend_factory=_insecure_session)
        print("[WARN] HF_DISABLE_SSL=1: SSL verification disabled (MITM possible).")
    # --- fin bypass SSL ---

    parser = argparse.ArgumentParser(prog="modelscanner")
    sub = parser.add_subparsers(dest="cmd")

    p_scan = sub.add_parser("scan", help="Scan a model -> provenance.")
    p_scan.add_argument("model", help="HF id or local path.")
    p_scan.add_argument("--behavioral", action="store_true",
                        help="enable the behavioral plan (separates censored/fine-tuned).")
    p_scan.add_argument("--probe-subset", type=int, default=None,
                        help="limit the number of probes per class (speed).")
    p_scan.add_argument("--max-new-tokens", type=int, default=64, metavar="N",
                        help="max length of generated responses (behavioral plan). "
                             "Default 64: enough to show a REAL response in the "
                             "report without truncating it. Lower it (e.g. 24) to speed up the campaign.")
    p_scan.add_argument("--device", default="auto", help="auto | cuda | cpu.")
    p_scan.add_argument("--lang", default="en", help="probe language (en, zh, fr, de, es, it).")
    p_scan.add_argument("--log", default=None,
                        help="save the JSON trace (flags + stats + prompt Q/A).")
    p_scan.add_argument("--report", nargs="?", const=".", default=None, metavar="DIR",
                        help="JORAK bundle (pro HTML + prompts CSV + summary CSV + JSON + heatmap) "
                             "in <DIR>/<model>_jorak_<date>/ (default DIR = current). "
                             "Enables the behavioral plan to capture prompt responses.")
    p_scan.add_argument("--s3", nargs="?", const="", default=None, metavar="DEST",
                        help="push the bundle to S3 THEN delete the local folder. "
                             "DEST optional: empty -> s3://your-bucket/results/Jorak ; a bucket "
                             "('my-bucket') or an exact prefix ('s3://my-bucket/x') "
                             "overrides it (also via $MODELSCANNER_S3_BUCKET). If the model is "
                             "missing from the HF cache, it is downloaded first (AWS box procedure). "
                             "Implies --report. See --keep-local.")
    p_scan.add_argument("--keep-local", action="store_true",
                        help="with --s3: KEEP the local bundle after upload (instead of "
                             "deleting it). Without --s3, no effect.")
    p_scan.add_argument("--profile", action="store_true",
                        help="profile the model (behavior, quality, hallucination, metadata) into the JSON.")
    p_scan.add_argument("--multilingual", action="store_true",
                        help="per-language refusal rate (EN-only asymmetry / partial ablation).")
    p_scan.add_argument("--no-activations", action="store_true",
                        help="disable the ACTIVATIONS plan (Cohen's d) — useful on tight GPU / large models.")
    p_scan.add_argument("--weight-targets", default=None, metavar="o_proj,down_proj",
                        help="JORAK targets of the weight signature, comma-separated. "
                             "Default o_proj only. 'o_proj,down_proj' ORs the severance of both "
                             "residual writers (catches an MLP-carried ablation). Doubles the SVD cost.")
    p_scan.add_argument("--subspace-k", type=int, default=None,
                        help="k of the multi-direction signature (default 4; cf. n_directions of modern OBLITERATUS-style ablations).")
    p_scan.add_argument("--expected-label", default=None,
                        help="expected provenance (censored/ablated/finetuned_decensored/...) written into the JSON.")

    sub.add_parser("archs", help="List supported families.")

    sub.add_parser("tui", help="Full-screen interactive wizard (curses): "
                              "builds and launches a scan or a campaign.")

    p_cmp = sub.add_parser("compare",
                           help="Overlay several --report bundles on a 4-bucket plane.")
    p_cmp.add_argument("paths", nargs="+",
                       help="bundles <model>_jorak_<date>/ , scan_log.json, or parent folder.")
    p_cmp.add_argument("--out", default=None, metavar="PNG",
                       help="output PNG (default jorak_compare_<date>.png ; a .csv is also written).")
    p_cmp.add_argument("--title", default=None, help="chart title.")
    p_cmp.add_argument("--lang", default="fr", choices=["fr", "en"], help="label language.")

    args = parser.parse_args(argv)

    if args.cmd == "archs":
        from modelscanner.loaders import supported_model_types

        print("\n".join(supported_model_types()))
        return 0

    if args.cmd == "tui":
        from modelscanner import tui

        return tui.main()

    if args.cmd == "compare":
        from modelscanner.report_single import compare_bundles

        res = compare_bundles(args.paths, out_png=args.out, title=args.title, lang=args.lang)
        if res is None:
            print("No scan_log.json found in:", args.paths)
            return 1
        print(f"== 4-bucket comparison: {res['n']} models ==")
        print("PNG:", res["png"])
        print("CSV:", res["csv"])
        return 0

    if args.cmd == "scan":
        from modelscanner.classifier import Thresholds, scan
        from modelscanner.loaders import (
            TransformersOutdated,
            UnsupportedArchitecture,
            UnsupportedFormat,
            load_model,
        )

        # --s3 implique --report (dossier courant par défaut).
        if args.s3 is not None and args.report is None:
            args.report = "."

        # bandeau JORAK — affiché pour les 2 surfaces « modèle » : rapport local
        # (aucun push S3) et upload S3. Le scan brut n'affiche pas le bandeau.
        if args.report is not None:
            if args.s3 is not None:
                ui.banner("S3", "JORAK report + S3 upload (s3://your-bucket/results/Jorak)")
            else:
                ui.banner("REPORT", "local JORAK bundle — no S3 push")

        # Destination S3 (--s3) : DEST vide -> s3://your-bucket/results/Jorak ; un bucket
        # ou un préfixe exact le surcharge. Purge locale par défaut, sauf --keep-local.
        s3_prefix = None
        delete_local = False
        model_was_cached = True   # par défaut : on ne purge rien du cache
        if args.s3 is not None:
            from modelscanner.hf_download import ensure_model_downloaded, is_model_cached
            from modelscanner.report_single import resolve_s3_dest

            dest = args.s3 or os.environ.get("MODELSCANNER_S3_BUCKET")
            s3_prefix = resolve_s3_dest(dest)     # bucket -> +/results/Jorak ; préfixe exact -> tel quel
            delete_local = not args.keep_local    # --keep-local garde le bundle local
            # sur la box : récupérer le modèle s'il n'est pas déjà dans le cache HF.
            # On retient s'il était déjà là pour ne purger en fin de run QUE ce
            # que --s3 a lui-même téléchargé (cache partagé vLLM : on n'y touche pas).
            model_was_cached = is_model_cached(args.model)
            ensure_model_downloaded(args.model)

        # signe de vie immédiat : le chargement d'un gros modèle est silencieux
        # et peut durer plusieurs minutes (ne pas le confondre avec un blocage).
        ui.bullet("run", f"loading model {args.model} (device={args.device}) …")
        # erreurs de chargement PRÉCISES : un message clair + un code de sortie
        # distinct par cause racine (le runner les re-catégorise depuis stderr).
        try:
            handle = load_model(args.model, device=args.device)
        except UnsupportedFormat as e:
            ui.bullet("fail", f"unsupported format: {e}")
            return 2
        except TransformersOutdated as e:
            ui.bullet("fail", f"transformers needs updating: {e}")
            return 3
        except UnsupportedArchitecture as e:
            ui.bullet("fail", f"unsupported architecture: {e}")
            return 4
        # --report a besoin des Q/R -> on force le plan comportemental (si modèle exécutable).
        want_behavioral = args.behavioral or (args.report is not None)
        # --report veut AUSSI toute la sonde multilingue (toutes les langues, tous les
        # prompts) pour remplir les onglets de langue du rapport.
        want_multilingual = args.multilingual or (args.report is not None)
        thr = Thresholds(subspace_k=args.subspace_k) if args.subspace_k else Thresholds()
        # cibles JORAK de la signature poids (o_proj seul par défaut ; multi-cible opt-in).
        wtargets = None
        if args.weight_targets:
            from modelscanner.core.types import WeightTarget

            wtargets = tuple(
                WeightTarget(x.strip()) for x in args.weight_targets.split(",") if x.strip()
            )

        # --- barre de progression + ETA (focalisée sur --report) ---
        pb = None
        if args.report is not None:
            from modelscanner.progress import (
                ProgressBar,
                estimate_scan_units,
                progress_enabled,
            )

            mlt_n_est = args.probe_subset or 10 ** 6  # --report = toute la sonde multilingue
            total_units = estimate_scan_units(
                lang=args.lang, probe_subset=args.probe_subset,
                with_activations=not args.no_activations,
                with_behavioral=want_behavioral,
                with_multilingual=want_multilingual,
                multilingual_harmless=True, multilingual_n=mlt_n_est,
                jorak_layers=getattr(handle, "n_layers", 0),
                jorak_targets=(len(wtargets) if wtargets else 1),
            )
            pb = ProgressBar(total_units, desc="scan", enabled=progress_enabled())

        result = scan(handle, with_behavioral=want_behavioral,
                      with_activations=not args.no_activations,
                      probe_subset=args.probe_subset, lang=args.lang,
                      weight_targets=wtargets,
                      expected_label=args.expected_label, thresholds=thr,
                      max_new_tokens=args.max_new_tokens,
                      progress=(pb.update if pb else None))
        if pb:
            pb.freeze()   # fige la barre avant les prints de résultat ci-dessous

        det = result.meta.get("classify_detail", {})
        band = det.get("band_alignment")
        sub = result.meta.get("subspace", {})
        ui.rule("provenance verdict")
        ui.kv("model", f"{result.model_id}  ({result.model_type}, {result.quantization.value})")
        ui.kv("verdict", ui.label_badge(result.label.value)
              + f"  confidence {result.confidence:.2f}")
        dmean = result.axis_quality["mean_cohens_d"]
        ui.kv("axis", f"mean Cohen's d {dmean:.2f}" if dmean is not None
              else "(activations plan off)")
        ui.kv("weights", f"global SVD alignment {result.svd_alignment:.3f}"
              + (f"  ·  band {band:.3f}" if band is not None else "")
              + (f"  ·  subspace k={sub.get('k')} {sub.get('alignment', 0):.3f}"
                 f"/band {sub.get('band', 0):.3f}" if sub else ""))
        if result.behavioral_refusal_rate is not None:
            ui.kv("compliance", f"refusal rate {result.behavioral_refusal_rate:.2f}"
                  + (f"  ·  harmless over-refusal {det['over_refusal']:.2f}"
                     if det.get("over_refusal") is not None else ""))
        else:
            ui.kv("compliance", "(not measured — use --behavioral)")
        if det.get("evasive_ablation"):
            ui.bullet("warn", "STEALTHY ablation suspected (weights ~intact to Jorak, "
                      "but live axis + complies + behavioral damage — norm-preserving multi-dir).")
        ui.kv("detail", str(result.meta['classify_detail']), value_codes=(ui.DIM,))

        if args.profile:
            from modelscanner.profile import model_profile

            prof = model_profile(handle, model_id=args.model)
            result.meta["model_profile"] = prof
            b = prof["behavior"]
            ui.kv("profile", f"harmful refusal {b['refusal_rate_harmful']:.2f} · "
                  f"harmless compliance {b['compliance_rate_harmless']:.2f} · "
                  f"hallu(acc) {prof['hallucination']['factual_accuracy']:.2f} · "
                  f"ppl {prof['quality']['neutral_perplexity']:.1f}")
            flags = prof.get("metadata", {}).get("declared_flags")
            if flags:
                ui.kv("HF tags", str(flags))

        if want_multilingual:
            from modelscanner.metrics.behavioral import multilingual_asymmetry

            # capture les Q/R par langue quand on produit un bundle --report
            mlt_qa = [] if args.report is not None else None
            # pour --report : TOUTE la sonde (tous les prompts de chaque langue),
            # sauf si --probe-subset borne explicitement. Sinon (plain --multilingual) : 8/langue.
            mlt_n = args.probe_subset or (10 ** 6 if args.report is not None else 8)
            # --report mesure AUSSI le sur-refus harmless par langue (dégât d'ablation).
            mlt = multilingual_asymmetry(handle, n=mlt_n, records=mlt_qa,
                                         with_harmless=args.report is not None,
                                         max_new_tokens=args.max_new_tokens,
                                         progress=(pb.update if pb else None))
            if pb:
                pb.close()   # fin de toute la génération -> barre 100 %
            result.meta["multilingual"] = mlt
            if mlt_qa is not None:
                result.meta["multilingual_qa"] = mlt_qa
            cap = f"  ·  {len(mlt_qa)} Q/A captured" if mlt_qa is not None else ""
            ui.kv("multiling", f"refusal/lang {mlt['per_lang_refusal']}  ·  MRA={mlt['mra']}"
                  f"  ·  spread={mlt['refusal_spread']}{cap}")
            if mlt.get("per_lang_over_refusal"):
                ui.kv("over-refusal", f"harmless/lang {mlt['per_lang_over_refusal']}"
                      f"  ·  max={mlt['max_over_refusal']}  ·  spread={mlt['over_refusal_spread']}")

            # repli du spread inter-langue dans le verdict : un refus très inégal
            # selon la langue est un signe d'ablation furtive (partielle/EN-only).
            # On re-classe avec ce signal en plus ; si le label bascule, on l'annonce.
            from modelscanner.classifier import Thresholds, classify

            d0 = result.meta["classify_detail"]
            new_label, new_conf, new_det = classify(
                max_cohens_d=d0.get("max_cohens_d"),
                svd_alignment=d0["svd_alignment"],
                median_suppression=d0["median_suppression"],
                band_alignment=d0["band_alignment"],
                refusal_rate=d0.get("refusal_rate"),
                subspace_alignment=d0.get("subspace_alignment", 0.0),
                subspace_band=d0.get("subspace_band", 0.0),
                over_refusal=d0.get("over_refusal"),
                refusal_spread=mlt.get("refusal_spread"),
                thr=Thresholds(**result.meta.get("thresholds", {})),
            )
            if new_label != result.label or abs(new_conf - result.confidence) > 1e-6:
                new_det["band_span"] = d0.get("band_span")
                new_det["subspace_band_span"] = d0.get("subspace_band_span")
                result.label, result.confidence = new_label, new_conf
                result.meta["classify_detail"] = new_det
                ui.bullet("warn", "verdict REVISED (multilingual spread folded in) → "
                          + ui.label_badge(new_label.value)
                          + f" confidence {new_conf:.2f}"
                          + ("  ⚠ stealthy ablation" if new_det.get("evasive_ablation") else ""))

        if args.log:
            from modelscanner.report import write_scan_log

            write_scan_log(result, args.log, flags={"device": args.device})
            ui.kv("log JSON", args.log)
        if pb:
            pb.close()   # filet de sécurité (idempotent) si la branche mlt a été sautée
        if args.report is not None:
            from modelscanner.report_single import write_scan_report

            paths = write_scan_report(result, base_dir=args.report,
                                      flags={"device": args.device},
                                      s3_prefix=s3_prefix, delete_local=delete_local)
            ui.rule("JORAK bundle")
            if paths.get("deleted_local"):
                ui.bullet("info", "local folder deleted after S3 upload (nothing kept locally)")
                ui.bullet("s3", "S3   " + ui.s3_uri(paths["s3"]))
            else:
                ui.kv("folder", paths["dir"])
                ui.kv("HTML EN", paths["html_en"])
                ui.kv("HTML FR", paths["html_fr"])
                ui.kv("prompts", paths["prompts_csv"])
                ui.kv("summary", paths["summary_csv"])
                ui.kv("JSON", paths["json"])
                if paths["heatmap"]:
                    ui.kv("heatmap", paths["heatmap"])
                if paths.get("bucket"):
                    ui.kv("4-buckets", paths["bucket"])
                if paths["s3"]:
                    ui.bullet("s3", "S3   " + ui.s3_uri(paths["s3"]))

        # nettoyage final (--s3) : purge du cache HF SEULEMENT si ce run a
        # téléchargé le modèle lui-même (modèle absent au départ).
        if args.s3 is not None and not model_was_cached:
            from modelscanner.hf_download import purge_model_cache

            purge_model_cache(args.model)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

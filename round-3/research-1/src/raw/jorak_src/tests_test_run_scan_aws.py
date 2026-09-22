"""Runner de campagne — câblage AWS (même méthode que `scan --s3`). Offline.

Vérifie que `experiments/run_scan.py`, en mode `download: true` / `purge: true` :
  - télécharge (procédure box) CHAQUE modèle avant de le scanner ;
  - ne purge du cache HF QUE les modèles que CE run a téléchargés lui-même
    (un modèle déjà en cache / local sous models_dir n'est jamais purgé).

Tout est mocké : aucun téléchargement, aucun scan réel, aucun accès réseau.
"""
import importlib.util
import json
import os
import sys
import types

import pytest

# --- charger experiments/run_scan.py comme module (hors package) ---
_RUN_SCAN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "experiments", "run_scan.py")


@pytest.fixture()
def run_scan():
    spec = importlib.util.spec_from_file_location("run_scan_mod", _RUN_SCAN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_runner_downloads_all_purges_only_what_it_fetched(run_scan, tmp_path, monkeypatch):
    calls = {"download": [], "purge": [], "cached_query": []}

    # "cached/m" est déjà hors-ligne ; "fresh/m" doit être téléchargé puis purgé.
    def fake_is_cached(ref):
        calls["cached_query"].append(ref)
        return ref == "cached/m"

    def fake_ensure(ref, **k):
        calls["download"].append(ref)
        return True

    def fake_purge(ref):
        calls["purge"].append(ref)
        return True

    monkeypatch.setattr(run_scan, "is_model_cached", fake_is_cached)
    monkeypatch.setattr(run_scan, "ensure_model_downloaded", fake_ensure)
    monkeypatch.setattr(run_scan, "purge_model_cache", fake_purge)

    # le "scan" (sous-process) écrit juste un JSON de résultat et réussit
    def fake_subprocess_run(cmd, *a, **k):
        log_path = cmd[cmd.index("--log") + 1]
        json.dump({"results": {"label": "ablated", "confidence": 0.9}},
                  open(log_path, "w", encoding="utf-8"))
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(run_scan.subprocess, "run", fake_subprocess_run)
    # le rapport de campagne final ne doit pas tourner pour de vrai
    fake_cr = types.ModuleType("campaign_report")
    fake_cr.generate = lambda *a, **k: None
    monkeypatch.setitem(sys.modules, "campaign_report", fake_cr)

    cfg = tmp_path / "run.yaml"
    cfg.write_text(
        "device: cpu\n"
        "plans:\n  behavioral: false\n  activations: false\n"
        "download: true\n"
        "purge: true\n"
        "min_free_gb: 0\n"  # neutralise la garde-disque : test hermétique (câblage, pas le disque réel du runner)
        f"output_dir: {tmp_path / 'out'}\n"
        "models:\n  - cached/m\n  - fresh/m\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["run_scan.py", str(cfg)])

    run_scan.main()

    # téléchargement tenté pour les DEUX (no-op interne si déjà en cache)
    assert calls["download"] == ["cached/m", "fresh/m"]
    # purge UNIQUEMENT du modèle que ce run a réellement téléchargé
    assert calls["purge"] == ["fresh/m"]


def test_dry_run_executes_nothing(run_scan, tmp_path, monkeypatch):
    """--dry-run : on affiche le plan mais on ne télécharge / scanne / purge rien."""
    calls = {"download": [], "purge": [], "scan": False}
    monkeypatch.setattr(run_scan, "is_model_cached", lambda ref: ref == "cached/m")
    monkeypatch.setattr(run_scan, "ensure_model_downloaded",
                        lambda ref, **k: calls["download"].append(ref))
    monkeypatch.setattr(run_scan, "purge_model_cache",
                        lambda ref: calls["purge"].append(ref))

    def boom(*a, **k):  # le scan ne doit JAMAIS partir en dry-run
        calls["scan"] = True
        raise AssertionError("subprocess.run ne doit pas être appelé en dry-run")

    monkeypatch.setattr(run_scan.subprocess, "run", boom)

    out = tmp_path / "out"
    cfg = tmp_path / "run.yaml"
    cfg.write_text(
        "device: cpu\ndownload: true\npurge: true\n"
        f"output_dir: {out}\n"
        "models:\n  - cached/m\n  - fresh/m\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["run_scan.py", str(cfg), "--dry-run"])

    run_scan.main()

    assert calls == {"download": [], "purge": [], "scan": False}
    assert not out.exists()  # dry-run ne crée même pas le dossier de run


def test_only_and_limit_select_subset(run_scan, tmp_path, monkeypatch):
    """--only filtre par motif, --limit borne le nombre — seuls ces modèles sont scannés."""
    scanned = []

    def fake_subprocess_run(cmd, *a, **k):
        ref = cmd[cmd.index("scan") + 1]
        scanned.append(ref)
        log_path = cmd[cmd.index("--log") + 1]
        json.dump({"results": {"label": "ablated", "confidence": 0.9}},
                  open(log_path, "w", encoding="utf-8"))
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(run_scan.subprocess, "run", fake_subprocess_run)
    fake_cr = types.ModuleType("campaign_report")
    fake_cr.generate = lambda *a, **k: None
    monkeypatch.setitem(sys.modules, "campaign_report", fake_cr)

    cfg = tmp_path / "run.yaml"
    cfg.write_text(
        "device: cpu\nplans:\n  behavioral: false\n  activations: false\n"
        f"output_dir: {tmp_path / 'out'}\n"
        "models:\n  - huihui/alpha\n  - dphn/beta\n  - other/gamma\n",
        encoding="utf-8",
    )

    # --only "dphn" -> un seul modèle
    monkeypatch.setattr(sys, "argv", ["run_scan.py", str(cfg), "--only", "dphn"])
    run_scan.main()
    assert scanned == ["dphn/beta"]

    # --limit 2 sur un nouveau run -> les 2 premiers seulement
    scanned.clear()
    cfg2 = tmp_path / "run2.yaml"
    cfg2.write_text(cfg.read_text(encoding="utf-8").replace("'out'", "'out2'")
                    .replace(str(tmp_path / 'out'), str(tmp_path / 'out2')),
                    encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["run_scan.py", str(cfg2), "--limit", "2"])
    run_scan.main()
    assert scanned == ["huihui/alpha", "dphn/beta"]


def test_runner_no_download_no_purge_by_default(run_scan, tmp_path, monkeypatch):
    calls = {"download": [], "purge": []}
    monkeypatch.setattr(run_scan, "is_model_cached", lambda ref: False)
    monkeypatch.setattr(run_scan, "ensure_model_downloaded",
                        lambda ref, **k: calls["download"].append(ref))
    monkeypatch.setattr(run_scan, "purge_model_cache",
                        lambda ref: calls["purge"].append(ref))

    def fake_subprocess_run(cmd, *a, **k):
        log_path = cmd[cmd.index("--log") + 1]
        json.dump({"results": {"label": "censored", "confidence": 0.8}},
                  open(log_path, "w", encoding="utf-8"))
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(run_scan.subprocess, "run", fake_subprocess_run)
    fake_cr = types.ModuleType("campaign_report")
    fake_cr.generate = lambda *a, **k: None
    monkeypatch.setitem(sys.modules, "campaign_report", fake_cr)

    cfg = tmp_path / "run.yaml"
    cfg.write_text(
        "device: cpu\n"
        "plans:\n  behavioral: false\n  activations: false\n"
        f"output_dir: {tmp_path / 'out'}\n"
        "models:\n  - some/model\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["run_scan.py", str(cfg)])

    run_scan.main()

    # sans `download`, le runner garde l'ancien comportement (local/CPU intact)
    assert calls["download"] == []
    assert calls["purge"] == []


# --------------------------------------------------------------------------
# Catégorisation des erreurs de scan (campagne ACTIONNABLE : kind + hint).
# --------------------------------------------------------------------------
import pytest as _pytest


@_pytest.mark.parametrize("stderr, kind", [
    ("modelscanner.loaders.arch_adapter.UnsupportedArchitecture: model_type 'ministral' non supporté",
     "unsupported_arch"),
    ("OSError: repo does not appear to have a file named pytorch_model.bin or model.safetensors",
     "unsupported_format"),
    # config.json sans model_type (huihui) -> kind dédié (inférence échouée si on le voit encore)
    ("ValueError: Unrecognized model in huihui-ai/Qwen3-8B-abliterated. Should have a `model_type`",
     "config_no_model_type"),
    # dépôt GGUF-only : notre garde-fou UnsupportedFormat met « gguf » dans le message
    ("modelscanner.loaders.errors.UnsupportedFormat: org/model : dépôt GGUF-only "
     "(aucun safetensors/bin) — format non supporté. GGUF not supported.",
     "gguf_only"),
    # notre exception dédiée transformers trop vieux (mistral3)
    ("modelscanner.loaders.errors.TransformersOutdated: org/Ministral-3-8B : model_type "
     "non reconnu par la version de transformers installée. transformers out of date.",
     "transformers_outdated"),
    ("ValueError: The checkpoint has model type `mistral3` but Transformers does not recognize "
     "this architecture. This could be because your version of Transformers is out of date.",
     "transformers_outdated"),
    ("huggingface_hub.utils._errors.GatedRepoError: 403 Client Error. Access to model X is restricted",
     "gated"),
    ("torch.cuda.OutOfMemoryError: CUDA out of memory. Tried to allocate 2 GiB",
     "oom"),
    ("requests.exceptions.ConnectionError: Max retries exceeded ... Read timed out",
     "download"),
    # ENOSPC pendant http_get : NE DOIT PAS être étiqueté « download » (trace
    # réseau trompeuse) mais « disk_full » — cf. campagne 2026-07-01.
    ("  File \"file_download.py\", line 436, in http_get\n    temp_file.write(chunk)\n"
     "OSError: [Errno 28] No space left on device",
     "disk_full"),
    # shard safetensors manquant au chargement = snapshot partiel (séquelle ENOSPC)
    ("FileNotFoundError: No such file or directory: "
     "/home/x/.cache/huggingface/hub/models--org--m/snapshots/abc/model-00001-of-00004.safetensors",
     "incomplete_download"),
    ("RuntimeError: something unexpected blew up", "scan_failed"),
])
def test_classify_error_kinds(run_scan, stderr, kind):
    got_kind, hint = run_scan._classify_error(stderr)
    assert got_kind == kind
    assert isinstance(hint, str) and hint            # une remédiation non vide


def test_classify_error_empty():
    spec = importlib.util.spec_from_file_location("run_scan_mod2", _RUN_SCAN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod._classify_error("")[0] == "scan_failed"
    assert mod._classify_error(None)[0] == "scan_failed"

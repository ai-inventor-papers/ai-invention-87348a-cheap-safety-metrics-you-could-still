"""Barre de progression (ETA) + push S3 avec purge locale (--s3). Offline.

Couvre :
  - les utilitaires purs de `modelscanner.progress` (format ETA, découpage
    train/test, estimation du nombre d'unités, mécanique de la barre) ;
  - la résolution du préfixe S3 fixe `result/Jorack result` ;
  - la purge locale conditionnelle de `write_scan_report` : on ne supprime le
    bundle local QUE si l'upload S3 a réussi.
"""
import io
import os

import numpy as np

from modelscanner import Quantization, ScanResult
from modelscanner import report_single as rs
from modelscanner.classifier.scanner import Thresholds, classify
from modelscanner.progress import (
    ProgressBar,
    _fmt_dur,
    _split_eval_count,
    estimate_scan_units,
)


# --------------------------------------------------------------------------- #
# progress.py — utilitaires purs                                              #
# --------------------------------------------------------------------------- #
def test_fmt_dur():
    assert _fmt_dur(0) == "00:00"
    assert _fmt_dur(75) == "01:15"
    assert _fmt_dur(3725) == "1:02:05"
    assert _fmt_dur(float("inf")) == "--:--"
    assert _fmt_dur(-1) == "--:--"
    assert _fmt_dur(float("nan")) == "--:--"


def test_split_eval_count_matches_scan_logic():
    # 40 probes -> train=24, eval=16 (split appliqué : >=4 de chaque côté)
    assert _split_eval_count(40) == 16
    assert _split_eval_count(24) == 10
    # trop peu de probes -> pas de split, on évalue sur tout
    assert _split_eval_count(6) == 6
    assert _split_eval_count(7) == 7  # train=4, eval=3 (<4) -> pas de split


def test_estimate_scan_units_report_en():
    # report EN : 80 activations + 32 behavioral + 320 multilingue = 432
    assert estimate_scan_units(lang="en") == 432
    # sans activations : pas de forward ni de over-refusal harmless
    n = estimate_scan_units(lang="en", with_activations=False)
    assert n == 16 + 320  # behavioral harmful (16) + multilingue (320)
    # probe_subset borne le total
    assert estimate_scan_units(lang="en", probe_subset=4) < estimate_scan_units(lang="en")
    assert estimate_scan_units(with_multilingual=False, with_behavioral=False,
                               with_activations=False) == 1  # plancher


def test_progressbar_counts_and_caps():
    buf = io.StringIO()
    pb = ProgressBar(10, stream=buf, min_interval=0.0)
    for _ in range(7):
        pb.update(1)
    assert pb.n == 7
    # callback signature `(n, desc=...)` : on peut passer pb.update tel quel
    cb = pb.update
    cb(3, desc="multilingual · zh")
    assert pb.n == 10
    pb.close()
    pb.close()  # idempotent
    out = buf.getvalue()
    assert "100.0%" in out and "done in" in out


def test_progressbar_disabled_is_silent():
    buf = io.StringIO()
    pb = ProgressBar(5, stream=buf, enabled=False)
    pb.update(3)
    pb.freeze()
    pb.close()
    assert buf.getvalue() == ""


# --------------------------------------------------------------------------- #
# Résolution du préfixe S3 fixe (bucket your-bucket par défaut, sous-chemin Jorak)  #
# --------------------------------------------------------------------------- #
def test_resolve_s3_dest():
    # défaut : bucket your-bucket, rien à préciser au terminal
    assert rs.resolve_s3_dest() == "s3://your-bucket/results/Jorak"
    assert rs.resolve_s3_dest("") == "s3://your-bucket/results/Jorak"
    assert rs.resolve_s3_dest(None) == "s3://your-bucket/results/Jorak"
    # surcharge du bucket SEUL -> +/results/Jorak
    assert rs.resolve_s3_dest("my-bucket") == "s3://my-bucket/results/Jorak"
    assert rs.resolve_s3_dest("s3://my-bucket") == "s3://my-bucket/results/Jorak"
    # PRÉFIXE EXACT (chemin après le bucket) -> tel quel (ex-`--report-s3`)
    assert rs.resolve_s3_dest("s3://my-bucket/runs") == "s3://my-bucket/runs"
    assert rs.resolve_s3_dest("s3://my-bucket/runs/") == "s3://my-bucket/runs"


# --------------------------------------------------------------------------- #
# hf_download — cache + procédure de téléchargement box AWS                    #
# --------------------------------------------------------------------------- #
def test_is_model_cached_local_dir(tmp_path):
    from modelscanner.hf_download import is_model_cached

    assert is_model_cached(str(tmp_path)) is True          # chemin local existant
    assert is_model_cached("definitely/not-a-real-model-xyz") is False


def test_download_command_reproduces_box_procedure():
    from modelscanner.hf_download import download_command

    cmd = download_command("meta-llama/Llama-3.2-1B-Instruct")
    assert 'cd "$HOME/venv/scripts"' in cmd  # $HOME non quoté (expansion)
    assert "source activate" in cmd
    assert "export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-bundle.crt" in cmd
    assert "export SSL_CERT_FILE=/etc/ssl/certs/ca-bundle.crt" in cmd
    assert "sudo -s source /path/to/.env_secrets" in cmd
    assert "hf download meta-llama/Llama-3.2-1B-Instruct" in cmd
    # repos mixtes safetensors+gguf : on n'aspire PAS les blobs GGUF par défaut.
    assert "--exclude '*.gguf'" in cmd


def test_download_command_exclude_is_env_overridable(monkeypatch):
    # le module lit ABLATION_DOWNLOAD_EXCLUDE à l'import -> recharger après set.
    import importlib

    import modelscanner.hf_download as hd

    monkeypatch.setenv("ABLATION_DOWNLOAD_EXCLUDE", "*.gguf *.pt")
    hd = importlib.reload(hd)
    try:
        cmd = hd.download_command("some/model")
        assert "--exclude '*.gguf'" in cmd
        assert "--exclude '*.pt'" in cmd
    finally:
        monkeypatch.delenv("ABLATION_DOWNLOAD_EXCLUDE", raising=False)
        importlib.reload(hd)   # restaure le défaut pour les autres tests


def test_ensure_model_downloaded_skips_when_cached(tmp_path, monkeypatch):
    import modelscanner.hf_download as hd

    called = {"ran": False}
    monkeypatch.setattr(hd.subprocess, "run",
                        lambda *a, **k: called.__setitem__("ran", True))
    # chemin local existant -> en cache -> aucun subprocess lancé
    assert hd.ensure_model_downloaded(str(tmp_path)) is True
    assert called["ran"] is False


def test_purge_model_cache_skips_local_dir(tmp_path):
    from modelscanner.hf_download import purge_model_cache

    # chemin local de l'utilisateur : on ne supprime JAMAIS
    assert purge_model_cache(str(tmp_path)) is False


def test_purge_model_cache_deletes_matching_repo(monkeypatch):
    import sys
    import types

    from modelscanner.hf_download import purge_model_cache

    executed = {"ran": False, "hashes": None}

    class _Rev:
        def __init__(self, h):
            self.commit_hash = h

    class _Repo:
        def __init__(self, rid, hs):
            self.repo_id = rid
            self.revisions = [_Rev(h) for h in hs]

    class _Strategy:
        expected_freed_size_str = "1.2G"

        def execute(self):
            executed["ran"] = True

    class _Cache:
        repos = [_Repo("ed/m", ["abc", "def"]), _Repo("other/x", ["zzz"])]

        def delete_revisions(self, *hashes):
            executed["hashes"] = set(hashes)
            return _Strategy()

    # faux module huggingface_hub (le vrai n'est pas requis pour ce test offline)
    fake = types.ModuleType("huggingface_hub")
    fake.scan_cache_dir = lambda: _Cache()
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake)

    assert purge_model_cache("ed/m") is True          # repo présent -> supprimé
    assert executed["ran"] is True
    assert executed["hashes"] == {"abc", "def"}        # toutes ses révisions
    assert purge_model_cache("absent/repo") is False   # repo absent -> no-op


def test_purge_partial_cache_removes_broken_repo(tmp_path, monkeypatch):
    # snapshot partiel (séquelle ENOSPC) : `delete_revisions` ne le voit pas ->
    # `_purge_partial_cache` doit récupérer l'espace et supprimer le dossier.
    import modelscanner.hf_download as hd

    hub = tmp_path / "hub"
    repo = hub / "models--org--m"
    blobs = repo / "blobs"
    snap = repo / "snapshots" / "abc"
    blobs.mkdir(parents=True)
    snap.mkdir(parents=True)
    (blobs / "deadbeef").write_bytes(b"x" * 100)            # blob complet
    (blobs / "deadbeef.incomplete").write_bytes(b"y" * 50)  # résidu coupé
    (snap / "model.safetensors").write_bytes(b"z" * 30)

    monkeypatch.setattr(hd, "_hf_hub_cache", lambda: str(hub))
    monkeypatch.setattr(hd, "is_model_cached", lambda mid: False)  # repo cassé

    freed = hd._purge_partial_cache("org/m")
    assert freed >= 180                 # 50 (.incomplete) + 100 + 30
    assert not repo.exists()            # dossier de repo entièrement supprimé


def test_purge_partial_cache_keeps_complete_repo(tmp_path, monkeypatch):
    # repo COMPLET : on ne supprime QUE le résidu `.incomplete`, jamais les blobs.
    import modelscanner.hf_download as hd

    hub = tmp_path / "hub"
    blobs = hub / "models--org--m" / "blobs"
    blobs.mkdir(parents=True)
    (blobs / "sha").write_bytes(b"x" * 100)
    inc = blobs / "sha.incomplete"
    inc.write_bytes(b"y" * 40)

    monkeypatch.setattr(hd, "_hf_hub_cache", lambda: str(hub))
    monkeypatch.setattr(hd, "is_model_cached", lambda mid: True)   # repo complet

    freed = hd._purge_partial_cache("org/m")
    assert freed == 40                  # seul le .incomplete est récupéré
    assert not inc.exists()
    assert (blobs / "sha").exists()     # blob complet conservé


def test_purge_partial_cache_ignores_absent_repo(tmp_path, monkeypatch):
    # hub calculé sans dossier de repo -> no-op strict (rien à supprimer).
    import modelscanner.hf_download as hd

    monkeypatch.setattr(hd, "_hf_hub_cache", lambda: str(tmp_path / "empty_hub"))
    assert hd._purge_partial_cache("org/m") == 0


# --------------------------------------------------------------------------- #
# write_scan_report — purge locale conditionnelle (--s3)                      #
# --------------------------------------------------------------------------- #
def _make_result() -> ScanResult:
    n_layers, hidden = 6, 32
    rng = np.random.default_rng(0)
    label, conf, detail = classify(
        max_cohens_d=4.5, svd_alignment=0.87, median_suppression=0.001,
        band_alignment=0.6, refusal_rate=0.05, subspace_alignment=0.6,
        subspace_band=0.5)
    detail["band_span"] = [1, 3]
    detail["subspace_band_span"] = [1, 3]
    return ScanResult(
        model_id="dummy/model", model_type="qwen2", quantization=Quantization.BF16,
        n_layers=n_layers, hidden_size=hidden,
        directions=rng.standard_normal((n_layers, hidden)).astype(np.float32),
        cohens_d=rng.standard_normal(n_layers).astype(np.float32),
        suppression={"o_proj": np.array([0.5, 0.4, 0.001, 0.002, 0.3, 0.6], dtype=np.float32),
                     "down_proj": np.array([0.5, 0.4, 0.0005, 0.45, 0.3, 0.6], dtype=np.float32)},
        weight_axis_align=rng.random(n_layers).astype(np.float32),
        svd_alignment=0.87, svd_pairwise_cos=0.42, behavioral_refusal_rate=0.05,
        label=label, confidence=conf,
        meta={"thresholds": vars(Thresholds()), "svd_target": "o_proj",
              "suppression_threshold": 0.01, "classify_detail": detail,
              "subspace": {"alignment": 0.6, "band": 0.5, "band_span": [1, 3],
                           "k": 4, "per_layer_align": [0.1] * 6},
              "behavioral_over_refusal": 0.1,
              "run": {"lang": "en", "n_probes": 40, "with_behavioral": True,
                      "with_activations": True, "target": "o_proj"},
              "behavioral_qa": [{"i": 0, "prompt": "q", "response": "i cannot",
                                 "refusal": True}],
              "expected_label": None})


def test_write_scan_report_deletes_local_after_successful_upload(tmp_path, monkeypatch):
    # upload "réussi" -> le local doit disparaître, l'URI S3 est renvoyée
    monkeypatch.setattr(rs, "_s3_sync_dir",
                        lambda d, p: p.rstrip("/") + "/" + os.path.basename(d))
    paths = rs.write_scan_report(_make_result(), base_dir=str(tmp_path),
                                 with_heatmap=False,
                                 s3_prefix=rs.resolve_s3_dest(),  # s3://your-bucket/results/Jorak
                                 delete_local=True)
    assert paths["deleted_local"] is True
    assert not os.path.exists(paths["dir"])
    assert paths["s3"].endswith("/results/Jorak/" + os.path.basename(paths["dir"]))


def test_write_scan_report_keeps_local_when_upload_fails(tmp_path, monkeypatch):
    # upload KO (aws absent) -> on NE supprime PAS : rien ne doit être perdu
    monkeypatch.setattr(rs, "_s3_sync_dir", lambda d, p: None)
    paths = rs.write_scan_report(_make_result(), base_dir=str(tmp_path),
                                 with_heatmap=False, s3_prefix="s3://b/x",
                                 delete_local=True)
    assert paths["deleted_local"] is False
    assert os.path.exists(paths["dir"])
    assert paths["s3"] is None


def test_write_scan_report_no_s3_keeps_local(tmp_path):
    paths = rs.write_scan_report(_make_result(), base_dir=str(tmp_path),
                                 with_heatmap=False)
    assert paths["deleted_local"] is False
    assert os.path.isdir(paths["dir"])
    assert paths["s3"] is None

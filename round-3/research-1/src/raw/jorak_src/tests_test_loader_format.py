"""Garde-fous de chargement [J10] : inférence model_type, rejet GGUF, config réparée.

Couvre les correctifs issus du debug de campagne2 :
  - dépôts huihui-ai sans clé ``model_type`` (inférée depuis ``architectures``),
  - dépôts GGUF-only rejetés TÔT avec une erreur claire,
  - distinction des causes racines (format vs transformers trop vieux).

Tout est offline / sans téléchargement (fonctions pures + tmp dirs)."""
from __future__ import annotations

import json

import pytest

from modelscanner.loaders import safetensors_loader as sl
from modelscanner.loaders.errors import UnsupportedFormat


# --------------------------------------------------------------------------- #
# Inférence du model_type depuis architectures (cas huihui)                    #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("arch, expected", [
    ("Qwen3ForCausalLM", "qwen3"),
    ("MistralForCausalLM", "mistral"),
    ("LlamaForCausalLM", "llama"),
    ("Qwen2ForCausalLM", "qwen2"),
])
def test_infer_model_type_from_architectures(arch, expected):
    assert sl._infer_model_type({"architectures": [arch]}) == expected


@pytest.mark.parametrize("raw", [None, {}, {"architectures": []}])
def test_infer_model_type_none_when_absent(raw):
    assert sl._infer_model_type(raw) is None


def test_infer_model_type_unknown_falls_back_to_lowercase():
    # famille exotique non mappée -> repli base.lower() (jamais None si arch présent)
    assert sl._infer_model_type({"architectures": ["FooBarForCausalLM"]}) == "foobar"


# --------------------------------------------------------------------------- #
# Garde-fou GGUF / poids non chargeables                                       #
# --------------------------------------------------------------------------- #
def test_gguf_only_dir_rejected(tmp_path):
    (tmp_path / "model.gguf").write_bytes(b"\x00")
    with pytest.raises(UnsupportedFormat) as ei:
        sl._assert_loadable_weights(str(tmp_path), "org/model-gguf")
    assert "gguf" in str(ei.value).lower()


def test_gguf_file_path_rejected():
    with pytest.raises(UnsupportedFormat):
        sl._assert_loadable_weights("/some/where/model.gguf", "org/model.gguf")


def test_empty_dir_rejected_as_no_weights(tmp_path):
    with pytest.raises(UnsupportedFormat) as ei:
        sl._assert_loadable_weights(str(tmp_path), "org/empty")
    assert "loadable" in str(ei.value).lower() or "chargeable" in str(ei.value).lower()


def test_safetensors_present_ok(tmp_path):
    (tmp_path / "model.safetensors").write_bytes(b"\x00")
    # mix safetensors + gguf : on charge le safetensors, pas d'erreur.
    (tmp_path / "extra.gguf").write_bytes(b"\x00")
    sl._assert_loadable_weights(str(tmp_path), "org/mixed")  # ne lève pas


def test_remote_id_not_inspected():
    # id distant non résolu (pas un dossier) : on laisse passer (from_pretrained gère).
    sl._assert_loadable_weights("org/not-on-disk", "org/not-on-disk")


# --------------------------------------------------------------------------- #
# _load_config : config.json sans model_type -> réparée par inférence          #
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# Repli multimodal : décision CausalLM -> ImageTextToText/AutoModel             #
# --------------------------------------------------------------------------- #
def test_causal_lm_unsupported_detects_multimodal_config():
    # message réel de transformers pour un *ForConditionalGeneration (mistral3, etc.)
    err = ValueError(
        "Unrecognized configuration class <class 'transformers.models.mistral3."
        "configuration_mistral3.Mistral3Config'> for this kind of AutoModel: "
        "AutoModelForCausalLM."
    )
    assert sl._causal_lm_unsupported(err) is True


def test_causal_lm_unsupported_ignores_other_errors():
    # une vraie erreur de chargement ne doit PAS déclencher le repli multimodal
    assert sl._causal_lm_unsupported(RuntimeError("CUDA out of memory")) is False
    assert sl._causal_lm_unsupported(ValueError("some random load failure")) is False


def test_load_config_repairs_missing_model_type(tmp_path):
    pytest.importorskip("transformers")  # stack ML absente (box CPU) -> skip propre
    from transformers import CONFIG_MAPPING

    if "llama" not in CONFIG_MAPPING:  # robustesse multi-version transformers
        pytest.skip("LlamaConfig indisponible dans cette version de transformers")
    # config.json à la huihui : architectures présent, model_type ABSENT.
    cfg = {
        "architectures": ["LlamaForCausalLM"],
        "hidden_size": 16,
        "num_hidden_layers": 2,
        "num_attention_heads": 2,
        "vocab_size": 32,
    }
    (tmp_path / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
    resolved = sl._load_config(str(tmp_path), "huihui-ai/fake", trust_remote_code=False)
    assert resolved.model_type == "llama"
    assert resolved.num_hidden_layers == 2

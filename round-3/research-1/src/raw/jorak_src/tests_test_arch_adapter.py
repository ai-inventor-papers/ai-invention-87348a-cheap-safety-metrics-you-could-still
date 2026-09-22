"""J0 — validation de l'arch_adapter : les chemins de poids se résolvent."""
import pytest

from modelscanner.loaders import arch_adapter as aa


class _Cfg:
    """Faux objet config HF minimal."""

    def __init__(self, model_type, num_hidden_layers=None, hidden_size=None, text_config=None):
        self.model_type = model_type
        if num_hidden_layers is not None:
            self.num_hidden_layers = num_hidden_layers
        if hidden_size is not None:
            self.hidden_size = hidden_size
        if text_config is not None:
            self.text_config = text_config


@pytest.mark.parametrize("mt", ["qwen2", "qwen3", "mistral", "gemma", "gemma2", "gemma3_text"])
def test_llama_like_paths(mt):
    spec = aa.resolve(model_type=mt)
    assert spec.o_proj_path(0) == "model.layers.0.self_attn.o_proj"
    assert spec.down_proj_path(7) == "model.layers.7.mlp.down_proj"
    assert spec.embed_path() == "model.embed_tokens"


def test_gemma3_multimodal_nesting():
    spec = aa.resolve(model_type="gemma3")
    assert spec.o_proj_path(0) == "model.language_model.layers.0.self_attn.o_proj"
    assert spec.embed_path() == "model.language_model.embed_tokens"


def test_aliases_resolve():
    assert aa.resolve(model_type="mixtral").model_type == "mistral"
    assert aa.resolve(model_type="qwen2_moe").model_type == "qwen2"


def test_resolve_from_config():
    spec = aa.resolve(config=_Cfg("qwen2"))
    assert spec.o_proj_path(3) == "model.layers.3.self_attn.o_proj"


def test_override_takes_priority():
    custom = aa.ArchSpec("weird", "backbone.blocks", "attn.out", "ffn.down", "tok_emb")
    spec = aa.resolve(model_type="qwen2", override=custom)
    assert spec is custom
    assert spec.o_proj_path(1) == "backbone.blocks.1.attn.out"


def test_unsupported_raises():
    with pytest.raises(aa.UnsupportedArchitecture):
        aa.resolve(model_type="totally-unknown-arch")
    with pytest.raises(aa.UnsupportedArchitecture):
        aa.resolve()  # ni model_type ni config


def test_num_layers_and_hidden_from_text_config():
    cfg = _Cfg("gemma3", text_config=_Cfg("gemma3_text", num_hidden_layers=26, hidden_size=640))
    assert aa.get_num_layers(cfg) == 26
    assert aa.get_hidden_size(cfg) == 640


# --------------------------------------------------------------------------
# Familles Mistral/Ministral (cause des 5 échecs de la campagne 8B)
# --------------------------------------------------------------------------
def test_ministral_is_mistral_alias():
    """`ministral` (Ministral-8B-Instruct-2410) = nommage Mistral à plat."""
    spec = aa.resolve(model_type="ministral")
    assert spec.model_type == "mistral"            # alias
    assert spec.o_proj_path(0) == "model.layers.0.self_attn.o_proj"
    assert spec.down_proj_path(3) == "model.layers.3.mlp.down_proj"
    assert spec.embed_path() == "model.embed_tokens"


def test_mistral3_nested_decoder():
    """`mistral3` (Ministral-3 / Mistral-Small-3) = décodeur niché (multimodal)."""
    spec = aa.resolve(model_type="mistral3")
    assert spec.o_proj_path(0) == "model.language_model.layers.0.self_attn.o_proj"
    assert spec.embed_path() == "model.language_model.embed_tokens"


# --------------------------------------------------------------------------
# Auto-détection des chemins de poids sur un modèle chargé (filet de sécurité)
# --------------------------------------------------------------------------
class _FakeModule:
    """Mime l'API nn.Module utilisée par autodetect/resolve_against_model :
    `named_modules()` et `get_submodule(path)`."""

    def __init__(self, names, config=None):
        self._names = list(names)
        self.config = config

    def named_modules(self):
        return [(n, object()) for n in self._names]

    def get_submodule(self, path):
        if path in self._names:
            return object()
        raise AttributeError(path)


def _decoder_names(layers_path, n=4, *, embed=None, down="mlp.down_proj"):
    """Génère les noms de sous-modules d'un décodeur (couches + embed)."""
    names = [layers_path]
    for i in range(n):
        names += [
            f"{layers_path}.{i}",
            f"{layers_path}.{i}.self_attn.o_proj",
            f"{layers_path}.{i}.{down}",
        ]
    base = layers_path[: -len(".layers")] if layers_path.endswith(".layers") else layers_path
    names.append(embed or f"{base}.embed_tokens")
    return names


def test_autodetect_flat_decoder():
    model = _FakeModule(_decoder_names("model.layers", n=5))
    spec = aa.autodetect_arch(model, model_type="ministral")
    assert spec.o_proj_path(0) == "model.layers.0.self_attn.o_proj"
    assert spec.down_proj_path(2) == "model.layers.2.mlp.down_proj"
    assert spec.embed_path() == "model.embed_tokens"


def test_autodetect_nested_decoder():
    model = _FakeModule(_decoder_names("model.language_model.layers", n=3))
    spec = aa.autodetect_arch(model)
    assert spec.o_proj_path(0) == "model.language_model.layers.0.self_attn.o_proj"
    assert spec.embed_path() == "model.language_model.embed_tokens"


def test_autodetect_picks_deepest_decoder():
    """Quand plusieurs conteneurs `*.layers` existent (ex. vision tower), on prend
    le décodeur le PLUS profond (le plus de couches)."""
    names = _decoder_names("model.language_model.layers", n=6)
    names += _decoder_names("vision_tower.layers", n=2)   # leurre, moins de couches
    spec = aa.autodetect_arch(_FakeModule(names))
    assert spec.layers_path == "model.language_model.layers"


def test_autodetect_raises_without_attention():
    with pytest.raises(aa.UnsupportedArchitecture):
        aa.autodetect_arch(_FakeModule(["model", "model.embed_tokens"]))


def test_resolve_against_model_validates_registry():
    """Famille connue + chemins valides -> on garde la spec du registre."""
    model = _FakeModule(_decoder_names("model.layers", n=4))
    spec = aa.resolve_against_model(model, config=_Cfg("qwen3"))
    assert spec.model_type == "qwen3"
    assert spec.o_proj_path(0) == "model.layers.0.self_attn.o_proj"


def test_resolve_against_model_selfheals_wrong_nesting():
    """`mistral3` enregistré niché, mais le checkpoint réel est TEXT-ONLY à plat :
    le chemin niché ne se résout pas -> auto-détection des chemins à plat."""
    model = _FakeModule(_decoder_names("model.layers", n=4))   # à plat, pas de language_model
    spec = aa.resolve_against_model(model, config=_Cfg("mistral3"))
    assert spec.o_proj_path(0) == "model.layers.0.self_attn.o_proj"


def test_resolve_against_model_unknown_family_autodetects():
    """Famille absente du registre -> autodetect au lieu de lever."""
    model = _FakeModule(_decoder_names("model.layers", n=4))
    spec = aa.resolve_against_model(model, config=_Cfg("some-new-arch-9000"))
    assert spec.model_type == "some-new-arch-9000"
    assert spec.o_proj_path(0) == "model.layers.0.self_attn.o_proj"


def test_resolve_against_model_override_wins():
    custom = aa.ArchSpec("weird", "backbone.blocks", "attn.out", "ffn.down", "tok_emb")
    model = _FakeModule(_decoder_names("model.layers", n=4))
    assert aa.resolve_against_model(model, config=_Cfg("qwen3"), override=custom) is custom

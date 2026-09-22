"""Architecture adapter — mapping {model_type -> chemins des poids}.

Principe (brief §3.1) : ajouter une famille de modèles = ajouter une entrée
dans le registre, JAMAIS réécrire le détecteur. On résout, pour une famille
donnée, les chemins de module de `self_attn.o_proj`, `mlp.down_proj` et
`embed_tokens`, ainsi que le nombre de couches.

Les chemins sont donnés sous forme de templates relatifs (`{i}` = index de
couche) et fonctionnent aussi bien comme clés safetensors
(`model.layers.0.self_attn.o_proj.weight`) que comme arguments de
`nn.Module.get_submodule("model.layers.0.self_attn.o_proj")`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


class UnsupportedArchitecture(Exception):
    """Famille non reconnue et aucun override fourni."""


# ⚠ PÉRENNITÉ (cf. docs/MAINTENANCE.md §1) : ajouter une famille ici NE SUFFIT PAS
# si la version de `transformers` installée ne connaît pas son `model_type` — le
# chargement casse à `AutoConfig`/`AutoModelForCausalLM`, AVANT ce registre (ex.
# `mistral3` sur une box pas à jour). Le scanner doit suivre les montées de version
# de transformers pour les nouvelles familles de modèles. Le runner signale ce cas
# via `error_kind = transformers_outdated`.


@dataclass(frozen=True)
class ArchSpec:
    """Description des chemins de poids d'une famille."""

    model_type: str
    layers_path: str          # ex. "model.layers"
    o_proj: str               # relatif à une couche, ex. "self_attn.o_proj"
    down_proj: str            # ex. "mlp.down_proj"
    embed_tokens: str         # ex. "model.embed_tokens"
    # autres model_type qui partagent exactement ces chemins
    aliases: Tuple[str, ...] = field(default_factory=tuple)

    def o_proj_path(self, layer: int) -> str:
        return f"{self.layers_path}.{layer}.{self.o_proj}"

    def down_proj_path(self, layer: int) -> str:
        return f"{self.layers_path}.{layer}.{self.down_proj}"

    def embed_path(self) -> str:
        return self.embed_tokens


# --- famille "llama-like" : naming partagé par Llama/Mistral/Qwen/Gemma texte
_LLAMA_LIKE = dict(
    layers_path="model.layers",
    o_proj="self_attn.o_proj",
    down_proj="mlp.down_proj",
    embed_tokens="model.embed_tokens",
)

_SPECS: Tuple[ArchSpec, ...] = (
    # --- Must (brief §3.1) ---
    ArchSpec(model_type="qwen2", aliases=("qwen2_moe",), **_LLAMA_LIKE),
    ArchSpec(model_type="qwen3", aliases=("qwen3_moe",), **_LLAMA_LIKE),
    # `ministral` (Ministral-8B-Instruct-2410) partage EXACTEMENT le nommage Mistral
    # (model.layers.N.self_attn.o_proj / mlp.down_proj) -> simple alias.
    ArchSpec(model_type="mistral", aliases=("mixtral", "ministral"), **_LLAMA_LIKE),
    # Mistral 3 / Ministral-3 (model_type "mistral3") : wrapper multimodal
    # Mistral3ForConditionalGeneration -> décodeur texte niché sous
    # model.language_model (même schéma que gemma3 ci-dessous). Si le checkpoint est
    # en réalité text-only (model.layers à plat), `resolve_against_model` corrige
    # les chemins par auto-détection sur le modèle chargé.
    ArchSpec(
        model_type="mistral3",
        layers_path="model.language_model.layers",
        o_proj="self_attn.o_proj",
        down_proj="mlp.down_proj",
        embed_tokens="model.language_model.embed_tokens",
    ),
    # --- Haute priorité ---
    ArchSpec(model_type="gemma", **_LLAMA_LIKE),
    ArchSpec(model_type="gemma2", **_LLAMA_LIKE),
    # Gemma 3 texte-only (ex. modèle de dev gemma-3-270m-it)
    ArchSpec(model_type="gemma3_text", **_LLAMA_LIKE),
    # Gemma 3 multimodal : décodeur texte niché sous model.language_model
    ArchSpec(
        model_type="gemma3",
        layers_path="model.language_model.layers",
        o_proj="self_attn.o_proj",
        down_proj="mlp.down_proj",
        embed_tokens="model.language_model.embed_tokens",
    ),
    # DeepSeek distills (architecture Llama/Qwen) — MoE/MLA natif en v2
    ArchSpec(model_type="llama", **_LLAMA_LIKE),
)

# index {model_type|alias -> ArchSpec}
_REGISTRY: Dict[str, ArchSpec] = {}
for _s in _SPECS:
    _REGISTRY[_s.model_type] = _s
    for _a in _s.aliases:
        _REGISTRY[_a] = _s


def _model_type_from_config(config: Any) -> Optional[str]:
    """Extrait model_type d'un objet config HF ou d'un dict."""
    if config is None:
        return None
    mt = getattr(config, "model_type", None)
    if mt is None and isinstance(config, dict):
        mt = config.get("model_type")
    return mt


def get_num_layers(config: Any) -> int:
    """num_hidden_layers, en gérant les configs multimodales (text_config)."""
    for obj in (config, getattr(config, "text_config", None)):
        if obj is None:
            continue
        n = getattr(obj, "num_hidden_layers", None)
        if n is None and isinstance(obj, dict):
            n = obj.get("num_hidden_layers")
        if n is not None:
            return int(n)
    raise UnsupportedArchitecture("num_hidden_layers introuvable dans la config.")


def get_hidden_size(config: Any) -> int:
    for obj in (config, getattr(config, "text_config", None)):
        if obj is None:
            continue
        h = getattr(obj, "hidden_size", None)
        if h is None and isinstance(obj, dict):
            h = obj.get("hidden_size")
        if h is not None:
            return int(h)
    raise UnsupportedArchitecture("hidden_size introuvable dans la config.")


def resolve(
    model_type: Optional[str] = None,
    config: Any = None,
    override: Optional[ArchSpec] = None,
) -> ArchSpec:
    """Résout l'ArchSpec d'une famille.

    Priorité : `override` (manuel, brief §3.1) > `model_type` explicite >
    `config.model_type`. Lève `UnsupportedArchitecture` si inconnue.
    """
    if override is not None:
        return override
    mt = model_type or _model_type_from_config(config)
    if mt is None:
        raise UnsupportedArchitecture("Aucun model_type fourni (ni explicite, ni via config).")
    spec = _REGISTRY.get(mt)
    if spec is None:
        raise UnsupportedArchitecture(
            f"model_type '{mt}' non supporté. Familles connues : "
            f"{sorted(_REGISTRY)}. Fournis un `override=ArchSpec(...)`."
        )
    return spec


def supported_model_types() -> Tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


def autodetect_arch(model: Any, model_type: Optional[str] = None) -> ArchSpec:
    """Déduit un ``ArchSpec`` en INSPECTANT un modèle torch déjà chargé.

    Filet de sécurité reference-free quand (a) le registre ne connaît pas la
    famille, ou (b) le nesting réel diffère du registre (ex. ``mistral3``
    text-only à plat vs multimodal niché). On localise le conteneur de couches du
    décodeur via les sous-modules ``*.<i>.self_attn.o_proj``, puis on en déduit
    les chemins relatifs ``o_proj``/``down_proj`` et l'embedding (frère des
    couches). Aucune sonde, aucune génération.

    Lève ``UnsupportedArchitecture`` si aucun bloc d'attention ``self_attn.o_proj``
    n'est trouvé (architecture vraiment exotique)."""
    import re
    from collections import defaultdict

    names = [n for n, _ in model.named_modules()]
    nameset = set(names)
    pat = re.compile(r"^(?P<prefix>.+)\.(?P<idx>\d+)\.self_attn\.o_proj$")
    groups: Dict[str, set] = defaultdict(set)
    for n in names:
        m = pat.match(n)
        if m:
            groups[m.group("prefix")].add(int(m.group("idx")))
    if not groups:
        raise UnsupportedArchitecture(
            "auto-détection impossible : aucun sous-module "
            "'*.<i>.self_attn.o_proj' dans le modèle chargé."
        )
    # décodeur principal = conteneur de couches le plus profond (le plus de blocs)
    layers_path = max(groups, key=lambda p: len(groups[p]))

    def _first_present(relatives):
        for rel in relatives:
            if f"{layers_path}.0.{rel}" in nameset:
                return rel
        return relatives[0]

    o_rel = _first_present(["self_attn.o_proj"])
    down_rel = _first_present(["mlp.down_proj", "mlp.c_proj", "feed_forward.down_proj"])

    # embedding = frère du conteneur de couches (model.embed_tokens, ...).
    base = (
        layers_path[: -len(".layers")]
        if layers_path.endswith(".layers")
        else layers_path.rsplit(".", 1)[0]
    )
    embed = f"{base}.embed_tokens"
    if embed not in nameset:
        cands = [n for n in names if n.endswith("embed_tokens")]
        embed = min(cands, key=len) if cands else embed

    mt = model_type or _model_type_from_config(getattr(model, "config", None)) or "auto"
    return ArchSpec(
        model_type=str(mt),
        layers_path=layers_path,
        o_proj=o_rel,
        down_proj=down_rel,
        embed_tokens=embed,
    )


def resolve_against_model(
    model: Any, *, config: Any = None, override: Optional[ArchSpec] = None
) -> ArchSpec:
    """Résout l'``ArchSpec`` en le VALIDANT contre un modèle torch chargé.

    Priorité : ``override`` (intention manuelle, non validée) > registre validé >
    auto-détection. On tente le registre (``resolve``) ; si la famille est inconnue
    OU si son chemin ``o_proj`` couche 0 ne se résout pas sur le modèle réel, on
    retombe sur ``autodetect_arch``. C'est ce qui rend le loader robuste aux
    familles non enregistrées et aux nestings inattendus, sans jamais réécrire le
    détecteur (brief §3.1)."""
    if override is not None:
        return override
    try:
        arch = resolve(config=config)
    except UnsupportedArchitecture:
        return autodetect_arch(model, model_type=_model_type_from_config(config))
    try:
        model.get_submodule(arch.o_proj_path(0))
        return arch
    except Exception:
        return autodetect_arch(model, model_type=arch.model_type)

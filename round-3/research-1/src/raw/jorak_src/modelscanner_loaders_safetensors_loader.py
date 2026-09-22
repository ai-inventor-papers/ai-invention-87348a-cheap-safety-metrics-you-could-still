"""Loader safetensors -> ModelHandle (déquantif fp32). [J1]

Charge un modèle HF (id ou chemin local) en :
  - exposant les poids ``o_proj`` / ``down_proj`` / ``embed_tokens`` déquantifiés
    en **fp32**, layer-par-layer (chargés à la demande pour ne pas exploser la
    RAM sur les gros modèles),
  - fournissant le modèle ``runnable`` pour le plan ACTIVATIONS (J3).

Le 4-bit bitsandbytes est reporté à J10 (garde-fou explicite ci-dessous) :
charger 7B en bnb_4bit sur T4 viendra avec la déquantif des Params4bit.
"""
from __future__ import annotations

import glob
import json
import os
from typing import Optional

from modelscanner.core.types import ModelHandle, Quantization
from modelscanner.loaders import arch_adapter as aa
from modelscanner.loaders.errors import TransformersOutdated, UnsupportedFormat


def _apply_env_workarounds() -> None:
    """Contournements env (cf. experiments/pipeline.py de Jolan), posés AVANT
    tout import torch/transformers lourd."""
    os.environ.setdefault("USE_HUB_KERNELS", "0")       # bug kernels/LayerRepository
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")  # crash OpenMP libgomp/libiomp


class SafetensorsHandle(ModelHandle):
    """ModelHandle adossé à un modèle HF transformers chargé en mémoire."""

    def __init__(
        self,
        *,
        model,
        tokenizer,
        arch: "aa.ArchSpec",
        config,
        quantization: Quantization,
        model_id: str,
    ):
        self._model = model
        self.tokenizer = tokenizer
        self._arch = arch
        self.config = config
        self.quantization = quantization
        self.model_id = model_id
        self.model_type = arch.model_type
        self.n_layers = aa.get_num_layers(config)
        self.hidden_size = aa.get_hidden_size(config)

    # --- accès poids : déquantif fp32, sur CPU, à la demande ---
    def _weight_fp32(self, module_path: str):
        import torch

        module = self._model.get_submodule(module_path)
        w = module.weight
        cls = w.__class__.__name__
        if cls in ("Params4bit", "Int8Params"):  # bnb -> J10
            raise NotImplementedError(
                f"Poids quantifié bnb ({cls}) en {module_path} : la déquantif "
                "4/8-bit est prévue en J10. Charge en fp32/fp16/bf16 pour J1."
            )
        return w.detach().to(torch.float32).cpu()

    def o_proj(self, layer: int):
        return self._weight_fp32(self._arch.o_proj_path(layer))

    def down_proj(self, layer: int):
        return self._weight_fp32(self._arch.down_proj_path(layer))

    def embed_tokens(self):
        return self._weight_fp32(self._arch.embed_path())

    # --- inférence (plan ACTIVATIONS) ---
    @property
    def runnable(self):
        return self._model


# dtype torch -> niveau de quantif "déclaré"
def _quant_from_dtype(dtype) -> Quantization:
    import torch

    return {
        torch.float32: Quantization.FP32,
        torch.float16: Quantization.FP16,
        torch.bfloat16: Quantization.BF16,
    }.get(dtype, Quantization.FP32)


# suffixes de classe d'architecture HF à retirer pour retomber sur le nom de
# config (``Qwen3ForCausalLM`` -> ``Qwen3`` -> ``Qwen3Config`` -> model_type ``qwen3``).
_ARCH_SUFFIXES = (
    "ForCausalLM", "ForConditionalGeneration", "LMHeadModel",
    "ForSequenceClassification", "ForTokenClassification", "PreTrainedModel", "Model",
)


def _read_config_json(local_ref: str) -> Optional[dict]:
    """Lit le config.json brut d'un snapshot local (None si introuvable)."""
    path = os.path.join(local_ref, "config.json") if os.path.isdir(local_ref) else local_ref
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _infer_model_type(raw: Optional[dict]) -> Optional[str]:
    """Déduit le ``model_type`` depuis le champ ``architectures`` du config.json.

    Cas réel (dépôts huihui-ai non standard, ex. ``Qwen3-8B-abliterated``) : le
    config.json a bien ``architectures: ["Qwen3ForCausalLM"]`` mais PAS de clé
    ``model_type`` -> ``AutoConfig`` casse. On retombe sur le nom de classe de
    config (``Qwen3ForCausalLM`` -> ``Qwen3Config``) et on le mappe vers son
    model_type via la table de transformers, avec repli sur ``base.lower()``."""
    if not raw:
        return None
    archs = raw.get("architectures") or []
    if not archs:
        return None
    base = str(archs[0])
    for suf in _ARCH_SUFFIXES:
        if base.endswith(suf) and len(base) > len(suf):
            base = base[: -len(suf)]
            break
    try:
        from transformers.models.auto.configuration_auto import CONFIG_MAPPING_NAMES

        inv = {v: k for k, v in CONFIG_MAPPING_NAMES.items()}  # ClassName -> model_type
        mt = inv.get(f"{base}Config")
        if mt:
            return mt
    except Exception:
        pass
    return base.lower() or None


def _assert_loadable_weights(local_ref: str, model_id: str) -> None:
    """Rejette TÔT un dépôt non chargeable (GGUF-only), avec une erreur claire.

    Jorak/activations ont besoin des tenseurs déquantifiables -> un dépôt qui n'a
    que des blobs ``.gguf`` (llama.cpp) n'est pas scannable. On le dit franchement
    au lieu de laisser ``AutoConfig`` lever une erreur cryptique en aval."""
    if model_id.endswith(".gguf") or local_ref.endswith(".gguf"):
        raise UnsupportedFormat(
            f"{model_id} : fichier GGUF — format non supporté (le scanner a besoin "
            "des poids safetensors/bin déquantifiables). GGUF not supported."
        )
    if not os.path.isdir(local_ref):
        return  # id distant non résolu : on laisse from_pretrained gérer/expliquer
    has_loadable = bool(
        glob.glob(os.path.join(local_ref, "*.safetensors"))
        or glob.glob(os.path.join(local_ref, "*.bin"))
    )
    if has_loadable:
        return
    has_gguf = bool(glob.glob(os.path.join(local_ref, "*.gguf")))
    if has_gguf:
        raise UnsupportedFormat(
            f"{model_id} : dépôt GGUF-only (aucun safetensors/bin) — format non "
            "supporté. Choisir une variante safetensors. GGUF not supported."
        )
    raise UnsupportedFormat(
        f"{model_id} : aucun poids chargeable (ni safetensors, ni .bin) dans le "
        "snapshot local. No loadable weights found."
    )


def _load_config(local_ref: str, model_id: str, trust_remote_code: bool):
    """``AutoConfig`` robuste : répare le ``model_type`` manquant, distingue le
    cas « transformers trop vieux » du cas « format non chargeable ».

    - config.json sans ``model_type`` (huihui) -> on infère depuis ``architectures``
      et on reconstruit la config via ``CONFIG_MAPPING`` (le scan devient possible).
    - ``model_type`` présent mais inconnu de transformers (ex. ``mistral3`` sur une
      box pas à jour) -> ``TransformersOutdated`` (réparable par upgrade)."""
    from transformers import AutoConfig

    try:
        return AutoConfig.from_pretrained(local_ref, trust_remote_code=trust_remote_code)
    except ValueError as e:
        msg = str(e)
        low = msg.lower()

        # Cas A : config.json sans clé model_type -> inférer depuis architectures.
        if "should have a `model_type`" in low or "should have a model_type" in low \
                or "unrecognized model in" in low:
            raw = _read_config_json(local_ref)
            mt = _infer_model_type(raw)
            if mt and raw is not None:
                try:
                    from transformers import CONFIG_MAPPING

                    if mt in CONFIG_MAPPING:
                        fixed = dict(raw)
                        fixed["model_type"] = mt
                        return CONFIG_MAPPING[mt].from_dict(fixed)
                except Exception:
                    pass
            raise UnsupportedFormat(
                f"{model_id} : config.json sans clé `model_type` et model_type "
                f"non inférable depuis architectures={(raw or {}).get('architectures')}. "
                "Dépôt non standard — ajouter `model_type` au config.json."
            ) from e

        # Cas B : model_type connu du dépôt mais inconnu de CETTE transformers.
        if "does not recognize this architecture" in low or "out of date" in low \
                or ("has model type" in low and "does not" in low):
            raise TransformersOutdated(
                f"{model_id} : model_type non reconnu par la version de transformers "
                "installée (trop ancienne). METTRE À JOUR transformers. "
                "transformers out of date."
            ) from e
        raise


# Classes Auto à tenter pour un wrapper multimodal, dans l'ordre :
#  - AutoModelForImageTextToText : garde lm_head + `.generate()` (behavioral OK) ;
#  - AutoModel : dernier recours (décodeur seul -> Jorak/activations, pas de génération).
_MULTIMODAL_AUTO = ("AutoModelForImageTextToText", "AutoModel")


def _causal_lm_unsupported(err: Exception) -> bool:
    """L'erreur dit-elle que la config n'entre PAS dans AutoModelForCausalLM ?

    Cas multimodal (`Mistral3ForConditionalGeneration`, Gemma3, Qwen-VL…) :
    transformers lève « Unrecognized configuration class … for … AutoModelForCausalLM »."""
    return "unrecognized configuration" in str(err).lower()


def _from_pretrained_lm(local_ref: str, load_kwargs: dict):
    """`from_pretrained` robuste : décodeur texte (CausalLM), sinon wrapper multimodal.

    Les modèles multimodaux (`*ForConditionalGeneration` : Mistral3 / Ministral-3,
    Gemma3, Qwen-VL) ne sont pas dans le mapping `AutoModelForCausalLM`. On retombe
    alors sur `AutoModelForImageTextToText` (puis `AutoModel`). Jorak et le plan
    ACTIVATIONS lisent ensuite le décodeur texte NICHÉ (`model.language_model.…`)
    résolu par l'arch_adapter (registre `mistral3`/`gemma3` ou auto-détection).
    NB : requiert un `transformers` assez récent pour connaître la famille (sinon
    `TransformersOutdated` est levé bien avant, à `AutoConfig`)."""
    import transformers
    from transformers import AutoModelForCausalLM

    try:
        return AutoModelForCausalLM.from_pretrained(local_ref, **load_kwargs)
    except (ValueError, KeyError) as e:
        if not _causal_lm_unsupported(e):
            raise          # vraie erreur de chargement, pas un souci de classe Auto
        last = e
    for name in _MULTIMODAL_AUTO:
        Auto = getattr(transformers, name, None)
        if Auto is None:
            continue
        try:
            return Auto.from_pretrained(local_ref, **load_kwargs)
        except Exception as e:  # noqa: BLE001 - on tente la classe Auto suivante
            last = e
    raise UnsupportedFormat(
        f"chargement impossible (ni CausalLM ni multimodal) : {last}"
    ) from last


def load_model(
    model_id: str,
    *,
    quant: Optional[Quantization] = None,
    device: str = "auto",
    dtype=None,
    arch_override: "Optional[aa.ArchSpec]" = None,
    trust_remote_code: bool = False,
) -> ModelHandle:
    """Charge `model_id` (HF id ou chemin local) en ModelHandle.

    Args:
        model_id: id Hugging Face ou chemin local.
        quant: BNB_4BIT/BNB_8BIT pour charger un gros modèle compressé (J10).
        device: "auto" | "cuda" | "cpu".
        dtype: dtype torch de chargement (défaut: fp32 sur CPU, bf16 sur GPU).
        arch_override: ArchSpec manuel si l'auto-détection échoue.
        trust_remote_code: pour les archis à code custom.
    """
    _apply_env_workarounds()
    import torch
    from transformers import AutoTokenizer

    from modelscanner.loaders.cache_resolve import resolve_model_ref

    # id HF -> snapshot local (cache HF puis cache vLLM), sans réseau ni certificat.
    # `model_id` (l'id logique) reste affiché ; `local_ref` sert au chargement.
    local_ref = resolve_model_ref(model_id)

    # garde-fou format : dépôt GGUF-only / sans poids chargeables -> erreur claire.
    _assert_loadable_weights(local_ref, model_id)

    # AutoConfig robuste : répare le model_type manquant (huihui) et distingue
    # « transformers trop vieux » (mistral3) du « format non chargeable ».
    config = _load_config(local_ref, model_id, trust_remote_code)
    # NB : la résolution d'architecture est faite APRÈS chargement (voir plus bas,
    # `resolve_against_model`) pour valider/auto-corriger les chemins de poids contre
    # le modèle réel — robuste aux familles non enregistrées (ex. `ministral`,
    # `mistral3`) et aux nestings multimodaux inattendus.

    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    if dtype is None:
        # CPU : charger dans le dtype NATIF du checkpoint ("auto", bf16 pour Qwen)
        # au lieu de forcer fp32. Forcer fp32 DOUBLE la RAM (~6 Go résident + pic de
        # conversion ~9 Go) sans gagner de précision — le checkpoint est déjà bf16 —
        # et fait tuer le process par systemd-oomd (pression mémoire). JORAK upcaste
        # chaque couche en fp32 à la volée (_weight_fp32) -> résultats identiques.
        # GPU : bf16 comme avant.
        dtype = "auto" if device == "cpu" else torch.bfloat16

    # on passe la config DÉJÀ résolue (peut être reconstruite avec un model_type
    # inféré pour les dépôts huihui) -> from_pretrained ne re-casse pas dessus.
    load_kwargs = dict(trust_remote_code=trust_remote_code, config=config)
    # transformers récent : `dtype=` (torch_dtype déprécié, cf. note de Jolan).
    load_kwargs["dtype"] = dtype
    # évite la copie transitoire au chargement (pic RAM) -> tient dans 15 Go.
    load_kwargs["low_cpu_mem_usage"] = True

    if quant in (Quantization.BNB_4BIT, Quantization.BNB_8BIT):
        # Chargement compressé : nécessite bitsandbytes + GPU. Câblé en J10.
        from transformers import BitsAndBytesConfig

        load_kwargs["device_map"] = "auto"
        load_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=(quant == Quantization.BNB_4BIT),
            load_in_8bit=(quant == Quantization.BNB_8BIT),
            bnb_4bit_compute_dtype=torch.float16,
        )
        quantization = quant
    else:
        load_kwargs["device_map"] = device
        quantization = None  # déterminé après chargement (dtype réel, ex. bf16 via "auto")

    # CausalLM, avec repli multimodal (Mistral3/Ministral-3, Gemma3, Qwen-VL).
    model = _from_pretrained_lm(local_ref, load_kwargs)
    model.eval()
    # résolution d'archi VALIDÉE contre le modèle chargé : registre si connu + chemins
    # vérifiés, sinon auto-détection des chemins de poids (o_proj/down_proj/embed).
    arch = aa.resolve_against_model(model, config=config, override=arch_override)
    if quantization is None:
        quantization = _quant_from_dtype(model.dtype)
    tokenizer = AutoTokenizer.from_pretrained(local_ref, trust_remote_code=trust_remote_code)

    return SafetensorsHandle(
        model=model,
        tokenizer=tokenizer,
        arch=arch,
        config=config,
        quantization=quantization,
        model_id=model_id,
    )

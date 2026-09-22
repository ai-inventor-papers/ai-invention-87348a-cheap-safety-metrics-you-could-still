"""Chat templates standardisés PAR FAMILLE. [J2]

Sinon on mesure du bruit de formatage, pas du refus (brief §3.8). Le prompt
doit se terminer EXACTEMENT à la position de génération du 1er token de réponse
(`add_generation_prompt=True`) : c'est là qu'on lit le hidden state (§3.5).

On réutilise le chat template natif du tokenizer (robuste, exact pour chaque
famille) et on ne gère ici que les *quirks* :
  - Gemma n'a pas de rôle `system` -> on le replie dans le tour `user`.
  - Qwen3 peut injecter `<think>` -> on force `enable_thinking=False` pour une
    position de refus propre.
"""
from __future__ import annotations

from typing import List

# Familles sans rôle `system` dans leur chat template.
_NO_SYSTEM_FAMILIES = {"gemma", "gemma2", "gemma3", "gemma3_text"}
# Familles à mode "thinking" qu'il faut désactiver.
_THINKING_FAMILIES = {"qwen3", "qwen3_moe"}


def supports_system_role(model_type: str) -> bool:
    return model_type not in _NO_SYSTEM_FAMILIES


def build_messages(text: str, model_type: str, system: str | None = None) -> List[dict]:
    """Construit la liste de messages, en gérant l'absence de rôle system."""
    messages: List[dict] = []
    if system:
        if supports_system_role(model_type):
            messages.append({"role": "system", "content": system})
        else:  # Gemma & co : on replie le system dans le user
            text = f"{system}\n\n{text}"
    messages.append({"role": "user", "content": text})
    return messages


def format_prompt(
    text: str,
    model_type: str,
    *,
    tokenizer,
    system: str | None = None,
) -> str:
    """Rend `text` au format chat de la famille, prêt pour la génération
    (`add_generation_prompt=True`). Renvoie une chaîne (tokenize=False)."""
    if tokenizer is None:
        raise ValueError("Un tokenizer (porteur du chat template) est requis.")
    messages = build_messages(text, model_type, system)
    kwargs = dict(tokenize=False, add_generation_prompt=True)
    if model_type in _THINKING_FAMILIES:
        kwargs["enable_thinking"] = False
    return tokenizer.apply_chat_template(messages, **kwargs)

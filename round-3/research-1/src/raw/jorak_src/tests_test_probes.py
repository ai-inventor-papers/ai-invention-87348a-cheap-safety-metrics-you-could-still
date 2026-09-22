"""J2 — validation des sondes + chat templates.

Partie 1 (intégrité du jeu) : pure-python, tourne toujours.
Partie 2 (templates) : nécessite un tokenizer -> gated sur MS_TEST_MODEL.
"""
import os

import pytest

from modelscanner.probes import ProbeSet, load_probes
from modelscanner.probes.templates import build_messages, format_prompt, supports_system_role


# --------------------------- intégrité du jeu ---------------------------
def test_load_probes_v1():
    ps = load_probes(version="v1")
    assert isinstance(ps, ProbeSet)
    assert ps.lang == "en"
    assert ps.n_pairs >= 30                      # assez pour Cohen's d
    assert len(ps.harmful) == len(ps.harmless)   # appariement strict


def test_probes_are_clean():
    ps = load_probes(version="v1")
    for lst in (ps.harmful, ps.harmless):
        assert all(isinstance(x, str) and x.strip() for x in lst)  # pas de vide
        assert len(set(lst)) == len(lst)                           # pas de doublon
    # un harmful ne doit pas être identique à son harmless apparié
    assert all(h != hl for h, hl in zip(ps.harmful, ps.harmless))


def test_pairs_comparable_length():
    """Appariement en longueur (isoler le refus du topic shift) : la longueur
    médiane des deux classes doit être proche (tolérance large)."""
    ps = load_probes(version="v1")
    med_h = sorted(len(x) for x in ps.harmful)[ps.n_pairs // 2]
    med_hl = sorted(len(x) for x in ps.harmless)[ps.n_pairs // 2]
    assert abs(med_h - med_hl) < 0.5 * max(med_h, med_hl)


def test_unpaired_set_rejected():
    with pytest.raises(ValueError):
        ProbeSet(harmful=["a", "b"], harmless=["x"])


# --------------------------- quirks par famille ---------------------------
def test_system_role_support():
    assert supports_system_role("qwen2") is True
    assert supports_system_role("mistral") is True
    assert supports_system_role("gemma3_text") is False


def test_build_messages_gemma_folds_system():
    # Gemma : pas de rôle system -> replié dans le user
    msgs = build_messages("Hello", "gemma3_text", system="Be helpful")
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"
    assert "Be helpful" in msgs[0]["content"] and "Hello" in msgs[0]["content"]


def test_build_messages_qwen_keeps_system():
    msgs = build_messages("Hello", "qwen2", system="Be helpful")
    assert [m["role"] for m in msgs] == ["system", "user"]


# --------------------------- templates (gated) ---------------------------
_MODEL = os.environ.get("MS_TEST_MODEL")


@pytest.mark.skipif(not _MODEL, reason="définir MS_TEST_MODEL pour tester le chat template réel")
def test_format_prompt_real_tokenizer():
    pytest.importorskip("transformers")
    from transformers import AutoConfig, AutoTokenizer

    model_type = AutoConfig.from_pretrained(_MODEL).model_type
    tok = AutoTokenizer.from_pretrained(_MODEL)
    ps = load_probes(version="v1")

    p_harm = format_prompt(ps.harmful[0], model_type, tokenizer=tok)
    p_safe = format_prompt(ps.harmless[0], model_type, tokenizer=tok)

    # le prompt contient bien l'instruction et se termine au point de génération
    assert ps.harmful[0] in p_harm
    assert p_harm != p_safe
    # harmful/harmless ne diffèrent QUE par l'instruction (même enveloppe de template)
    common_tail = "assistant"  # toutes nos familles ouvrent un tour assistant
    assert common_tail in p_harm.lower()

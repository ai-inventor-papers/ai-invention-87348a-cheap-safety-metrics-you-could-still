"""SEAL GUARD: the ONLY place from_pretrained / snapshot_download may be called is load_model()."""
from __future__ import annotations

from pathlib import Path

W = Path(__file__).resolve().parent.parent
LOADED = W / "results" / "loaded_repos.txt"
SEALED_TOKENS = ("granite", "stablelm")


class SealedRepoError(RuntimeError):
    pass


def _check_str(s: str, repo: str, what: str) -> None:
    low = s.lower()
    if any(t in low for t in SEALED_TOKENS) or low.startswith(("ibm-granite/", "stabilityai/")):
        raise SealedRepoError(f"{repo}: sealed token in {what}: {s}")


def assert_not_sealed(repo: str, card_base_model: object | None = None, check_hub: bool = True) -> None:
    _check_str(repo, repo, "repo id")
    bm = card_base_model
    if bm is None and check_hub:
        from huggingface_hub import HfApi
        info = HfApi().model_info(repo)
        cd = info.card_data
        bm = (cd.get("base_model") if cd is not None else None)
    for b in ([bm] if isinstance(bm, str) else (bm or [])):
        _check_str(str(b), repo, "card base_model")


def load_model(repo: str, dtype=None, **kw):
    """Guarded loader: returns (model, tokenizer)."""
    assert_not_sealed(repo)
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(repo)
    model = AutoModelForCausalLM.from_pretrained(repo, dtype=dtype or torch.bfloat16, low_cpu_mem_usage=True, **kw)
    model.eval()
    LOADED.parent.mkdir(parents=True, exist_ok=True)
    with LOADED.open("a") as fh:
        fh.write(repo + "\n")
    return model, tok


def test_guard() -> None:
    for bad in ("ibm-granite/granite-3.3-2b-instruct", "stabilityai/stablelm-zephyr-3b", "someone/Granite-derivative"):
        try:
            assert_not_sealed(bad, check_hub=False)
        except SealedRepoError:
            continue
        raise AssertionError(f"guard did not raise on {bad}")
    try:  # derivative whose CARD names a granite base
        assert_not_sealed("someone/innocent-name", card_base_model=["ibm-granite/granite-3.3-2b-instruct"], check_hub=False)
        raise AssertionError("guard did not raise on card base_model")
    except SealedRepoError:
        pass
    # real hub derivative (Damien420 granite abliterated) -> card or id must trip
    try:
        assert_not_sealed("Damien420/granite-3.2-2b-instruct-abliterated", check_hub=False)
        raise AssertionError("guard missed granite derivative")
    except SealedRepoError:
        pass
    assert_not_sealed("Qwen/Qwen3-0.6B", card_base_model="Qwen/Qwen3-0.6B-Base", check_hub=False)
    print("guard tests passed")


if __name__ == "__main__":
    test_guard()

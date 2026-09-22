"""J1 — validation du loader safetensors sur un vrai modèle.

Reste SKIP par défaut (suite légère/offline). Pour valider J1, désigne un
modèle via l'env ``MS_TEST_MODEL`` :

    MS_TEST_MODEL=Qwen/Qwen2.5-0.5B-Instruct pytest tests/test_loader.py -v

Qwen2.5-0.5B-Instruct est libre (non gated) et minuscule -> cible de validation.
"""
import os

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")

MODEL = os.environ.get("MS_TEST_MODEL")
pytestmark = pytest.mark.skipif(
    not MODEL, reason="définir MS_TEST_MODEL=<hf-id|chemin> pour valider J1"
)


@pytest.fixture(scope="module")
def handle():
    from modelscanner.loaders import load_model

    return load_model(MODEL, device="cpu", dtype=torch.float32)


def test_handle_metadata(handle):
    from modelscanner.loaders import arch_adapter as aa

    assert handle.n_layers == aa.get_num_layers(handle.config)
    assert handle.hidden_size == aa.get_hidden_size(handle.config)
    assert handle.model_type  # auto-détecté
    assert handle.supports_activations  # modèle runnable dispo


def test_weights_fp32_and_shapes(handle):
    h = handle.hidden_size
    o = handle.o_proj(0)
    d = handle.down_proj(0)
    e = handle.embed_tokens()

    # déquantif fp32 sur CPU
    assert o.dtype == torch.float32 and o.device.type == "cpu"
    # o_proj écrit dans le residual stream -> sortie de dim hidden
    assert o.shape[0] == h
    # down_proj : [hidden, d_ff]
    assert d.shape[0] == h and d.shape[1] > h
    # embed : [vocab, hidden]
    assert e.shape[1] == h

    for t in (o, d, e):
        assert torch.isfinite(t).all()


def test_all_layer_paths_resolve(handle):
    """Le mapping arch_adapter doit couvrir TOUTES les couches sans trou."""
    for i in range(handle.n_layers):
        assert handle.o_proj(i).shape[0] == handle.hidden_size
        assert handle.down_proj(i).shape[0] == handle.hidden_size

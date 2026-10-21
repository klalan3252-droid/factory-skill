import pytest

from factory.config import load_config
from factory.llm import LLMError, get_chat_model


@pytest.fixture
def spy(monkeypatch):
    calls = []
    sentinel = object()

    def fake(*args, **kwargs):
        calls.append((args, kwargs))
        return sentinel

    monkeypatch.setattr("langchain.chat_models.init_chat_model", fake)
    import factory.llm
    monkeypatch.setattr(factory.llm, "init_chat_model", fake, raising=False)
    return calls, sentinel


@pytest.mark.parametrize("provider,model", [
    ("anthropic", "claude-x"), ("openai", "gpt-x"), ("google_genai", "gemini-x")])
def test_env_only_switches_provider(spy, base_env, provider, model):
    calls, sentinel = spy
    cfg = load_config({**base_env, "FACTORY_LLM_PROVIDER": provider, "FACTORY_LLM_MODEL": model})
    assert get_chat_model(cfg) is sentinel
    args, kwargs = calls[-1]
    assert model in args or kwargs.get("model") == model
    assert kwargs.get("model_provider") == provider


def test_unknown_provider(spy, base_env):
    cfg = load_config({**base_env, "FACTORY_LLM_PROVIDER": "nonsense"})
    with pytest.raises(LLMError, match="nonsense"):
        get_chat_model(cfg)
    assert not spy[0]


@pytest.mark.parametrize("drop", ["FACTORY_LLM_PROVIDER", "FACTORY_LLM_MODEL"])
def test_unconfigured(spy, base_env, drop):
    del base_env[drop]
    with pytest.raises(LLMError):
        get_chat_model(load_config(base_env))


def test_init_failure_wrapped_without_secret(monkeypatch, base_env):
    def boom(*a, **k):
        raise ImportError("pip install langchain-anthropic")
    monkeypatch.setattr("langchain.chat_models.init_chat_model", boom)
    import factory.llm
    monkeypatch.setattr(factory.llm, "init_chat_model", boom, raising=False)
    with pytest.raises(LLMError) as e:
        get_chat_model(load_config(base_env))
    assert "ghp_SECRET" not in str(e.value)

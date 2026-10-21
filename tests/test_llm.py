import pytest

from factory_agents.config import ConfigError
from factory_agents.llm import ChatModelProvider, LLMProvider, ProviderError


def test_unknown_provider_gives_provider_error():
    with pytest.raises(ProviderError) as e:
        ChatModelProvider("definitelynotreal:foo").get_chat_model()
    assert "definitelynotreal" in str(e.value)


def test_missing_model_string_is_config_error():
    with pytest.raises(ConfigError):
        ChatModelProvider(None)


def test_provider_calls_init_chat_model(monkeypatch):
    seen = {}

    def fake_init(model, model_provider=None, **kw):
        seen.update(model=model, provider=model_provider)
        return "MODEL"

    monkeypatch.setattr("factory_agents.llm.init_chat_model", fake_init)
    p = ChatModelProvider("anthropic:claude-x")
    assert p.get_chat_model() == "MODEL"
    assert seen == {"model": "claude-x", "provider": "anthropic"}
    assert isinstance(p, LLMProvider)


def test_import_error_wrapped(monkeypatch):
    def boom(*a, **k):
        raise ImportError("no package")

    monkeypatch.setattr("factory_agents.llm.init_chat_model", boom)
    with pytest.raises(ProviderError):
        ChatModelProvider("anthropic:x").get_chat_model()

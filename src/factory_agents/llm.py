"""Thin LLM provider interface backed by LangChain's init_chat_model."""

from typing import Protocol, runtime_checkable

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

from factory_agents.config import ConfigError


class ProviderError(Exception):
    """The chat model provider is unknown or not installed/configured."""


def parse_model(spec: str) -> tuple[str, str]:
    """Split 'provider:model' on the first colon."""
    provider, sep, model = (spec or "").partition(":")
    if not sep or not provider.strip() or not model.strip():
        raise ConfigError(f"model must look like 'provider:model', got {spec!r}")
    return provider.strip(), model.strip()


@runtime_checkable
class LLMProvider(Protocol):
    def get_chat_model(self) -> BaseChatModel: ...


class ChatModelProvider:
    def __init__(self, spec: str | None):
        if not spec:
            raise ConfigError("no model given: use --model or FACTORY_MODEL ('provider:model')")
        self.provider, self.model = parse_model(spec)

    def get_chat_model(self) -> BaseChatModel:
        try:
            return init_chat_model(self.model, model_provider=self.provider)
        except (ImportError, ValueError) as e:
            raise ProviderError(
                f"cannot load provider {self.provider!r} (model {self.model!r}): {e}"
            ) from e

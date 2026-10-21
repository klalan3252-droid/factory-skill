"""LLM factory: a LangChain chat model chosen purely by configuration."""
from __future__ import annotations

from langchain.chat_models import init_chat_model

from .config import Config, redact

SUPPORTED_PROVIDERS = ("anthropic", "openai", "google_genai")


class LLMError(Exception):
    """Raised when the chat model cannot be configured or created."""


def get_chat_model(config: Config):
    provider, model = config.llm_provider, config.llm_model
    if not provider:
        raise LLMError("FACTORY_LLM_PROVIDER is not set "
                       f"(supported: {', '.join(SUPPORTED_PROVIDERS)})")
    if not model:
        raise LLMError("FACTORY_LLM_MODEL is not set")
    if provider not in SUPPORTED_PROVIDERS:
        raise LLMError(f"unknown LLM provider {provider!r} "
                       f"(supported: {', '.join(SUPPORTED_PROVIDERS)})")
    try:
        return init_chat_model(model, model_provider=provider)
    except Exception as exc:
        msg = redact(str(exc), config.github_token)
        raise LLMError(f"could not initialise {provider} model {model!r}: {msg}") from None

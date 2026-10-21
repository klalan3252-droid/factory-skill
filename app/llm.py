import os

DEFAULT_MODEL = "claude-sonnet-4-5"


def get_llm():
    """Build the default chat model lazily so importing never requires the API key."""
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL),
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
    )

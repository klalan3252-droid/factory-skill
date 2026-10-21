from pathlib import Path

import pytest

README = (Path(__file__).resolve().parent.parent / "README.md").read_text()


@pytest.mark.parametrize("name", [
    "GITHUB_TOKEN", "FACTORY_REPO", "FACTORY_LABEL", "FACTORY_LLM_PROVIDER", "FACTORY_LLM_MODEL",
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY", "FACTORY_DRY_RUN",
    "FACTORY_POLL_INTERVAL", "FACTORY_TEST_COMMAND"])
def test_env_var_documented(name):
    assert name in README


@pytest.mark.parametrize("text", ["pip install -e", "run --once", "--dry-run", "--issue", "--interval"])
def test_usage_documented(text):
    assert text in README


def test_safety_section():
    low = README.lower()
    assert "safety" in low and "default branch" in low

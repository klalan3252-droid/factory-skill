import pytest

from factory_agents.config import Config, ConfigError
from factory_agents.llm import parse_model


def test_parse_model_valid():
    assert parse_model("anthropic:claude-x") == ("anthropic", "claude-x")


def test_parse_model_keeps_extra_colons_in_model():
    assert parse_model("ollama:llama3:8b") == ("ollama", "llama3:8b")


@pytest.mark.parametrize("bad", ["", "nocolon", ":model", "provider:", ":"])
def test_parse_model_invalid(bad):
    with pytest.raises(ConfigError):
        parse_model(bad)


def test_defaults(tmp_path):
    cfg = Config.load(repo=tmp_path, request="x", env={})
    assert cfg.test_cmd == "pytest"
    assert cfg.max_iterations == 3
    assert cfg.push is False
    assert cfg.model is None


def test_env_overrides_defaults(tmp_path):
    env = {"FACTORY_MODEL": "openai:gpt", "FACTORY_TEST_CMD": "make t", "FACTORY_MAX_ITERATIONS": "5"}
    cfg = Config.load(repo=tmp_path, request="x", env=env)
    assert (cfg.model, cfg.test_cmd, cfg.max_iterations) == ("openai:gpt", "make t", 5)


def test_cli_overrides_env(tmp_path):
    env = {"FACTORY_MODEL": "openai:gpt", "FACTORY_TEST_CMD": "make t", "FACTORY_MAX_ITERATIONS": "5"}
    cfg = Config.load(
        repo=tmp_path, request="x", model="anthropic:c", test_cmd="tox", max_iterations=2, env=env
    )
    assert (cfg.model, cfg.test_cmd, cfg.max_iterations) == ("anthropic:c", "tox", 2)


@pytest.mark.parametrize("bad", ["0", "abc", "-1"])
def test_bad_max_iterations(tmp_path, bad):
    with pytest.raises(ConfigError):
        Config.load(repo=tmp_path, request="x", env={"FACTORY_MAX_ITERATIONS": bad})

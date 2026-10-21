import dataclasses

import pytest

from factory.config import Config, ConfigError, load_config, redact
from .conftest import TOKEN


def test_loads_values_and_defaults(base_env):
    c = load_config(base_env)
    assert c.github_token == TOKEN
    assert c.repo == "acme/widgets"
    assert c.label == "factory"
    assert c.llm_provider == "anthropic" and c.llm_model == "claude-test"
    assert c.dry_run is False
    assert c.test_command == "pytest"
    assert isinstance(c.poll_interval, (int, float)) and c.poll_interval > 0


def test_overrides(base_env):
    c = load_config({**base_env, "FACTORY_LABEL": "bot", "FACTORY_DRY_RUN": "true",
                     "FACTORY_POLL_INTERVAL": "12", "FACTORY_TEST_COMMAND": "make test"})
    assert (c.label, c.dry_run, c.poll_interval, c.test_command) == ("bot", True, 12, "make test")


@pytest.mark.parametrize("val,exp", [("1", True), ("true", True), ("0", False), ("false", False), ("", False)])
def test_dry_run_parsing(base_env, val, exp):
    assert load_config({**base_env, "FACTORY_DRY_RUN": val}).dry_run is exp


@pytest.mark.parametrize("missing", ["GITHUB_TOKEN", "FACTORY_REPO"])
def test_missing_required(base_env, missing):
    del base_env[missing]
    with pytest.raises(ConfigError) as e:
        load_config(base_env)
    assert missing in str(e.value)


@pytest.mark.parametrize("repo", ["widgets", "a/b/c", "/x", "x/"])
def test_invalid_repo(base_env, repo):
    with pytest.raises(ConfigError):
        load_config({**base_env, "FACTORY_REPO": repo})


def test_token_never_in_repr_or_str(base_env):
    c = load_config(base_env)
    assert TOKEN not in repr(c) and TOKEN not in str(c)
    assert dataclasses.is_dataclass(c)
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.repo = "x/y"


def test_redact():
    assert TOKEN not in redact(f"fatal: https://x:{TOKEN}@github.com failed", TOKEN)

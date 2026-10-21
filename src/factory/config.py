"""Configuration loaded from environment variables."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Mapping

_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_TRUE = {"1", "true", "yes", "on"}


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    github_token: str = field(repr=False)
    repo: str
    label: str = "factory"
    llm_provider: str = ""
    llm_model: str = ""
    dry_run: bool = False
    poll_interval: float = 60.0
    test_command: str = "pytest"


def redact(text: str, *secrets: str | None) -> str:
    """Replace every secret occurring in `text` with a placeholder."""
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


def load_config(env: Mapping[str, str]) -> Config:
    token = env.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise ConfigError("GITHUB_TOKEN is not set")
    repo = env.get("FACTORY_REPO", "").strip()
    if not repo:
        raise ConfigError("FACTORY_REPO is not set (expected owner/name)")
    if not _REPO_RE.match(repo):
        raise ConfigError(f"FACTORY_REPO must look like owner/name, got {repo!r}")
    try:
        interval = float(env.get("FACTORY_POLL_INTERVAL") or 60)
    except ValueError:
        raise ConfigError("FACTORY_POLL_INTERVAL must be a number of seconds") from None
    if interval <= 0:
        raise ConfigError("FACTORY_POLL_INTERVAL must be positive")
    return Config(
        github_token=token,
        repo=repo,
        label=env.get("FACTORY_LABEL") or "factory",
        llm_provider=env.get("FACTORY_LLM_PROVIDER", "").strip(),
        llm_model=env.get("FACTORY_LLM_MODEL", "").strip(),
        dry_run=env.get("FACTORY_DRY_RUN", "").strip().lower() in _TRUE,
        poll_interval=interval,
        test_command=env.get("FACTORY_TEST_COMMAND") or "pytest",
    )

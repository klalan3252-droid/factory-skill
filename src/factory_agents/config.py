"""Run configuration. Precedence: explicit (CLI) values > environment > defaults."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TEST_CMD = "pytest"
DEFAULT_MAX_ITERATIONS = 3
DEFAULT_TEST_TIMEOUT = 600


class ConfigError(Exception):
    """Invalid or missing configuration."""


@dataclass(frozen=True)
class Config:
    repo: Path
    request: str
    model: str | None = None
    test_cmd: str = DEFAULT_TEST_CMD
    max_iterations: int = DEFAULT_MAX_ITERATIONS
    test_timeout: int = DEFAULT_TEST_TIMEOUT
    push: bool = False

    @classmethod
    def load(
        cls,
        repo: Path,
        request: str,
        model: str | None = None,
        test_cmd: str | None = None,
        max_iterations: int | None = None,
        push: bool = False,
        env: Mapping[str, str] | None = None,
    ) -> "Config":
        env = os.environ if env is None else env
        if max_iterations is None:
            raw = env.get("FACTORY_MAX_ITERATIONS")
            if raw is None:
                max_iterations = DEFAULT_MAX_ITERATIONS
            else:
                try:
                    max_iterations = int(raw)
                except ValueError:
                    raise ConfigError(f"FACTORY_MAX_ITERATIONS must be an integer, got {raw!r}")
        if max_iterations < 1:
            raise ConfigError(f"max iterations must be >= 1, got {max_iterations}")
        return cls(
            repo=Path(repo),
            request=request,
            model=model or env.get("FACTORY_MODEL") or None,
            test_cmd=test_cmd or env.get("FACTORY_TEST_CMD") or DEFAULT_TEST_CMD,
            max_iterations=max_iterations,
            push=push,
        )

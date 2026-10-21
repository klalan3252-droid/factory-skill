"""Test step: run the configured test command in the clone."""
from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

MAX_OUTPUT = 20000


@dataclass
class TestResult:
    __test__ = False  # not a pytest class

    passed: bool
    exit_code: int
    output: str


def _truncate(text: str) -> str:
    if len(text) <= MAX_OUTPUT:
        return text
    return "[...truncated...]\n" + text[-MAX_OUTPUT:]


def run_tests(command: str, cwd: Path, timeout: float = 600) -> TestResult:
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
    try:
        proc = subprocess.run(shlex.split(command), cwd=cwd, env=env, capture_output=True,
                              text=True, errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return TestResult(False, -1, f"test command timed out after {timeout}s")
    except (OSError, ValueError) as exc:
        return TestResult(False, 127, f"could not run test command: {exc}")
    return TestResult(proc.returncode == 0, proc.returncode,
                      _truncate(proc.stdout + proc.stderr))

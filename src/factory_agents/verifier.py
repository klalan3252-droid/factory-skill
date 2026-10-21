"""Runs the target repo's test command (no shell, with a timeout)."""

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

MAX_OUTPUT = 20_000


@dataclass(frozen=True)
class TestResult:
    __test__ = False  # not a pytest test class

    passed: bool
    output: str
    timed_out: bool = False


def _truncate(text: str) -> str:
    if len(text) <= MAX_OUTPUT:
        return text
    return text[: MAX_OUTPUT // 2] + "\n...[truncated]...\n" + text[-MAX_OUTPUT // 2 :]


def _text(data: str | bytes | None) -> str:
    if isinstance(data, bytes):
        return data.decode(errors="replace")
    return data or ""


def run_tests(cmd: str, cwd: Path, timeout: int) -> TestResult:
    try:
        argv = shlex.split(cmd)
        if not argv:
            return TestResult(False, "empty test command")
        proc = subprocess.run(
            argv, cwd=cwd, shell=False, capture_output=True, text=True, errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        out = _text(e.stdout) + _text(e.stderr)
        return TestResult(False, _truncate(f"{out}\nTimed out after {timeout}s"), timed_out=True)
    except (OSError, ValueError) as e:
        return TestResult(False, f"could not run test command {cmd!r}: {e}")
    return TestResult(proc.returncode == 0, _truncate(proc.stdout + proc.stderr))

"""PR step: build the pull request title and body."""
from __future__ import annotations

from .testing import TestResult


def build_title(issue: dict) -> str:
    return f"{issue['title']} (#{issue['number']})"


def build_body(issue_number: int, plan: str, test_result: TestResult) -> str:
    status = "passed" if test_result.passed else f"FAILED (exit code {test_result.exit_code})"
    return (f"Closes #{issue_number}\n\n## Plan\n{plan}\n\n## Test result\n"
            f"Tests {status}.\n\n```\n{test_result.output.strip()[-3000:]}\n```\n\n"
            "_Opened by the factory agent._\n")

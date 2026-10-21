"""Triage step: decide whether an issue is suitable for automation."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Verdict(BaseModel):
    verdict: Literal["suitable", "reject", "skip"]
    reason: str


SYSTEM = ("You triage GitHub issues for an autonomous coding agent. Answer 'suitable' if the "
          "issue is a clear, self-contained code change; 'reject' if it is invalid or unsafe; "
          "'skip' if it needs human input or is too large. Give a short reason.")


def issue_text(issue: dict) -> str:
    return f"Title: {issue['title']}\n\n{issue.get('body') or ''}"


def triage(llm, issue: dict) -> Verdict:
    return llm.with_structured_output(Verdict).invoke(
        [("system", SYSTEM), ("human", issue_text(issue))])

"""Spec step: turn an issue into an implementation plan."""
from __future__ import annotations

from pydantic import BaseModel

from .triage import issue_text


class Spec(BaseModel):
    plan: str


SYSTEM = ("You are a senior engineer. Write a concise, step-by-step implementation plan "
          "for the issue, naming the files to change.")


def make_spec(llm, issue: dict) -> str:
    return llm.with_structured_output(Spec).invoke(
        [("system", SYSTEM), ("human", issue_text(issue))]).plan

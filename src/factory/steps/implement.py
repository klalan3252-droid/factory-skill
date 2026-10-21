"""Implement step: ask the model for file edits."""
from __future__ import annotations

from pydantic import BaseModel

from .triage import issue_text


class FileEdit(BaseModel):
    path: str
    content: str


class Edits(BaseModel):
    edits: list[FileEdit]


SYSTEM = ("You implement the plan as complete file contents. Return every file to create or "
          "overwrite as a repository-relative path plus its full new content. Never touch .git.")


def propose_edits(llm, issue: dict, plan: str, repo_files: list[str]) -> list[FileEdit]:
    files = "\n".join(repo_files[:500])
    prompt = f"{issue_text(issue)}\n\nPlan:\n{plan}\n\nExisting files:\n{files}"
    return llm.with_structured_output(Edits).invoke(
        [("system", SYSTEM), ("human", prompt)]).edits

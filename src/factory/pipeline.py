"""Pipeline orchestrator: triage -> spec -> implement -> test -> PR."""
from __future__ import annotations

import logging
import tempfile
from contextlib import nullcontext
from pathlib import Path
from typing import Callable

from . import gitops
from .config import Config, redact
from .steps import implement, pr, spec, triage
from .steps.testing import run_tests

log = logging.getLogger(__name__)

LABEL_IN_PROGRESS = "in-progress"
LABEL_DONE = "factory-done"
LABEL_REJECTED = "factory-rejected"
PROCESSED_LABELS = {LABEL_IN_PROGRESS, LABEL_DONE, LABEL_REJECTED}


def _write(config: Config, description: str, fn: Callable, *args, **kwargs):
    """Perform a GitHub write, or only log it in dry-run mode."""
    if config.dry_run:
        log.info("[dry-run] would %s", description)
        return None
    return fn(*args, **kwargs)


def process_issue(issue: dict, config: Config, gh, llm,
                  workdir_factory: Callable[[], Path] | None = None) -> None:
    number = issue["number"]
    default_branch = gh.get_default_branch()

    verdict = triage.triage(llm, issue)
    log.info("issue #%s triage: %s (%s)", number, verdict.verdict, verdict.reason)
    if verdict.verdict != "suitable":
        _write(config, f"comment on #{number} and label it {LABEL_REJECTED}",
               _comment_and_label, gh, number,
               f"Factory triage: {verdict.verdict}. {verdict.reason}", LABEL_REJECTED)
        return

    _write(config, f"label #{number} {LABEL_IN_PROGRESS}", gh.add_label, number, LABEL_IN_PROGRESS)
    plan = spec.make_spec(llm, issue)

    ctx = nullcontext(None) if workdir_factory else tempfile.TemporaryDirectory(prefix="factory-")
    with ctx as tmp:
        workdir = Path(workdir_factory() if workdir_factory else tmp)
        repo = workdir / "repo"
        gitops.clone(gh.clone_url, repo, token=config.github_token)
        branch = gitops.branch_name(number, issue["title"])
        gitops.checkout_new_branch(repo, branch)
        edits = implement.propose_edits(llm, issue, plan, gitops.list_files(repo))
        if not edits:
            _write(config, f"comment on #{number} that no changes were proposed",
                   gh.comment, number, "Factory: the model proposed no changes.")
            return
        gitops.apply_edits(repo, edits)
        gitops.commit_all(repo, f"{issue['title']} (#{number})", default_branch=default_branch)

        result = run_tests(config.test_command, repo)
        log.info("issue #%s tests %s", number, "passed" if result.passed else "failed")

        gitops.push(repo, branch, default_branch, dry_run=config.dry_run,
                    token=config.github_token)

    draft = not result.passed
    title = pr.build_title(issue)
    body = pr.build_body(number, plan, result)
    created = _write(config, f"open {'draft ' if draft else ''}pull request {branch} -> "
                     f"{default_branch} for #{number}",
                     gh.create_pr, title, body, branch, default_branch, draft=draft)
    if draft:
        _write(config, f"comment on #{number} that tests failed",
               gh.comment, number, f"Factory: tests failed; opened a draft PR for {branch}.")
    _write(config, f"label #{number} {LABEL_DONE}", gh.add_label, number, LABEL_DONE)
    if created:
        log.info("issue #%s: opened %s", number, created.get("html_url"))


def _comment_and_label(gh, number: int, body: str, label: str) -> None:
    gh.comment(number, body)
    gh.add_label(number, label)


def _label_names(issue: dict) -> set[str]:
    return {label["name"] for label in issue.get("labels", [])}


def run_once(config: Config, gh, llm, workdir_factory=None) -> list[int]:
    """Process all matching unprocessed issues; returns numbers that succeeded."""
    done = []
    for issue in gh.list_issues(config.label):
        number = issue["number"]
        if _label_names(issue) & PROCESSED_LABELS:
            log.info("issue #%s already processed, skipping", number)
            continue
        try:
            process_issue(issue, config, gh, llm, workdir_factory=workdir_factory)
            done.append(number)
        except Exception as exc:
            log.error("issue #%s failed: %s: %s", number, type(exc).__name__,
                      redact(str(exc), config.github_token))
    return done


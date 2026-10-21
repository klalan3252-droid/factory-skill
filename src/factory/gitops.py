"""Git workspace helpers using the git CLI (argv lists, no shell)."""
from __future__ import annotations

import base64
import logging
import os
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Iterable

from .config import redact

log = logging.getLogger(__name__)


class GitError(Exception):
    """Raised when a git command fails or an unsafe operation is requested."""


def _basic_credential(token: str) -> str:
    return base64.b64encode(f"x-access-token:{token}".encode()).decode()


def _auth_env(token: str | None) -> dict[str, str]:
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    if token:
        cred = _basic_credential(token)
        env["GIT_CONFIG_COUNT"] = "1"
        env["GIT_CONFIG_KEY_0"] = "http.extraheader"
        env["GIT_CONFIG_VALUE_0"] = f"AUTHORIZATION: basic {cred}"
    return env


def _git(args: list[str], cwd: Path | None = None, token: str | None = None) -> str:
    cmd = ["git", "-c", "user.name=factory-bot",
           "-c", "user.email=factory-bot@users.noreply.github.com", *args]
    log.debug("git %s", redact(" ".join(args), token))
    proc = subprocess.run(cmd, cwd=cwd, env=_auth_env(token), capture_output=True, text=True)
    if proc.returncode != 0:
        secrets = [token]
        if token:
            secrets.append(_basic_credential(token))
        err = redact((proc.stderr or proc.stdout).strip(), *secrets)
        raise GitError(f"git {args[0]} failed: {err}")
    return proc.stdout.strip()


def slug(title: str, max_len: int = 40) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:max_len].strip("-")


def branch_name(number: int, title: str) -> str:
    s = slug(title)
    return f"factory/{number}-{s}" if s else f"factory/{number}"


def clone(url: str, dest: Path, token: str | None = None) -> None:
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    _git(["clone", "--quiet", url, str(dest)], token=token)


def current_branch(repo: Path) -> str:
    return _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo)


def checkout_new_branch(repo: Path, branch: str) -> None:
    _git(["checkout", "-b", branch], cwd=repo)


def list_files(repo: Path) -> list[str]:
    out = _git(["ls-files"], cwd=repo)
    return out.splitlines()


def apply_edits(root: Path, edits: Iterable) -> None:
    """Write edits under `root`; reject any path escaping it or touching .git."""
    root = Path(root).resolve()
    targets = []
    for edit in edits:
        raw = edit.path
        if not raw or Path(raw).is_absolute():
            raise GitError(f"unsafe edit path: {raw!r}")
        target = (root / raw).resolve()
        if not target.is_relative_to(root) or target == root:
            raise GitError(f"edit path escapes the repository: {raw!r}")
        if ".git" in PurePosixPath(target.relative_to(root).as_posix()).parts:
            raise GitError(f"edit path touches .git: {raw!r}")
        targets.append((target, edit.content))
    for target, content in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)


def commit_all(repo: Path, message: str, default_branch: str | None = None) -> None:
    if default_branch and current_branch(repo) == default_branch:
        raise GitError(f"refusing to commit on default branch {default_branch!r}")
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-m", message], cwd=repo)


def push(repo: Path, branch: str, default_branch: str, dry_run: bool = False,
         token: str | None = None) -> None:
    if branch == default_branch:
        raise GitError(f"refusing to push to default branch {default_branch!r}")
    if dry_run:
        log.info("[dry-run] would push branch %s", branch)
        return
    ref = f"refs/heads/{branch}"
    _git(["push", "--force", "origin", f"+{ref}:{ref}"], cwd=repo, token=token)

"""Git helpers using the git CLI. Never force-pushes."""

import re
import secrets
import subprocess
from pathlib import Path


class GitError(Exception):
    """A git operation failed or was refused."""


def _git(repo: Path, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, timeout=120
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        raise GitError(f"git {' '.join(args)} failed: {e}") from e
    if proc.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed: {(proc.stderr or proc.stdout).strip()}")
    return proc.stdout.strip()


def slugify(text: str, max_len: int = 50) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:max_len].strip("-")
    return slug or "change"


def ensure_clean(repo: Path) -> None:
    if not Path(repo).is_dir():
        raise GitError(f"{repo} is not a git repo (directory not found)")
    try:
        _git(repo, "rev-parse", "--is-inside-work-tree")
    except GitError:
        raise GitError(f"{repo} is not a git repo") from None
    if _git(repo, "status", "--porcelain"):
        raise GitError(f"working tree at {repo} is dirty: commit or stash uncommitted changes first")


def _branch_exists(repo: Path, name: str) -> bool:
    try:
        _git(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{name}")
        return True
    except GitError:
        return False


def create_branch(repo: Path, request: str) -> str:
    name = f"factory/{slugify(request)}"
    while _branch_exists(repo, name):
        name = f"factory/{slugify(request)}-{secrets.token_hex(2)}"
    _git(repo, "checkout", "-b", name)
    return name


def has_changes(repo: Path) -> bool:
    return bool(_git(repo, "status", "--porcelain"))


def commit_all(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)


def push_branch(repo: Path, branch: str) -> None:
    """Plain push of the factory branch; only called behind --push."""
    _git(repo, "push", "-u", "origin", branch)

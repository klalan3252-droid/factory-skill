import subprocess

import pytest

from conftest import git
from factory_agents import gitops
from factory_agents.gitops import GitError


def test_slugify():
    assert gitops.slugify("Add a Feature!! to the thing") == "add-a-feature-to-the-thing"
    assert len(gitops.slugify("x" * 200)) <= 50
    assert gitops.slugify("!!!") != ""


def test_ensure_clean_ok(git_repo):
    gitops.ensure_clean(git_repo)


def test_dirty_tree_refused(git_repo):
    (git_repo / "new.txt").write_text("x")
    with pytest.raises(GitError, match="(?i)dirty|uncommitted|clean"):
        gitops.ensure_clean(git_repo)


def test_non_git_path_refused(tmp_path):
    with pytest.raises(GitError, match="(?i)git repo"):
        gitops.ensure_clean(tmp_path)


def test_create_branch_off_head(git_repo):
    head = git(git_repo, "rev-parse", "HEAD")
    name = gitops.create_branch(git_repo, "Add feature")
    assert name.startswith("factory/")
    assert git(git_repo, "rev-parse", "--abbrev-ref", "HEAD") == name
    assert git(git_repo, "rev-parse", "HEAD") == head


def test_branch_collision_gets_suffix(git_repo):
    a = gitops.create_branch(git_repo, "same")
    git(git_repo, "checkout", "main")
    b = gitops.create_branch(git_repo, "same")
    assert a != b and b.startswith(a)


def test_commit_all(git_repo):
    gitops.create_branch(git_repo, "c")
    (git_repo / "a.txt").write_text("a")
    (git_repo / "sub").mkdir()
    (git_repo / "sub" / "b.txt").write_text("b")
    gitops.commit_all(git_repo, "F: do thing")
    assert git(git_repo, "status", "--porcelain") == ""
    assert "do thing" in git(git_repo, "log", "-1", "--format=%s")
    assert git(git_repo, "rev-list", "--count", "main") == "1"


def test_push_is_plain(git_repo, monkeypatch):
    calls = []

    def fake_run(argv, *a, **k):
        calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(gitops.subprocess, "run", fake_run)
    gitops.push_branch(git_repo, "factory/x")
    pushes = [c for c in calls if "push" in c]
    assert len(pushes) == 1
    argv = pushes[0]
    assert argv[:2] == ["git", "push"] or "push" in argv
    assert argv[argv.index("push") + 1:] == ["-u", "origin", "factory/x"]
    assert not any("force" in a or a == "-f" or a.startswith("+") for a in argv)

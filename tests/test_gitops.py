import pytest

from factory import gitops
from factory.steps.implement import FileEdit
from .conftest import git, branches


def test_slug_and_branch_name():
    assert gitops.branch_name(12, "Fix: the BIG bug!!") == "factory/12-fix-the-big-bug"
    n = gitops.branch_name(3, "x" * 300)
    assert n.startswith("factory/3-") and len(n) < 100
    assert gitops.branch_name(4, "!!!").startswith("factory/4")


def test_clone_edit_commit_push(remote, tmp_path):
    dest = tmp_path / "clone"
    gitops.clone(str(remote), dest)
    gitops.checkout_new_branch(dest, "factory/1-x")
    gitops.apply_edits(dest, [FileEdit(path="sub/a.txt", content="A")])
    assert (dest / "sub/a.txt").read_text() == "A"
    gitops.commit_all(dest, "F: change")
    gitops.push(dest, "factory/1-x", default_branch="main")
    assert "factory/1-x" in branches(remote)


@pytest.mark.parametrize("bad", ["../evil.txt", "/etc/evil", ".git/hooks/pre-commit", "a/../../x"])
def test_apply_edits_rejects_escapes(tmp_path, bad):
    root = tmp_path / "r"
    (root / ".git").mkdir(parents=True)
    with pytest.raises(Exception):
        gitops.apply_edits(root, [FileEdit(path=bad, content="x")])
    assert not (tmp_path / "evil.txt").exists()


def test_push_refuses_default_branch(remote, tmp_path):
    dest = tmp_path / "clone"
    gitops.clone(str(remote), dest)
    before = git("--git-dir", str(remote), "rev-parse", "main")
    (dest / "x").write_text("x")
    gitops.commit_all(dest, "x")
    with pytest.raises(Exception):
        gitops.push(dest, "main", default_branch="main")
    assert git("--git-dir", str(remote), "rev-parse", "main") == before


def test_commit_refuses_default_branch(remote, tmp_path):
    dest = tmp_path / "clone"
    gitops.clone(str(remote), dest)
    (dest / "x").write_text("x")
    with pytest.raises(Exception):
        gitops.commit_all(dest, "x", default_branch="main")


def test_push_dry_run_skips(remote, tmp_path):
    dest = tmp_path / "clone"
    gitops.clone(str(remote), dest)
    gitops.checkout_new_branch(dest, "factory/2-y")
    (dest / "y").write_text("y")
    gitops.commit_all(dest, "y")
    gitops.push(dest, "factory/2-y", default_branch="main", dry_run=True)
    assert "factory/2-y" not in branches(remote)

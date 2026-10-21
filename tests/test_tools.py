import os

import pytest

from factory_agents.tools import FileTools, ToolError, build_tools, resolve_safe


@pytest.fixture
def root(tmp_path):
    r = tmp_path / "repo"
    (r / ".git").mkdir(parents=True)
    return r


def test_happy_paths(root):
    t = FileTools(root)
    t.write_file("a/b/c.txt", "hello")
    assert (root / "a/b/c.txt").read_text() == "hello"
    assert t.read_file("a/b/c.txt") == "hello"
    listing = t.list_files(".")
    assert "a/b/c.txt" in listing
    assert ".git" not in listing


def test_absolute_rejected(root, tmp_path):
    target = tmp_path / "evil.txt"
    with pytest.raises(ToolError):
        FileTools(root).write_file(str(target), "x")
    assert not target.exists()


def test_dotdot_rejected(root, tmp_path):
    with pytest.raises(ToolError):
        FileTools(root).write_file("../evil.txt", "x")
    with pytest.raises(ToolError):
        resolve_safe(root, "a/../../evil.txt")
    assert not (tmp_path / "evil.txt").exists()


def test_symlink_escape_rejected(root, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    os.symlink(outside, root / "link")
    with pytest.raises(ToolError):
        FileTools(root).write_file("link/evil.txt", "x")
    assert not (outside / "evil.txt").exists()


def test_git_dir_rejected(root):
    with pytest.raises(ToolError):
        FileTools(root).write_file(".git/hooks/pre-commit", "x")
    with pytest.raises(ToolError):
        FileTools(root).write_file("sub/.git/config", "x")


def test_langchain_tools_return_error_strings(root, tmp_path):
    tools = {t.name: t for t in build_tools(root)}
    assert set(tools) == {"read_file", "write_file", "list_files"}
    out = tools["write_file"].invoke({"path": "../x.txt", "content": "x"})
    assert "error" in out.lower()
    assert not (tmp_path / "x.txt").exists()
    ok = tools["write_file"].invoke({"path": "ok.txt", "content": "x"})
    assert "error" not in ok.lower()
    assert (root / "ok.txt").exists()

import pytest
from langchain_core.messages import AIMessage

from conftest import FakeProvider, git, make_llm, write_call
from factory_agents import gitops
from factory_agents.config import Config
from factory_agents.gitops import GitError
from factory_agents.pipeline import run

PASS = "def test_feature():\n    assert True\n"
FAIL = "def test_feature():\n    assert False, 'MARKER_FAIL'\n"
DONE = AIMessage(content="done")


def cfg(repo, cmd, **kw):
    return Config.load(repo=repo, request="Add the feature", test_cmd=cmd, env={}, **kw)


def test_happy_path(git_repo, py_test_cmd):
    head = git(git_repo, "rev-parse", "HEAD")
    llm = make_llm(AIMessage(content="plan"), write_call("test_feature.py", PASS), DONE)
    res = run(cfg(git_repo, py_test_cmd), FakeProvider(llm))
    assert res.success and res.iterations == 1
    assert res.branch.startswith("factory/")
    assert git(git_repo, "rev-parse", "--abbrev-ref", "HEAD") == res.branch
    assert git(git_repo, "rev-parse", "main") == head
    assert git(git_repo, "rev-list", "--count", f"main..{res.branch}") == "1"
    assert "Add the feature" in git(git_repo, "log", "-1", "--format=%B")
    assert git(git_repo, "status", "--porcelain") == ""


def test_retry_then_succeed(git_repo, py_test_cmd):
    llm = make_llm(
        AIMessage(content="plan"),
        write_call("test_feature.py", FAIL), DONE,
        write_call("test_feature.py", PASS), DONE,
    )
    res = run(cfg(git_repo, py_test_cmd), FakeProvider(llm))
    assert res.success and res.iterations == 2
    assert any("MARKER_FAIL" in str(m.content) for m in llm.calls[3])
    assert git(git_repo, "rev-list", "--count", f"main..{res.branch}") == "1"


def test_exhausted_no_commit(git_repo, py_test_cmd):
    head = git(git_repo, "rev-parse", "HEAD")
    script = [AIMessage(content="plan")]
    for i in range(2):
        script += [write_call("test_feature.py", FAIL, f"c{i}"), DONE]
    res = run(cfg(git_repo, py_test_cmd, max_iterations=2), FakeProvider(make_llm(*script)))
    assert not res.success and res.iterations == 2
    assert git(git_repo, "rev-parse", "HEAD") == head
    assert git(git_repo, "rev-parse", "--abbrev-ref", "HEAD") == res.branch
    assert (git_repo / "test_feature.py").exists()


def test_dirty_tree_raises_before_branch(git_repo, py_test_cmd):
    (git_repo / "dirty.txt").write_text("x")
    with pytest.raises(GitError):
        run(cfg(git_repo, py_test_cmd), FakeProvider(make_llm()))
    assert git(git_repo, "branch", "--list").split() == ["*", "main"]


def test_no_push_by_default(git_repo, py_test_cmd, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("push called")

    monkeypatch.setattr(gitops, "push_branch", boom)
    monkeypatch.setattr("factory_agents.pipeline.gitops.push_branch", boom, raising=False)
    llm = make_llm(AIMessage(content="plan"), write_call("test_feature.py", PASS), DONE)
    assert run(cfg(git_repo, py_test_cmd), FakeProvider(llm)).success

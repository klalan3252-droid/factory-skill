"""Shared fixtures: fake LLM, fake GitHub client, local bare remote. No network."""
import subprocess
from pathlib import Path

import pytest

TOKEN = "ghp_SECRETTOKEN1234567890"

GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_TERMINAL_PROMPT": "0",
}


def git(*args, cwd=None):
    import os
    env = {**os.environ, **GIT_ENV}
    return subprocess.run(["git", *args], cwd=cwd, env=env, check=True,
                          capture_output=True, text=True).stdout.strip()


@pytest.fixture(autouse=True)
def _git_identity(monkeypatch):
    for k, v in GIT_ENV.items():
        monkeypatch.setenv(k, v)


@pytest.fixture
def base_env():
    return {
        "GITHUB_TOKEN": TOKEN,
        "FACTORY_REPO": "acme/widgets",
        "FACTORY_LLM_PROVIDER": "anthropic",
        "FACTORY_LLM_MODEL": "claude-test",
    }


@pytest.fixture
def remote(tmp_path):
    """Local bare repo with one commit on `main`."""
    bare = tmp_path / "remote.git"
    seed = tmp_path / "seed"
    git("init", "--bare", "-b", "main", str(bare))
    git("init", "-b", "main", str(seed))
    (seed / "README.md").write_text("hello\n")
    git("add", ".", cwd=seed)
    git("commit", "-m", "init", cwd=seed)
    git("push", str(bare), "main", cwd=seed)
    return bare


def branches(bare: Path):
    out = git("--git-dir", str(bare), "for-each-ref", "--format=%(refname:short)", "refs/heads")
    return set(out.split())


class FakeStructured:
    def __init__(self, llm, schema):
        self.llm, self.schema = llm, schema

    def invoke(self, *a, **k):
        fields = self.schema.model_fields
        data = {}
        for name in fields:
            if name in ("verdict", "decision", "status", "outcome"):
                data[name] = self.llm.verdict
            elif name in ("reason", "rationale", "explanation"):
                data[name] = "because"
            elif name in ("edits", "files", "changes"):
                data[name] = [{"path": p, "content": c} for p, c in self.llm.edits]
            elif name in ("plan", "spec", "text", "summary", "body", "content", "steps"):
                data[name] = "1. do the thing"
        self.llm.calls.append(self.schema.__name__)
        return self.schema.model_validate(data)


class FakeLLM:
    """Stub chat model whose with_structured_output returns canned pydantic objects."""

    def __init__(self, verdict="suitable", edits=(("hello.txt", "hi\n"),)):
        self.verdict, self.edits, self.calls = verdict, list(edits), []

    def with_structured_output(self, schema, **kw):
        return FakeStructured(self, schema)


class FakeGitHub:
    """Records calls; write calls are listed in `.writes`."""

    def __init__(self, remote_path, issues=None):
        self.clone_url = str(remote_path)
        self.issues = issues if issues is not None else [make_issue(7, "Add hello file")]
        self.writes = []
        self.prs = []

    def get_default_branch(self):
        return "main"

    def get_branch_sha(self, branch):
        return "0" * 40

    def list_issues(self, label=None, **kw):
        return list(self.issues)

    def get_issue(self, number):
        return next(i for i in self.issues if i["number"] == number)

    def create_branch(self, *a, **k):
        self.writes.append(("create_branch", a, k))

    def comment(self, number, body, *a, **k):
        self.writes.append(("comment", number, body))

    def add_label(self, number, label, *a, **k):
        self.writes.append(("add_label", number, label))

    def create_pr(self, title, body, head, base, draft=False, **k):
        self.writes.append(("create_pr", head, base, draft))
        self.prs.append({"title": title, "body": body, "head": head, "base": base, "draft": draft})
        return {"number": 99, "html_url": "https://example.test/pr/99"}


def make_issue(number, title, labels=("factory",), body="Please add hello.txt"):
    return {"number": number, "title": title, "body": body,
            "labels": [{"name": n} for n in labels], "state": "open"}


@pytest.fixture
def fake_llm():
    return FakeLLM()


@pytest.fixture
def fake_gh(remote):
    return FakeGitHub(remote)


@pytest.fixture
def make_config(base_env):
    from factory.config import load_config

    def _make(**over):
        env = {**base_env, "FACTORY_TEST_COMMAND": "true", **over}
        return load_config(env)
    return _make

import pytest

import factory.cli as cli
import factory.pipeline as pipeline
from .conftest import TOKEN, make_issue


@pytest.fixture
def env(monkeypatch, base_env):
    for k in ("GITHUB_TOKEN", "FACTORY_REPO", "FACTORY_DRY_RUN", "FACTORY_LABEL"):
        monkeypatch.delenv(k, raising=False)
    for k, v in base_env.items():
        monkeypatch.setenv(k, v)


@pytest.fixture
def patched(monkeypatch):
    calls = {"run_once": [], "process_issue": []}

    def ro(config, *a, **k):
        calls["run_once"].append(config)
        return []

    def pi(issue, config, *a, **k):
        calls["process_issue"].append((issue, config))

    for mod in (pipeline, cli):
        monkeypatch.setattr(mod, "run_once", ro, raising=False)
        monkeypatch.setattr(mod, "process_issue", pi, raising=False)
        monkeypatch.setattr(mod, "get_chat_model", lambda c: object(), raising=False)
    import factory.llm
    monkeypatch.setattr(factory.llm, "get_chat_model", lambda c: object())
    import factory.github
    monkeypatch.setattr(factory.github.GitHubClient, "get_issue",
                        lambda self, n: make_issue(n, "t"))
    return calls


def call(argv):
    try:
        return cli.main(argv) or 0
    except SystemExit as e:
        return e.code or 0


def test_run_once(env, patched):
    assert call(["run", "--once"]) == 0
    assert len(patched["run_once"]) == 1


def test_flags_override_config(env, patched):
    call(["run", "--once", "--dry-run", "--repo", "o/r", "--label", "bot"])
    cfg = patched["run_once"][0]
    assert cfg.dry_run and cfg.repo == "o/r" and cfg.label == "bot"


def test_dry_run_env(env, patched, monkeypatch):
    monkeypatch.setenv("FACTORY_DRY_RUN", "1")
    call(["run", "--once"])
    assert patched["run_once"][0].dry_run


def test_single_issue(env, patched):
    assert call(["run", "--issue", "7"]) == 0
    assert [i["number"] for i, _ in patched["process_issue"]] == [7]
    assert patched["run_once"] == []


def test_polling_uses_interval(env, patched, monkeypatch):
    sleeps = []

    def fake_sleep(s):
        sleeps.append(s)
        if len(sleeps) >= 2:
            raise KeyboardInterrupt

    monkeypatch.setattr("time.sleep", fake_sleep)
    try:
        call(["run", "--interval", "5"])
    except KeyboardInterrupt:
        pass
    assert sleeps[:2] == [5, 5]
    assert len(patched["run_once"]) >= 2


def test_config_error_exits_nonzero_without_secret(env, patched, monkeypatch, capsys):
    monkeypatch.delenv("FACTORY_REPO")
    assert call(["run", "--once"]) != 0
    out = capsys.readouterr()
    assert "FACTORY_REPO" in out.err + out.out
    assert TOKEN not in out.err + out.out


def test_missing_token_exits_nonzero(env, patched, monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_TOKEN")
    assert call(["run", "--once"]) != 0
    assert "GITHUB_TOKEN" in "".join(capsys.readouterr())


def test_llm_error_exits_nonzero(env, patched, monkeypatch, capsys):
    from factory.llm import LLMError

    def bad(c):
        raise LLMError("unknown provider 'x'")
    import factory.llm
    for mod in (factory.llm, cli):
        monkeypatch.setattr(mod, "get_chat_model", bad, raising=False)
    assert call(["run", "--once"]) != 0
    assert "unknown provider" in "".join(capsys.readouterr())

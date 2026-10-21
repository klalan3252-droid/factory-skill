import pytest

import factory.pipeline as pipeline
from factory.pipeline import process_issue, run_once
from .conftest import FakeLLM, FakeGitHub, make_issue, branches, git


def run(issue, cfg, gh, llm, tmp_path):
    return process_issue(issue, cfg, gh, llm, workdir_factory=lambda: tmp_path / "work")


def test_happy_path_ready_pr(make_config, fake_gh, fake_llm, remote, tmp_path):
    main_before = git("--git-dir", str(remote), "rev-parse", "main")
    run(fake_gh.issues[0], make_config(), fake_gh, fake_llm, tmp_path)
    assert len(fake_gh.prs) == 1
    pr = fake_gh.prs[0]
    assert pr["draft"] is False and pr["base"] == "main"
    assert pr["head"].startswith("factory/7-add-hello-file")
    assert "Closes #7" in pr["body"]
    assert pr["head"] in branches(remote)
    assert git("--git-dir", str(remote), "rev-parse", "main") == main_before
    assert git("--git-dir", str(remote), "show", f"{pr['head']}:hello.txt") == "hi"
    assert any(w[0] == "add_label" for w in fake_gh.writes)
    assert fake_llm.calls[:3] and len(fake_llm.calls) >= 3  # triage, spec, implement


def test_triage_reject_stops_and_comments(make_config, fake_gh, remote, tmp_path):
    llm = FakeLLM(verdict="reject")
    run(fake_gh.issues[0], make_config(), fake_gh, llm, tmp_path)
    assert fake_gh.prs == []
    assert [w for w in fake_gh.writes if w[0] == "comment"]
    assert branches(remote) == {"main"}
    assert len(llm.calls) == 1


def test_triage_skip_stops(make_config, fake_gh, remote, tmp_path):
    run(fake_gh.issues[0], make_config(), fake_gh, FakeLLM(verdict="skip"), tmp_path)
    assert fake_gh.prs == [] and branches(remote) == {"main"}


def test_failing_tests_never_ready_pr(make_config, fake_gh, fake_llm, remote, tmp_path):
    run(fake_gh.issues[0], make_config(FACTORY_TEST_COMMAND="false"), fake_gh, fake_llm, tmp_path)
    assert all(p["draft"] is True for p in fake_gh.prs)
    assert fake_gh.prs or [w for w in fake_gh.writes if w[0] == "comment"]
    for p in fake_gh.prs:
        assert "fail" in p["body"].lower()


def test_tests_run_in_clone(make_config, fake_gh, remote, tmp_path):
    cfg = make_config(FACTORY_TEST_COMMAND="test -f hello.txt")
    run(fake_gh.issues[0], cfg, fake_gh, FakeLLM(), tmp_path)
    assert fake_gh.prs and fake_gh.prs[0]["draft"] is False


def test_edit_escaping_clone_fails_safely(make_config, fake_gh, remote, tmp_path):
    llm = FakeLLM(edits=[("../escape.txt", "x")])
    try:
        run(fake_gh.issues[0], make_config(), fake_gh, llm, tmp_path)
    except Exception:
        pass
    assert not (tmp_path / "escape.txt").exists()
    assert not [p for p in fake_gh.prs if not p["draft"]]
    assert branches(remote) <= {"main"} or all(b.startswith("factory/") for b in branches(remote))


def test_run_once_skips_already_processed(make_config, fake_gh, fake_llm, monkeypatch, tmp_path):
    fake_gh.issues = [make_issue(1, "a", labels=("factory", "factory-done")),
                      make_issue(2, "b", labels=("factory", "in-progress")),
                      make_issue(3, "c")]
    seen = []
    monkeypatch.setattr(pipeline, "process_issue", lambda issue, *a, **k: seen.append(issue["number"]))
    run_once(make_config(), fake_gh, fake_llm, workdir_factory=lambda: tmp_path)
    assert seen == [3]


def test_run_once_continues_after_failure(make_config, fake_gh, fake_llm, monkeypatch, tmp_path, caplog):
    fake_gh.issues = [make_issue(1, "a"), make_issue(2, "b")]
    seen = []

    def fake_process(issue, *a, **k):
        seen.append(issue["number"])
        if issue["number"] == 1:
            raise RuntimeError("boom")
    monkeypatch.setattr(pipeline, "process_issue", fake_process)
    run_once(make_config(), fake_gh, fake_llm, workdir_factory=lambda: tmp_path)
    assert seen == [1, 2]
    assert "boom" in caplog.text

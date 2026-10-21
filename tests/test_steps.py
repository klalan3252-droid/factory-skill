import pytest

from factory.steps import pr as pr_step
from factory.steps import testing as test_step
from factory.steps import triage, spec, implement
from .conftest import FakeLLM, make_issue


def test_run_tests_pass_and_fail(tmp_path):
    ok = test_step.run_tests("true", tmp_path)
    bad = test_step.run_tests("false", tmp_path)
    assert ok.passed and ok.exit_code == 0
    assert not bad.passed and bad.exit_code != 0


def test_run_tests_captures_and_truncates_output(tmp_path):
    r = test_step.run_tests("python -c \"print('x'*200000)\"", tmp_path)
    assert 0 < len(r.output) < 100000


def test_run_tests_runs_in_cwd_and_times_out(tmp_path):
    (tmp_path / "marker").write_text("m")
    r = test_step.run_tests("ls", tmp_path)
    assert "marker" in r.output
    t = test_step.run_tests("sleep 5", tmp_path, timeout=0.5)
    assert not t.passed


def test_pr_body_references_issue_and_result(tmp_path):
    res = test_step.run_tests("true", tmp_path)
    body = pr_step.build_body(issue_number=42, plan="the plan", test_result=res)
    assert "Closes #42" in body
    assert "pass" in body.lower()
    bad = test_step.run_tests("false", tmp_path)
    assert "fail" in pr_step.build_body(issue_number=42, plan="p", test_result=bad).lower()


def test_triage_returns_verdict_with_reason():
    v = triage.triage(FakeLLM(verdict="reject"), make_issue(1, "t"))
    assert "reject" in str(getattr(v, "verdict", v)).lower() or v.verdict == "reject"
    assert v.reason


def test_spec_returns_text():
    s = spec.make_spec(FakeLLM(), make_issue(1, "t"))
    assert isinstance(s, str) and s.strip()


def test_implement_returns_file_edits():
    edits = implement.propose_edits(FakeLLM(edits=[("a.txt", "A")]), make_issue(1, "t"), "plan", repo_files=["README.md"])
    assert [(e.path, e.content) for e in edits] == [("a.txt", "A")]

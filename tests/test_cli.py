import pytest
from langchain_core.messages import AIMessage

from conftest import FakeProvider, git, make_llm, write_call
from factory_agents.cli import build_parser, main

PASS = "def test_feature():\n    assert True\n"
FAIL = "def test_feature():\n    assert False\n"


def test_help_exits_zero(capsys):
    with pytest.raises(SystemExit) as e:
        main(["--help"])
    assert e.value.code == 0
    assert "run" in capsys.readouterr().out


def test_push_defaults_false():
    args = build_parser().parse_args(["run", "--repo", "x", "--request", "y"])
    assert args.push is False


def test_non_git_repo(tmp_path, capsys):
    code = main(["run", "--repo", str(tmp_path), "--request", "x", "--model", "a:b"])
    assert code != 0
    assert capsys.readouterr().err.strip()


def test_missing_repo(tmp_path, capsys):
    code = main(["run", "--repo", str(tmp_path / "nope"), "--request", "x", "--model", "a:b"])
    assert code != 0 and capsys.readouterr().err.strip()


def test_bad_model(git_repo, capsys):
    assert main(["run", "--repo", str(git_repo), "--request", "x", "--model", "bogus"]) != 0
    assert capsys.readouterr().err.strip()
    assert main(["run", "--repo", str(git_repo), "--request", "x", "--model", "nopkg:m"]) != 0


def test_success_exit_zero_and_request_file(git_repo, py_test_cmd, tmp_path):
    rf = tmp_path / "req.txt"
    rf.write_text("Do from file")
    llm = make_llm(AIMessage(content="p"), write_call("test_feature.py", PASS), AIMessage(content="d"))
    code = main(
        ["run", "--repo", str(git_repo), "--request-file", str(rf), "--test-cmd", py_test_cmd,
         "--model", "fake:m"],
        provider=FakeProvider(llm),
    )
    assert code == 0
    assert "Do from file" in git(git_repo, "log", "-1", "--format=%B")


def test_failure_exit_one(git_repo, py_test_cmd, capsys):
    llm = make_llm(AIMessage(content="p"), write_call("test_feature.py", FAIL), AIMessage(content="d"))
    code = main(
        ["run", "--repo", str(git_repo), "--request", "x", "--test-cmd", py_test_cmd,
         "--max-iterations", "1", "--model", "fake:m"],
        provider=FakeProvider(llm),
    )
    assert code == 1

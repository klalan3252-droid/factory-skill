import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

PYTEST_CMD = f"{sys.executable} -m pytest -q"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "target"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "Tester")
    (repo / ".gitignore").write_text("__pycache__/\n.pytest_cache/\n")
    (repo / "test_base.py").write_text("def test_ok():\n    assert True\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "initial")
    return repo


class ScriptedLLM(BaseChatModel):
    """Fake chat model replaying a queue of AIMessages; records every prompt."""

    responses: list[AIMessage]
    calls: list[list[BaseMessage]] = []

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "ScriptedLLM":
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        self.calls.append(list(messages))
        if not self.responses:
            msg = AIMessage(content="(script exhausted)")
        else:
            msg = self.responses.pop(0)
        return ChatResult(generations=[ChatGeneration(message=msg)])


def make_llm(*responses: AIMessage) -> ScriptedLLM:
    return ScriptedLLM(responses=list(responses), calls=[])


def write_call(path: str, content: str, call_id: str = "c1") -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {"name": "write_file", "args": {"path": path, "content": content}, "id": call_id}
        ],
    )


class FakeProvider:
    def __init__(self, model: ScriptedLLM):
        self.model = model

    def get_chat_model(self) -> ScriptedLLM:
        return self.model


@pytest.fixture
def py_test_cmd() -> str:
    return PYTEST_CMD

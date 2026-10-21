import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class StubResponse:
    def __init__(self, content):
        self.content = content


class StubLLM:
    """Offline stand-in for a chat model: invoke(messages) -> object with .content."""

    def __init__(self):
        self.calls = []

    def invoke(self, messages, *args, **kwargs):
        self.calls.append(messages)
        return StubResponse(f"stub-response-{len(self.calls)}")


@pytest.fixture
def stub_llm():
    return StubLLM()


@pytest.fixture
def tickets_dir(tmp_path, monkeypatch):
    d = tmp_path / "tickets"
    d.mkdir()
    monkeypatch.setenv("TICKETS_DIR", str(d))
    return d

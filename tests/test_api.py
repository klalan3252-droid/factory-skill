import json

import pytest
from fastapi.testclient import TestClient

from app.llm import get_llm
from app.main import app


@pytest.fixture
def client(tickets_dir, stub_llm):
    (tickets_dir / "a.json").write_text(
        json.dumps({"id": "a", "title": "Fix login", "description": "Login fails"})
    )
    (tickets_dir / "b.md").write_text("# Add search\n\nNeed search box\n")
    app.dependency_overrides[get_llm] = lambda: stub_llm
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_list(client):
    r = client.get("/tickets")
    assert r.status_code == 200
    data = r.json()
    assert sorted(data, key=lambda t: t["id"]) == [
        {"id": "a", "title": "Fix login"},
        {"id": "b", "title": "Add search"},
    ]


def test_get(client):
    r = client.get("/tickets/a")
    assert r.status_code == 200
    assert r.json() == {"id": "a", "title": "Fix login", "description": "Login fails"}


def test_get_markdown(client):
    body = client.get("/tickets/b").json()
    assert body["title"] == "Add search"
    assert "Need search box" in body["description"]


def test_get_unknown_404(client):
    assert client.get("/tickets/nope").status_code == 404


def test_process(client, stub_llm):
    r = client.post("/tickets/a/process")
    assert r.status_code == 200
    assert r.json() == {
        "ticket_id": "a",
        "triage": "stub-response-1",
        "plan": "stub-response-2",
    }
    assert len(stub_llm.calls) == 2


def test_process_unknown_404_no_llm(client, stub_llm):
    r = client.post("/tickets/nope/process")
    assert r.status_code == 404
    assert stub_llm.calls == []

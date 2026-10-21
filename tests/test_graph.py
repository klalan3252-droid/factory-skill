import json

import pytest

from app.graph import build_graph
from app.tickets import TicketNotFoundError


@pytest.fixture
def one_ticket(tickets_dir):
    (tickets_dir / "a.json").write_text(
        json.dumps({"id": "a", "title": "Fix login", "description": "Login fails on Safari"})
    )


def test_graph_runs_and_fills_state(one_ticket, stub_llm):
    graph = build_graph(stub_llm)
    result = graph.invoke({"ticket_id": "a"})
    assert result["ticket_id"] == "a"
    assert "Fix login" in repr(result["ticket"])
    assert result["triage"] == "stub-response-1"
    assert result["plan"] == "stub-response-2"
    assert len(stub_llm.calls) == 2


def test_graph_node_names_and_order(one_ticket, stub_llm):
    g = build_graph(stub_llm).get_graph()
    names = set(g.nodes)
    assert {"load_ticket", "triage", "plan"} <= names
    edges = {(e.source, e.target) for e in g.edges}
    assert ("load_ticket", "triage") in edges
    assert ("triage", "plan") in edges
    assert ("plan", "__end__") in edges


def test_ticket_content_reaches_llm(one_ticket, stub_llm):
    build_graph(stub_llm).invoke({"ticket_id": "a"})
    assert "Login fails on Safari" in repr(stub_llm.calls[0])


def test_unknown_ticket_raises_without_llm(one_ticket, stub_llm):
    with pytest.raises(TicketNotFoundError):
        build_graph(stub_llm).invoke({"ticket_id": "zzz"})
    assert stub_llm.calls == []


def test_import_and_get_llm_need_no_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    import app.main  # noqa: F401
    from app.llm import get_llm  # noqa: F401

import json
from pathlib import Path

import pytest

from app import tickets
from app.tickets import TicketNotFoundError, get_ticket, list_tickets

ROOT = Path(__file__).resolve().parent.parent


def test_json_ticket(tickets_dir):
    (tickets_dir / "a.json").write_text(
        json.dumps({"id": "T-1", "title": "Fix bug", "description": "It breaks"})
    )
    [t] = list_tickets()
    assert (t.id, t.title, t.description) == ("T-1", "Fix bug", "It breaks")


def test_markdown_ticket_id_from_stem(tickets_dir):
    (tickets_dir / "my-ticket.md").write_text("# Add feature\n\nLine one.\nLine two.\n")
    t = get_ticket("my-ticket")
    assert t.id == "my-ticket"
    assert t.title == "Add feature"
    assert "Line one." in t.description and "Line two." in t.description
    assert "# Add feature" not in t.description


def test_markdown_front_matter_id_override(tickets_dir):
    (tickets_dir / "stem.md").write_text("---\nid: CUSTOM-9\n---\n# Title\n\nBody text\n")
    t = get_ticket("CUSTOM-9")
    assert t.title == "Title"
    assert "Body text" in t.description
    with pytest.raises(TicketNotFoundError):
        get_ticket("stem")


def test_list_mixed_and_ignores_other_files(tickets_dir):
    (tickets_dir / "a.json").write_text(json.dumps({"id": "a", "title": "A", "description": "d"}))
    (tickets_dir / "b.md").write_text("# B\n\nbody")
    (tickets_dir / "notes.txt").write_text("ignore me")
    assert sorted(t.id for t in list_tickets()) == ["a", "b"]


def test_unknown_id_raises(tickets_dir):
    (tickets_dir / "a.json").write_text(json.dumps({"id": "a", "title": "A", "description": "d"}))
    with pytest.raises(TicketNotFoundError):
        get_ticket("nope")


def test_id_match_is_exact_no_path_traversal(tickets_dir):
    (tickets_dir / "a.json").write_text(json.dumps({"id": "a", "title": "A", "description": "d"}))
    for bad in ["../a", "a.json", "A", "a ", ""]:
        with pytest.raises(TicketNotFoundError):
            get_ticket(bad)


def test_missing_directory_yields_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("TICKETS_DIR", str(tmp_path / "does-not-exist"))
    assert list_tickets() == []


def test_malformed_files_do_not_break_listing(tickets_dir):
    (tickets_dir / "good.json").write_text(json.dumps({"id": "g", "title": "G", "description": "d"}))
    (tickets_dir / "bad.json").write_text("{not json")
    (tickets_dir / "missing-keys.json").write_text(json.dumps({"id": "x"}))
    assert [t.id for t in list_tickets()] == ["g"]


def test_env_read_at_call_time(tmp_path, monkeypatch):
    d1, d2 = tmp_path / "one", tmp_path / "two"
    d1.mkdir()
    d2.mkdir()
    (d1 / "a.json").write_text(json.dumps({"id": "a", "title": "A", "description": "d"}))
    (d2 / "b.json").write_text(json.dumps({"id": "b", "title": "B", "description": "d"}))
    monkeypatch.setenv("TICKETS_DIR", str(d1))
    assert [t.id for t in list_tickets()] == ["a"]
    monkeypatch.setenv("TICKETS_DIR", str(d2))
    assert [t.id for t in list_tickets()] == ["b"]


def test_default_dir_is_tickets(monkeypatch):
    monkeypatch.delenv("TICKETS_DIR", raising=False)
    assert Path(tickets.tickets_dir()) == Path("tickets")


def test_sample_tickets_in_repo(monkeypatch):
    monkeypatch.setenv("TICKETS_DIR", str(ROOT / "tickets"))
    assert list((ROOT / "tickets").glob("*.json"))
    assert list((ROOT / "tickets").glob("*.md"))
    ts = list_tickets()
    assert len(ts) >= 2
    assert all(t.id and t.title and t.description for t in ts)

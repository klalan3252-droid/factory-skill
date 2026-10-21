import json
import logging
import os
import re
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Ticket(BaseModel):
    id: str
    title: str
    description: str


class TicketNotFoundError(Exception):
    pass


def tickets_dir() -> Path:
    return Path(os.environ.get("TICKETS_DIR", "tickets"))


def _parse_json(path: Path) -> Ticket:
    data = json.loads(path.read_text(encoding="utf-8"))
    return Ticket(id=str(data["id"]), title=data["title"], description=data["description"])


def _parse_markdown(path: Path) -> Ticket:
    text = path.read_text(encoding="utf-8")
    ticket_id = path.stem
    match = re.match(r"---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if match:
        text = text[match.end():]
        for line in match.group(1).splitlines():
            key, _, value = line.partition(":")
            if key.strip() == "id" and value.strip():
                ticket_id = value.strip()
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("# "):
            return Ticket(
                id=ticket_id,
                title=line[2:].strip(),
                description="\n".join(lines[i + 1:]).strip(),
            )
    raise ValueError("no '#' heading found")


def list_tickets() -> list[Ticket]:
    directory = tickets_dir()
    if not directory.is_dir():
        return []
    tickets = []
    for path in sorted(directory.iterdir()):
        parser = {".json": _parse_json, ".md": _parse_markdown}.get(path.suffix)
        if parser is None or not path.is_file():
            continue
        try:
            tickets.append(parser(path))
        except Exception as exc:
            logger.warning("Skipping malformed ticket %s: %s", path, exc)
    return tickets


def get_ticket(ticket_id: str) -> Ticket:
    for ticket in list_tickets():
        if ticket.id == ticket_id:
            return ticket
    raise TicketNotFoundError(ticket_id)

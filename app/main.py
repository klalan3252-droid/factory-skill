from fastapi import Depends, FastAPI, HTTPException

from app.graph import build_graph
from app.llm import get_llm
from app.tickets import Ticket, TicketNotFoundError, get_ticket, list_tickets

app = FastAPI(title="factory-skill")


def _get_ticket_or_404(ticket_id: str) -> Ticket:
    try:
        return get_ticket(ticket_id)
    except TicketNotFoundError:
        raise HTTPException(status_code=404, detail="Ticket not found")


@app.get("/tickets")
def tickets_index() -> list[dict]:
    return [{"id": t.id, "title": t.title} for t in list_tickets()]


@app.get("/tickets/{ticket_id}")
def ticket_detail(ticket_id: str) -> Ticket:
    return _get_ticket_or_404(ticket_id)


@app.post("/tickets/{ticket_id}/process")
def process_ticket(ticket_id: str, llm=Depends(get_llm)) -> dict:
    _get_ticket_or_404(ticket_id)
    result = build_graph(llm).invoke({"ticket_id": ticket_id})
    return {"ticket_id": ticket_id, "triage": result["triage"], "plan": result["plan"]}

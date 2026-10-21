from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.tickets import get_ticket


class State(TypedDict, total=False):
    ticket_id: str
    ticket: dict
    triage: str
    plan: str


def _describe(ticket: dict) -> str:
    return f"Title: {ticket['title']}\n\n{ticket['description']}"


def build_graph(llm):
    def load_ticket(state: State) -> dict:
        return {"ticket": get_ticket(state["ticket_id"]).model_dump()}

    def triage(state: State) -> dict:
        prompt = (
            "Triage this ticket. Give a short summary, its type (bug, feature, chore) "
            "and a priority (low, medium, high).\n\n" + _describe(state["ticket"])
        )
        return {"triage": str(llm.invoke(prompt).content)}

    def plan(state: State) -> dict:
        prompt = (
            "Write a plan for this ticket as a numbered list of steps.\n\n"
            f"{_describe(state['ticket'])}\n\nTriage:\n{state['triage']}"
        )
        return {"plan": str(llm.invoke(prompt).content)}

    graph = StateGraph(State)
    graph.add_node("load_ticket", load_ticket)
    graph.add_node("triage", triage)
    graph.add_node("plan", plan)
    graph.set_entry_point("load_ticket")
    graph.add_edge("load_ticket", "triage")
    graph.add_edge("triage", "plan")
    graph.add_edge("plan", END)
    return graph.compile()

"""Planner and implementer agents built on a bounded tool-calling loop."""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

PLAN_SYSTEM = (
    "You are a software planner. Given a request and the repository file listing, "
    "write a short numbered implementation plan. Do not write code."
)
IMPLEMENT_SYSTEM = (
    "You are a software engineer. Implement the plan by creating or editing files with "
    "the provided tools (paths are relative to the repo root). Include or update tests. "
    "Reply with a short summary when finished."
)


def run_tool_loop(
    model: BaseChatModel, system: str, user: str, tools: list[BaseTool], max_steps: int = 20
) -> str:
    bound = model.bind_tools(tools)
    by_name = {t.name: t for t in tools}
    messages: list[BaseMessage] = [SystemMessage(system), HumanMessage(user)]
    text = ""
    for _ in range(max_steps):
        reply = bound.invoke(messages)
        messages.append(reply)
        text = str(reply.content)
        if not reply.tool_calls:
            break
        for call in reply.tool_calls:
            tool = by_name.get(call["name"])
            result = (
                tool.invoke(call["args"]) if tool else f"Error: unknown tool {call['name']}"
            )
            messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
    return text


def plan(model: BaseChatModel, request: str, file_listing: str) -> str:
    user = f"Request:\n{request}\n\nFiles:\n{file_listing or '(empty)'}"
    return str(model.invoke([SystemMessage(PLAN_SYSTEM), HumanMessage(user)]).content)


def implement(
    model: BaseChatModel,
    request: str,
    plan_text: str,
    tools: list[BaseTool],
    feedback: str | None = None,
    max_steps: int = 20,
) -> str:
    user = f"Request:\n{request}\n\nPlan:\n{plan_text}"
    if feedback:
        user += f"\n\nThe tests failed with this output; fix the problems:\n{feedback}"
    return run_tool_loop(model, IMPLEMENT_SYSTEM, user, tools, max_steps)

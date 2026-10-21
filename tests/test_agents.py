from langchain_core.messages import AIMessage, ToolMessage

from conftest import make_llm, write_call
from factory_agents.agents import implement, plan, run_tool_loop
from factory_agents.tools import build_tools


def test_plan_returns_text():
    llm = make_llm(AIMessage(content="1. do it"))
    assert plan(llm, "add feature", "a.py\nb.py") == "1. do it"
    text = "".join(str(m.content) for m in llm.calls[0])
    assert "add feature" in text and "a.py" in text


def test_tool_loop_executes_calls(tmp_path):
    llm = make_llm(write_call("x.txt", "hi"), AIMessage(content="done"))
    out = run_tool_loop(llm, "sys", "user", build_tools(tmp_path), max_steps=5)
    assert (tmp_path / "x.txt").read_text() == "hi"
    assert out == "done"
    assert any(isinstance(m, ToolMessage) for m in llm.calls[1])


def test_tool_loop_is_bounded(tmp_path):
    llm = make_llm(*[write_call("x.txt", "hi", f"c{i}") for i in range(50)])
    run_tool_loop(llm, "s", "u", build_tools(tmp_path), max_steps=3)
    assert len(llm.calls) <= 3


def test_implement_includes_feedback(tmp_path):
    llm = make_llm(AIMessage(content="ok"))
    implement(llm, "req", "the plan", build_tools(tmp_path), feedback="FAILURE_MARKER")
    text = "".join(str(m.content) for m in llm.calls[0])
    assert "req" in text and "the plan" in text and "FAILURE_MARKER" in text

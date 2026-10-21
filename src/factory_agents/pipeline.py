"""plan -> implement -> verify (with retries) -> commit."""

from dataclasses import dataclass

from factory_agents import agents, gitops
from factory_agents.config import Config
from factory_agents.llm import LLMProvider
from factory_agents.tools import FileTools, build_tools
from factory_agents.verifier import run_tests


@dataclass(frozen=True)
class RunResult:
    success: bool
    branch: str
    iterations: int
    message: str


def run(config: Config, provider: LLMProvider) -> RunResult:
    repo = config.repo
    gitops.ensure_clean(repo)
    model = provider.get_chat_model()
    branch = gitops.create_branch(repo, config.request)

    plan_text = agents.plan(model, config.request, FileTools(repo).list_files("."))
    tools = build_tools(repo)
    feedback: str | None = None
    for i in range(1, config.max_iterations + 1):
        agents.implement(model, config.request, plan_text, tools, feedback)
        result = run_tests(config.test_cmd, repo, config.test_timeout)
        if result.passed:
            if not gitops.has_changes(repo):
                return RunResult(False, branch, i, "tests passed but no changes were made")
            gitops.commit_all(repo, f"factory: {config.request.strip()}")
            if config.push:
                gitops.push_branch(repo, branch)
            return RunResult(True, branch, i, f"committed on {branch}")
        feedback = result.output
    return RunResult(
        False, branch, config.max_iterations,
        f"tests still failing after {config.max_iterations} iterations; changes left uncommitted on {branch}",
    )

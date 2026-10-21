"""Command line entry point: `factory run ...`."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from factory_agents.config import Config, ConfigError
from factory_agents.gitops import GitError
from factory_agents.llm import ChatModelProvider, LLMProvider, ProviderError
from factory_agents.pipeline import run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="factory", description="Autonomous software factory: request -> tested commit."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run", help="plan, implement, verify and commit a change on a new branch")
    r.add_argument("--repo", required=True, type=Path, help="path to the target git repo")
    src = r.add_mutually_exclusive_group(required=True)
    src.add_argument("--request", help="work item as free text")
    src.add_argument("--request-file", type=Path, help="file containing the work item")
    r.add_argument("--test-cmd", help="test command (default: FACTORY_TEST_CMD or 'pytest')")
    r.add_argument("--max-iterations", type=int, help="max implement/verify rounds (default 3)")
    r.add_argument("--model", help="provider:model (default: FACTORY_MODEL)")
    r.add_argument("--push", action="store_true", default=False,
                   help="push the factory branch (plain push, never forced)")
    return parser


def main(argv: Sequence[str] | None = None, provider: LLMProvider | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        request = args.request
        if args.request_file is not None:
            try:
                request = args.request_file.read_text()
            except OSError as e:
                raise ConfigError(f"cannot read request file: {e}") from e
        if not request or not request.strip():
            raise ConfigError("request is empty")
        config = Config.load(
            repo=args.repo, request=request, model=args.model, test_cmd=args.test_cmd,
            max_iterations=args.max_iterations, push=args.push,
        )
        result = run(config, provider or ChatModelProvider(config.model))
    except (ConfigError, ProviderError, GitError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if result.success:
        print(f"success: {result.message} ({result.iterations} iteration(s))")
        return 0
    print(f"failure: {result.message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())

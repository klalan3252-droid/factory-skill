"""Command line entrypoint."""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time

from .config import ConfigError, load_config
from .github import GitHubClient, GitHubError
from .llm import LLMError, get_chat_model
from .pipeline import process_issue, run_once

log = logging.getLogger("factory")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="factory", description="Autonomous software factory agent")
    sub = p.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="process labelled issues")
    run.add_argument("--once", action="store_true", help="process matching issues once and exit")
    run.add_argument("--issue", type=int, help="process a single issue by number and exit")
    run.add_argument("--interval", type=float, help="polling interval in seconds")
    run.add_argument("--dry-run", action="store_true", help="make no GitHub writes or pushes")
    run.add_argument("--repo", help="owner/name (overrides FACTORY_REPO)")
    run.add_argument("--label", help="trigger label (overrides FACTORY_LABEL)")
    run.add_argument("-v", "--verbose", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    env = dict(os.environ)
    if args.repo:
        env["FACTORY_REPO"] = args.repo
    if args.label:
        env["FACTORY_LABEL"] = args.label
    if args.dry_run:
        env["FACTORY_DRY_RUN"] = "1"
    if args.interval:
        env["FACTORY_POLL_INTERVAL"] = str(args.interval)
    try:
        config = load_config(env)
        llm = get_chat_model(config)
        gh = GitHubClient(config.github_token, config.repo)
        if config.dry_run:
            log.info("dry-run: no GitHub writes or pushes will be made")
        if args.issue is not None:
            process_issue(gh.get_issue(args.issue), config, gh, llm)
        elif args.once:
            run_once(config, gh, llm)
        else:
            _poll(config, gh, llm)
    except (ConfigError, LLMError, GitHubError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        log.info("interrupted, exiting")
    return 0


def _poll(config, gh, llm) -> None:
    while True:
        run_once(config, gh, llm)
        time.sleep(config.poll_interval)

---
name: software-factory
description: Use when Claude is tagged in a Slack thread about a ClickUp task and asked to do the work. Runs the full loop - read the ClickUp task, resolve the repo, plan, implement, test, open a GitHub pull request and report the link back in the same Slack thread.
---

# Software factory

Follow the steps in order. Conventions (branch, PR title/body, failure report, config) are in `${CLAUDE_PLUGIN_ROOT}/docs/conventions.md`; read it first.

Remember the Slack channel and thread timestamp that triggered you; all replies go there.

## Checkpoints, self-healing and usage limits

Deterministic helpers live in `${CLAUDE_PLUGIN_ROOT}/scripts/factory.py` (`python3 -I`, stdlib only). Use them instead of improvising:

- **Checkpoint.** Run `factory.py init --task-id <id> --channel <c> --thread-ts <ts>` first. It resumes an existing run rather than restarting. After each step run `factory.py mark --task-id <id> --step <step> --status done` (add `--repo`, `--branch`, `--pr-url` when known). `factory.py next --task-id <id>` says which step to continue from; never redo a `done` step, and never open a second PR if `pr_url` is set.
- **Self-healing loop.** Run the test step through `factory.py heal --task-id <id> --step test --run "<test command>" --max-attempts 3`. Exit 0 means pass; exit 10 means fix the code from the printed output and call it again; exit 3 means attempts are exhausted, so go to Failure handling.
- **Usage limits.** Exit 75 from `heal` (or any tool output that hits a usage or rate limit, check with `factory.py parse-limit`) means pause, not fail. Post one short "paused until <time>" note in the thread, run `factory.py wait --task-id <id>` (it sleeps until the reset, then marks the run running), and continue from `factory.py next`. A limit never counts as a failed attempt and never produces a failure report.
- Use `factory.py resolve-repo`, `branch`, `pr-title`, `pr-body` and `failure-report` for the repo, naming and report formats so output matches the conventions exactly.

1. **Read the ClickUp task** with the ClickUp MCP (task ID from the thread, mirrored message or URL). Collect title, description, acceptance criteria, comments, URL.
2. **Resolve the target repo.** Use the repo named in the ClickUp task or the Slack message (`owner/name` or GitHub URL). If none is found, never guess: ask in the thread with the Slack MCP, then stop. Do this before any clone, branch or edit.
3. **Plan.** Clone the repo with `gh repo clone`, study it, and write a short plan mapped to the acceptance criteria. If planning fails, go to Failure handling.
4. **Implement** on a branch named `CU-<task-id>-<short-slug>` created from the default branch. Keep the change focused and match the project's style. Commit with messages that reference the task ID.
5. **Test.** Tests must run before any PR is opened, using the project's own test command, plus tests for new behaviour. If tests fail, fix and rerun; if still failing, go to Failure handling.
6. **Open a PR** with `gh pr create`, ready for review against the default branch, titled and described per the conventions. Never merge it, never auto-merge.
7. **Post the PR link** in the originating Slack thread with the Slack MCP, with a one-line summary and test result.
8. **Optional: update ClickUp** via the ClickUp MCP (PR-link comment and/or status change). Off by default; do it only when enabled in the conventions config or requested in the Slack message.

## Failure handling

If planning, tests (after the self-healing attempts) or PR creation fail, post a failure report in the thread with the Slack MCP using `factory.py failure-report` and the format in the conventions: step failed, error summary, what was tried, suggested next action. Do not post a PR link in a failure report, and never post one unless the PR was actually created.

## Rules

- One repo per task; never guess the repo.
- Never push to the default branch, never merge, never deploy.
- Never put secrets or tokens in commits, PRs or Slack.

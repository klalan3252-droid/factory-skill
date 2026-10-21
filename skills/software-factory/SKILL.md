---
name: software-factory
description: Use when Claude is tagged in a Slack thread about a ClickUp task and asked to do the work. Runs the full loop - read the ClickUp task, resolve the repo, plan, implement, test, open a GitHub pull request and report the link back in the same Slack thread.
---

# Software factory

Follow the steps in order. Conventions (branch, PR title/body, failure report, config) are in `${CLAUDE_PLUGIN_ROOT}/docs/conventions.md`; read it first.

Remember the Slack channel and thread timestamp that triggered you; all replies go there.

1. **Read the ClickUp task** with the ClickUp MCP (task ID from the thread, mirrored message or URL). Collect title, description, acceptance criteria, comments, URL.
2. **Resolve the target repo.** Use the repo named in the ClickUp task or the Slack message (`owner/name` or GitHub URL). If none is found, never guess: ask in the thread with the Slack MCP, then stop. Do this before any clone, branch or edit.
3. **Plan.** Clone the repo with `gh repo clone`, study it, and write a short plan mapped to the acceptance criteria. If planning fails, go to Failure handling.
4. **Implement** on a branch named `CU-<task-id>-<short-slug>` created from the default branch. Keep the change focused and match the project's style. Commit with messages that reference the task ID.
5. **Test.** Tests must run before any PR is opened, using the project's own test command, plus tests for new behaviour. If tests fail, fix and rerun; if still failing, go to Failure handling.
6. **Open a PR** with `gh pr create`, ready for review against the default branch, titled and described per the conventions. Never merge it, never auto-merge.
7. **Post the PR link** in the originating Slack thread with the Slack MCP, with a one-line summary and test result.
8. **Optional: update ClickUp** via the ClickUp MCP (PR-link comment and/or status change). Off by default; do it only when enabled in the conventions config or requested in the Slack message.

## Failure handling

If planning, tests or PR creation fail, post a failure report in the thread with the Slack MCP using the format in the conventions: step failed, error summary, what was tried, suggested next action. Do not post a PR link in a failure report, and never post one unless the PR was actually created.

## Rules

- One repo per task; never guess the repo.
- Never push to the default branch, never merge, never deploy.
- Never put secrets or tokens in commits, PRs or Slack.

---
name: factory-workflow
description: Plan, implement, test and open a GitHub PR for a task when Claude is tagged in a Slack thread, then post the PR link back in the thread. Use whenever asked to work on a task from Slack or ClickUp.
allowed-tools: mcp__clickup__*, mcp__slack__*, mcp__github__*, Read, Edit, Write, Bash, Grep, Glob
---

# Slack to PR workflow

Run these steps in order when tagged in a Slack thread (or given a ClickUp task ID).

## Configuration

Read env vars first, then `.factory.json`: `FACTORY_REPO` / `repo`, `FACTORY_BASE_BRANCH` / `baseBranch` (default `main`), `FACTORY_TEST_COMMAND` / `testCommand`, `FACTORY_SLACK_CHANNEL` / `slackChannel`. If the repo is missing, report it (see Failure handling).

## Steps

1. **Read context.** Read the whole Slack thread via the Slack MCP. Find the linked ClickUp task (task ID in the first message, or a ClickUp URL) and read it via the ClickUp MCP: description, comments, acceptance criteria. Acknowledge in the thread that work has started.
2. **Plan.** Write a short plan (files to change, approach, tests) and post it in the thread. If the request is ambiguous, ask in the thread instead of guessing.
3. **Implement on a new branch.** Create `factory/<task-id>-<slug>` from the base branch. Make focused changes in the project's style. Commit with clear messages.
4. **Run the tests.** Use the configured test command, otherwise detect one (`package.json` scripts, `Makefile`, `pyproject.toml`, `Cargo.toml`, `go.mod`). Fix failures you caused and re-run.
5. **Open a pull request** through the GitHub MCP against the base branch, with a description linking the ClickUp task and summarising the plan and test results.
6. **Post the link.** Reply with the PR link in the same Slack thread.
7. **Update ClickUp (optional).** If `updateClickupStatus` is enabled, set the task status (`clickupStatusOnPr`) and/or add a comment with the PR link.

## Checkpoints, pause and resume

State is kept by `node ${CLAUDE_PLUGIN_ROOT}/scripts/factory.js` in `.factory/state/<task-id>.json` (atomic writes, so a crash never corrupts it).

- Before starting: `factory.js next <task-id>`. If it returns `resume`, continue from that step and do not repeat completed ones (reuse saved data such as branch name, thread ts, PR URL). If it returns `wait`, post the reset time in the thread and stop; a scheduled `/factory-skill:work` run picks it up later.
- Around each step (`context`, `plan`, `implement`, `test`, `pr`, `post`, `update`): `factory.js begin <task-id> <step>`, then `factory.js complete <task-id> <step> '<json data>'`. Commit work-in-progress on the branch so implementation survives a pause.
- On a usage or rate limit: `factory.js pause <task-id> <reset ISO time> "usage limit"`, post a short note with the reset time in the thread, and stop. After the reset, resume from the saved step.
- On any other failure: `factory.js fail <task-id> <step> "<reason>"`.
- Before opening a PR, check the checkpoint's `pr` data so a resumed run never opens a duplicate.

## Failure handling

Never fail silently. On any failure (missing config, unauthenticated or erroring MCP server, branch/push problems, failing tests) report the failure and its reason in the Slack thread, say what was completed, and stop.

- Do not open a PR when tests fail, unless `allowPrOnFailingTests` is explicitly true; then mark the PR as a draft and state the failing tests in the PR and the thread.
- If no test command can be found, report that in the thread rather than skipping tests.
- Never merge a PR, deploy or release. Humans review and merge.
- Never print or commit secrets.

---
name: clickup-slack-sync
description: Post newly assigned ClickUp tasks to the configured Slack channel, once each. Use when asked to sync ClickUp tasks to Slack or from the /factory-skill:sync command.
allowed-tools: mcp__clickup__*, mcp__slack__*, Read
---

# ClickUp to Slack sync

Mirror newly assigned ClickUp tasks into Slack. The sync is idempotent: running it repeatedly never posts a task twice.

## Configuration

Read settings from env vars first, then `.factory.json` in the repo root:

| Setting | Env var | `.factory.json` key |
|---|---|---|
| Slack channel | `FACTORY_SLACK_CHANNEL` | `slackChannel` |
| ClickUp list | `FACTORY_CLICKUP_LIST_ID` | `clickupListId` |
| Assignee filter (default: me) | - | `clickupAssignee` |

If the Slack channel or ClickUp list is missing, stop and tell the user which setting is missing. Do not guess.

## Steps

1. Using the ClickUp MCP, list open tasks in the configured list that are assigned (to the assignee filter).
2. For each task, fetch its comments and custom fields. **Skip** the task if it already carries the marker `factory-slack-thread:` (in a comment or a custom field). This is the idempotency check.
3. For each remaining task, post a message to the Slack channel via the Slack MCP containing the task name, ID, assignee, priority, due date, URL and a short description. Include the task ID in the first line so the workflow skill can find it later.
4. Immediately after a successful post, record the Slack thread reference on the ClickUp task as a comment: `factory-slack-thread: <channel-id>/<thread-ts> <permalink>`. Never write the marker before the Slack post succeeds.
5. Finish with a summary: posted N, skipped M (already marked), failed K.

## Failures

If one task fails (Slack or ClickUp MCP error), report it in the summary with the reason, continue with the other tasks, and never write the marker for a task that was not posted. If the MCP server is not authenticated, tell the user to run `/mcp`.

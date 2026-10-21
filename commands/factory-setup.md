---
description: Check that the ClickUp, Slack and GitHub integrations needed by the software factory are available, and optionally post a test mirror update.
---

# Factory setup check

Check each integration and report a table with status `ok` or `missing` and how to fix it:

1. **ClickUp**: call a read-only ClickUp MCP tool (e.g. look up the workspace). Missing if no ClickUp MCP tools exist or the call fails.
2. **Slack**: call a read-only Slack MCP tool (e.g. list channels). Missing if no Slack MCP tools exist or the call fails.
3. **GitHub**: run `gh auth status`. Missing if `gh` is absent or not logged in with `repo` scope.

List every missing integration with the fix from the README. Do not proceed to a test post if anything is missing.

If all are available and the user passes a channel (`$ARGUMENTS`), offer to post a test message to it; when the native ClickUp-Slack integration did not reflect a task update, use the `clickup-slack-mirror` skill to post it.

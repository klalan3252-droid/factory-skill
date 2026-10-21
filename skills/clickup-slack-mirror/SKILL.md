---
name: clickup-slack-mirror
description: Use when a ClickUp task assignment or update has not appeared in the designated Slack channel (the native ClickUp-Slack integration did not mirror it), or when asked to post or reflect a ClickUp task update to Slack.
---

# ClickUp to Slack mirror (fallback)

The native ClickUp Slack integration is the primary mirror. Use this skill only when it did not post.

1. Read the task with the ClickUp MCP (name, assignee, status, URL, description summary).
2. Find the designated channel (given by the user, or `FACTORY_SLACK_CHANNEL`). If none is configured, ask the user and stop.
3. Check recent channel history with the Slack MCP; if the task URL was already posted, do nothing and say so.
4. Otherwise post one message with the Slack MCP:

```text
:clipboard: <task name> (CU-<task-id>)
Assignee: <name> | Status: <status>
<ClickUp URL>
Tag @Claude in this thread to start the factory workflow.
```

5. Report the message link back to the user.

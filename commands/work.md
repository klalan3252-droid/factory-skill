---
description: Manually run the Slack-to-PR workflow for a ClickUp task ID
argument-hint: <clickup-task-id>
---

Run the `factory-workflow` skill for ClickUp task $ARGUMENTS. Use the Slack thread recorded in the task's `factory-slack-thread:` comment as the thread to report in.
Resume or start from the checkpoint (`factory.js next`); if paused until a reset time, report it and stop.

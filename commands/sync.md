---
description: Sync newly assigned ClickUp tasks to the configured Slack channel
---

Run the `clickup-slack-sync` skill now and report its summary.

For polling, run it on an interval, for example `/loop 15m /factory-skill:sync`, or create a recurring job with `/schedule`. The sync skill is idempotent, so repeated runs are safe.

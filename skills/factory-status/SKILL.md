---
name: factory-status
description: Summarize factory state: ClickUp tasks synced to Slack, in-flight branches and open PRs. Use when asked for status, progress or a report.
allowed-tools: mcp__clickup__*, mcp__slack__*, mcp__github__*, Read
---

# Factory status

1. Read configuration (`FACTORY_*` env vars or `.factory.json`).
2. ClickUp MCP: list assigned tasks in the configured list; note which carry a `factory-slack-thread:` marker (posted) and which do not (pending sync).
3. GitHub MCP: list open PRs on the configured repo whose branch starts with `factory/`, with CI/review state.
4. Produce a compact summary: pending sync, in progress, PR open (with links), blocked or failed.
5. If invoked from a Slack thread or asked to post, send it to that thread (or the configured channel) via the Slack MCP; otherwise reply inline.

Report any MCP or config error in the summary instead of omitting that section silently. This skill is read-only apart from the Slack post.

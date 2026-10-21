# factory-skill

A Claude Code plugin that makes Claude act as an autonomous software factory. Tag Claude in a Slack thread about a ClickUp task and it reads the task, resolves the repo, plans, implements, tests, opens a GitHub PR and posts the PR link in the same thread.

No webhook service or custom bot is built: it relies on the existing ClickUp and Slack MCP connectors, the native ClickUp-Slack integration and the Claude Slack app.

## Install

From the plugin marketplace:

```text
/plugin marketplace add klalan3252-droid/factory-skill
/plugin install factory-skill@factory-skill
```

Local install for development:

```bash
git clone https://github.com/klalan3252-droid/factory-skill
claude --plugin-dir ./factory-skill
```

Then run `/factory-setup` to verify the integrations.

## Required integrations

- **ClickUp MCP** connector (read tasks, add comments).
- **Slack MCP** connector (read threads, post messages).
- **Native ClickUp-Slack integration** to mirror tasks into a channel.
- **Claude Slack app** installed in the workspace, so tagging Claude triggers Claude Code.
- **GitHub auth**: `gh auth login`, verify with `gh auth status`.

## Permissions and scopes

| Service | Needed |
| --- | --- |
| Slack | `channels:history`, `channels:read`, `chat:write` (add `groups:history` for private channels) |
| GitHub | `repo` scope, with permission to push branches and create PRs |
| ClickUp | Read tasks; comment on tasks (only for the optional update) |

Never commit tokens; configure them in the connectors or `gh`.

## ClickUp-to-Slack mirroring

1. Create a channel, e.g. `#factory-tasks`, and invite the Claude app.
2. In ClickUp, open the Slack integration (Settings > Integrations > Slack) and connect your workspace.
3. Add a channel subscription for the Space/List, to `#factory-tasks`, enabling task-assigned and status-change notifications.
4. Assign a test task and confirm the post appears.

If an update does not appear, the `clickup-slack-mirror` skill posts it as a fallback.

## Usage and example prompts

In the mirrored task thread:

> @Claude implement this task in klalan3252-droid/my-service

> @Claude take this ClickUp task, the repo is https://github.com/acme/web-app. Update the ClickUp task with the PR link when done.

If no repo is named in the task or message, Claude asks in the thread and stops without cloning, branching or editing.

## Conventions

See [docs/conventions.md](docs/conventions.md): branches `CU-<task-id>-<slug>`, PR titles with the task ID, a PR body template (summary, ClickUp link, test results, notes), and the failure report format (step failed, error summary, what was tried, suggested next action). Tests must pass before a PR is opened; PRs are never auto-merged. The ClickUp update is optional and off by default.

## Out of scope

Hosting webhooks or bots, modifying the Slack app or MCP servers, auto-merge, deployment, CI/CD, multi-repo tasks, and trackers/chat tools other than ClickUp, Slack and GitHub.

## Tests

```bash
python3 -I -m unittest discover -s tests -v
```

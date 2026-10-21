# factory-skill

A Claude Code plugin that makes Claude behave like an autonomous software factory across ClickUp, Slack and GitHub, using only the official hosted MCP servers. There is no webhook relay and no custom Slack bot.

1. **Sync:** tasks assigned in ClickUp are posted to a Slack channel (once each).
2. **Work:** tag Claude in the thread; it plans, implements on a branch, runs tests, opens a PR and posts the link back in the thread.

```
ClickUp --(ClickUp MCP)--> Claude sync skill --(Slack MCP)--> #channel thread
                                                                    |  @Claude
#channel thread <--(Slack MCP)-- workflow skill <-- Claude Slack app
                                     |--(GitHub MCP)--> branch + PR
                                     '--(ClickUp MCP)--> status/comment
```

## Prerequisites

- Claude Code, and a Claude workspace with the Claude Slack app available
- ClickUp, Slack and GitHub accounts with access to the target list, channel and repo
- Node >= 18 (only to run this repo's tests)

## Install the plugin

```
/plugin marketplace add <owner>/factory-skill
/plugin install factory-skill@factory-skill-marketplace
```

## Connect the MCP servers

The plugin's `.mcp.json` declares three hosted servers. No secrets are stored in it. Run `/mcp` and authenticate each one (OAuth in the browser):

| Server | Endpoint | Docs |
|---|---|---|
| clickup | `https://mcp.clickup.com/mcp` | https://developer.clickup.com/docs |
| slack | `https://mcp.slack.com/mcp` | https://api.slack.com/docs |
| github | `https://api.githubcopilot.com/mcp/` | https://docs.github.com/en/copilot/how-tos/provide-context/use-mcp |

Endpoints and auth flows change; follow each vendor's current docs. If you authenticate GitHub with a token instead of OAuth, supply it through an env var (for example `GITHUB_PAT`) in your own settings, never in the repo.

## Install the Claude Slack app

Install the official Claude app from the Slack Marketplace (workspace admin approval may be needed), connect it to your Claude account, then invite it to the channel: `/invite @Claude`. Tagging `@Claude` in a task thread starts the workflow.

## Configure

Environment variables win over the config file.

| Setting | Env var | `.factory.json` key |
|---|---|---|
| Slack channel | `FACTORY_SLACK_CHANNEL` | `slackChannel` |
| ClickUp list | `FACTORY_CLICKUP_LIST_ID` | `clickupListId` |
| Default repo (`owner/name`) | `FACTORY_REPO` | `repo` |
| Base branch | `FACTORY_BASE_BRANCH` | `baseBranch` |
| Test command override | `FACTORY_TEST_COMMAND` | `testCommand` |

Without a test command, it is auto-detected (`package.json`, `Makefile`, `pyproject.toml`, ...). Example `.factory.json` (also in `.factory.example.json`):

```json
{
  "slackChannel": "#dev-tasks",
  "clickupListId": "901234567",
  "clickupAssignee": "me",
  "repo": "my-org/my-repo",
  "baseBranch": "main",
  "testCommand": "npm test",
  "updateClickupStatus": true,
  "clickupStatusOnPr": "in review",
  "allowPrOnFailingTests": false
}
```

## Required scopes and permissions

- **ClickUp:** read tasks and lists in the configured workspace; write comments (the dedupe marker) and, optionally, update task status.
- **Slack:** read channel history and threads; post messages in the channel (for example `channels:history`, `chat:write`, plus `groups:history` for private channels). The bot must be a channel member.
- **GitHub:** read the repo, create branches and push commits, create pull requests (repo contents and pull requests read/write). Merge permission is not needed.

Exact scope names depend on the vendor; check their docs.

## Usage

- `/factory-skill:sync` posts newly assigned tasks to Slack and records `factory-slack-thread: <channel>/<ts> <permalink>` as a ClickUp comment. Tasks with that marker are skipped, so reruns are safe.
- Poll with `/loop 15m /factory-skill:sync` or `/schedule`.
- `/factory-skill:status` summarizes tasks and PRs.
- `/factory-skill:work <task-id>` runs the workflow manually.

On any failure (missing config, failing tests, MCP error) Claude reports the reason in the Slack thread. It does not open a PR when tests fail unless `allowPrOnFailingTests` is set, and it never merges.

## Out of scope

Webhook relays, custom Slack bots, real-time ClickUp triggers, auto-merge/deploy/release, and ClickUp field sync beyond the optional status/comment and the dedupe marker.

## Tests

```
npm test
```

The tests validate JSON manifests, `.mcp.json` (no secrets) and markdown frontmatter, using only Node built-ins.

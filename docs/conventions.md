# Factory conventions

## Branch names

`CU-<task-id>-<short-slug>`, for example `CU-14yqt44akxp-add-login-rate-limit`.
The slug is lowercase, hyphenated, at most 5 words, taken from the task name.

## PR title

Must reference the task ID: `CU-<task-id>: <imperative summary>`.

## PR description template

```markdown
## Summary
<what changed and why, 1-3 bullets>

## ClickUp link
<URL of the ClickUp task>

## Test results
<command run, pass/fail counts, any tests added>

## Notes
<assumptions, follow-ups, risks; "None" if empty>
```

PRs are opened ready for review against the repo's default branch. They are never auto-merged.

## Failure report

Posted in the originating Slack thread when planning, tests or PR creation fail. It never includes a PR link.

```text
:x: Factory run failed
Step failed: <plan | test | open PR>
Error summary: <1-3 lines>
What was tried: <commands/approaches>
Suggested next action: <what a person should do>
```

## Configuration

Optional ClickUp update after the PR is opened. Off by default.

| Setting | Default | Meaning |
| --- | --- | --- |
| `FACTORY_CLICKUP_COMMENT` | `off` | `on` adds a comment with the PR link to the ClickUp task |
| `FACTORY_CLICKUP_STATUS` | unset | Status name (e.g. `in review`) to set on the task; unset means no change |

Set them in the Slack message (e.g. "update ClickUp too") or in the environment.

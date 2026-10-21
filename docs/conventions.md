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

## Checkpoints and resume

State is stored per task as JSON in `~/.factory-skill/state/` (override with `FACTORY_STATE_DIR`), outside the target repo so it is never committed. Writes are atomic (temp file, fsync, rename) and the previous version is kept as `.bak`; a corrupt file falls back to it. Steps: `read_task`, `resolve_repo`, `plan`, `implement`, `test`, `open_pr`, `post_link`, `update_clickup`. Re-tagging Claude in the same thread resumes at the first step not `done`.

## Self-healing and usage limits

The test step allows 3 attempts by default (`--max-attempts`). Each failed attempt feeds the output tail back into a fix. After the last attempt, post a failure report. A usage or rate limit pauses the run, records the reset time in the checkpoint, waits until it passes (plus a 30 second margin, 5 minutes if no reset time is given), then resumes. Limits do not consume attempts.

## Configuration

Optional ClickUp update after the PR is opened. Off by default.

| Setting | Default | Meaning |
| --- | --- | --- |
| `FACTORY_CLICKUP_COMMENT` | `off` | `on` adds a comment with the PR link to the ClickUp task |
| `FACTORY_CLICKUP_STATUS` | unset | Status name (e.g. `in review`) to set on the task; unset means no change |

Set them in the Slack message (e.g. "update ClickUp too") or in the environment.

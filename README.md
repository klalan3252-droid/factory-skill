# factory

An autonomous software factory agent. It polls a GitHub repository for issues carrying a
trigger label, then carries each one to a reviewable pull request with no human steps:
triage, spec, implement (on a feature branch in a fresh clone), test, and open a PR that
says `Closes #N`. The LLM provider is swappable through environment variables alone.

## Setup

Requires Python 3.11+.

```bash
pip install -e '.[dev]'              # core + pytest
pip install -e '.[anthropic]'        # plus a provider SDK: anthropic | openai | google
pytest
```

## Environment variables

| Variable | Required | Meaning |
| --- | --- | --- |
| `GITHUB_TOKEN` | yes | Token with repo access (contents, issues, pull requests). |
| `FACTORY_REPO` | yes | Target repository as `owner/name`. |
| `FACTORY_LABEL` | no | Trigger label (default `factory`). |
| `FACTORY_LLM_PROVIDER` | yes | `anthropic`, `openai` or `google_genai`. |
| `FACTORY_LLM_MODEL` | yes | Model name for that provider. |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GOOGLE_API_KEY` | per provider | Read by the provider SDK, never by this tool. |
| `FACTORY_DRY_RUN` | no | `1`/`true` for dry-run (see below). Default off. |
| `FACTORY_POLL_INTERVAL` | no | Seconds between polls (default `60`). |
| `FACTORY_TEST_COMMAND` | no | Command run in the clone to test the change (default `pytest`). |

## Usage

```bash
export GITHUB_TOKEN=... FACTORY_REPO=acme/widgets
export FACTORY_LLM_PROVIDER=anthropic FACTORY_LLM_MODEL=<model> ANTHROPIC_API_KEY=...

factory run --once                 # process matching issues once and exit
factory run --interval 120         # poll forever, every 120 seconds
factory run --issue 42             # process a single issue by number
factory run --once --dry-run       # plan only: no GitHub writes, no pushes
factory run --once --repo o/r --label bot   # override FACTORY_REPO / FACTORY_LABEL
python -m factory run --once       # equivalent module entrypoint
```

Configuration and LLM errors print a clear message and exit non-zero.

## Switching providers

Change only the environment:

```bash
FACTORY_LLM_PROVIDER=openai       FACTORY_LLM_MODEL=<model> OPENAI_API_KEY=...
FACTORY_LLM_PROVIDER=google_genai FACTORY_LLM_MODEL=<model> GOOGLE_API_KEY=...
```

Install the matching extra (`openai`, `google`, `anthropic`). The model is created with
LangChain's `init_chat_model`; an unknown or missing provider/model is a clear error.

## Safety

- **The default branch is never committed to or pushed to.** The default branch is read
  from the GitHub API; commits and pushes on it are refused in code. Changes go to
  `factory/<number>-<slug>` and the PR targets the default branch.
- Failing tests never produce a ready PR: a draft PR is opened and the failure is
  commented on the issue.
- Dry-run (`--dry-run` or `FACTORY_DRY_RUN=1`) reads and plans, but makes no comments,
  labels, PRs or pushes, and logs what it would have done.
- Edit paths from the model are rejected if they escape the clone or touch `.git`.
- Secrets are never logged: the token is redacted from reprs, errors and git output, and
  is not passed to the test command's environment.
- A failure on one issue is logged and does not stop the others. Issues are labelled
  `in-progress`, `factory-done` or `factory-rejected` and are not reprocessed.
- Test code runs unsandboxed on the host; only run against repositories you trust.

## Architecture

`config` (env) → `llm` (LangChain model) → `pipeline` (orchestration) using `github`
(REST client), `gitops` (git CLI) and `steps/` (`triage`, `spec`, `implement`, `testing`,
`pr`); `cli` is the entrypoint.

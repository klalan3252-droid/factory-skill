# factory-agents

A small autonomous software factory: give it a work item and a local git repo, and LLM agents
plan, implement, verify and commit the change on a new `factory/<slug>` branch for review.

## Install

```bash
pip install -e '.[dev,anthropic]'   # or .[dev,openai]
```

Provider packages are optional extras; a missing one yields a clear error.

## Configuration

CLI flags override environment variables, which override defaults.

| Setting | Flag | Env var | Default |
|---|---|---|---|
| Model (`provider:model`) | `--model` | `FACTORY_MODEL` | none (required) |
| Test command | `--test-cmd` | `FACTORY_TEST_CMD` | `pytest` |
| Max iterations | `--max-iterations` | `FACTORY_MAX_ITERATIONS` | `3` |
| Push branch | `--push` | – | off |

Provider API keys use the usual variables (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, ...).
Examples: `anthropic:claude-sonnet-4-5`, `openai:gpt-4o`. Any provider supported by
LangChain's `init_chat_model` works without code changes.

## Usage

```bash
export ANTHROPIC_API_KEY=...
factory run --repo ~/code/myproj --request "Add a slugify() helper with tests" \
  --model anthropic:claude-sonnet-4-5 --test-cmd "pytest -q"
```

Use `--request-file PATH` instead of `--request` to read the work item from a file.
Exit code: 0 success, 1 tests still failing, 2 configuration/git/provider error.

## Pipeline

1. Refuse to start unless the target is a git repo with a clean working tree.
2. Create `factory/<slug>` off the current HEAD.
3. Planner agent writes a plan from the request and file listing.
4. Implementer agent edits files with `read_file`, `write_file`, `list_files`.
5. Verifier runs the test command; on failure the output is fed back to the implementer,
   up to the max iterations.
6. If tests pass, all changes are committed with a message referencing the request.

## Safety limits

- File tools are confined to the repo: absolute paths, `..`, symlink escapes and anything
  under `.git` are rejected.
- The implementer has no shell; only the verifier runs the test command (no `shell=True`,
  with a timeout, cwd = repo).
- Every loop is bounded (tool steps per agent, outer iterations).
- Never commits failing code: on exhaustion changes stay uncommitted on the branch.
- Never commits to the original branch; nothing is pushed unless `--push`, which runs a plain
  `git push -u origin <branch>`. Force-push is not implemented.

## Tests

```bash
python -m pytest -q
```

Tests use a scripted fake LLM and a temporary git repo; no network or live LLM.

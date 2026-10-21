# factory-skill

Minimal "autonomous software factory" service: a FastAPI app that lists local
tickets and processes one by ID through a small LangGraph workflow
(load ticket -> triage -> plan).

## Setup

```
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
```

## Environment variables

- `ANTHROPIC_API_KEY` – API key for the Anthropic chat model (needed only when processing tickets; not needed for tests).
- `ANTHROPIC_MODEL` – model name (default `claude-sonnet-4-5`).
- `TICKETS_DIR` – directory with `*.json` / `*.md` tickets (default `tickets/`).

Tickets: JSON files with `id`, `title`, `description`; Markdown files with a `#` heading as the title
(id from the filename stem, or `id:` in front matter).

## Run the server

```
uvicorn app.main:app
```

- `GET /tickets` – list ticket summaries
- `GET /tickets/{id}` – full ticket (404 if unknown)
- `POST /tickets/{id}/process` – run the workflow, returns `ticket_id`, `triage`, `plan`

## Tests

```
pytest
```

Tests are offline and use a stubbed LLM.

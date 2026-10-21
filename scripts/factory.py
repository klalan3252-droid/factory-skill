#!/usr/bin/env python3
"""Deterministic helpers for the software-factory plugin (stdlib only).

Skills call this CLI for the parts that must not depend on model judgement:
repo resolution, naming, checkpoints, the self-healing test loop and
usage-limit pause/resume. Run `factory.py --help` for subcommands.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

STEPS = ["read_task", "resolve_repo", "plan", "implement", "test",
         "open_pr", "post_link", "update_clickup"]
DONE = {"done", "skipped"}
EXIT_OK, EXIT_USAGE, EXIT_EXHAUSTED, EXIT_FIX, EXIT_PAUSED = 0, 2, 3, 10, 75
LIMIT_MARGIN = 30       # seconds added after the advertised reset
DEFAULT_BACKOFF = 300   # seconds when a limit is hit with no reset time
TAIL_LINES = 40

# ---------------------------------------------------------------- redaction

_SECRETS = re.compile(
    r"(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_\w{20,}|xox[abprs]-[\w-]{10,}"
    r"|sk-[A-Za-z0-9_-]{20,}|pk_\d+_[A-Z0-9]{20,}|Bearer\s+[\w.-]{20,})")


def redact(text):
    return _SECRETS.sub("[REDACTED]", text)


# ------------------------------------------------------------ repo / naming

_NOT_OWNERS = {"orgs", "settings", "marketplace", "features", "topics", "sponsors"}
_URL = re.compile(r"github\.com[/:]([\w.-]+)/([\w.-]+)", re.I)
_LABELLED = re.compile(
    r"\brepo(?:sitory)?\b[^\n\w/]{0,20}(?:(?:is|=|name[d]?)\s+)?[`<(\[]?"
    r"([\w-]+/[\w.-]+)", re.I)
# Bare "in owner/name" is accepted, but file paths like "in docs/readme.md" are not.
_PREPOSITION = re.compile(r"\b(?:in|on|for|into)\s+[`<(\[]?([A-Za-z][\w-]*/[\w.-]+)(?![\w/-])", re.I)
_FILE_EXT = re.compile(r"\.(?:py|js|ts|tsx|md|json|ya?ml|txt|sh|go|rs|java|css|html)$", re.I)
_NOT_OWNERS |= {"and", "or", "either", "yes", "no"}


def _clean(owner, name):
    name = re.sub(r"\.git$", "", name).rstrip(".")
    return f"{owner}/{name}" if owner.lower() not in _NOT_OWNERS and name else None


def find_repos(text):
    """Distinct owner/name candidates in text, in order of appearance."""
    found = []
    for m in _URL.finditer(text or ""):
        found.append(_clean(m.group(1), m.group(2)))
    for m in _LABELLED.finditer(text or ""):
        owner, _, name = m.group(1).partition("/")
        found.append(_clean(owner, name))
    for m in _PREPOSITION.finditer(text or ""):
        owner, _, name = m.group(1).partition("/")
        if not _FILE_EXT.search(name.rstrip(".")):
            found.append(_clean(owner, name))
    seen, out = set(), []
    for r in found:
        if r and r.lower() not in seen:
            seen.add(r.lower())
            out.append(r)
    return out


def resolve_repo(slack_text, task_text):
    """Slack message wins over the task. Returns (repo|None, reason).

    None means: ask in the thread and stop (nothing named, or ambiguous).
    """
    for label, text in (("slack message", slack_text), ("clickup task", task_text)):
        repos = find_repos(text)
        if len(repos) == 1:
            return repos[0], label
        if len(repos) > 1:
            return None, f"ambiguous in {label}: {', '.join(repos)}"
    return None, "no repo named"


def slug(title, words=5, limit=40):
    parts = re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).split()[:words]
    return "-".join(parts)[:limit].strip("-") or "task"


def branch_name(task_id, title):
    return f"CU-{re.sub(r'^CU-', '', task_id.strip(), flags=re.I)}-{slug(title)}"


def pr_title(task_id, summary):
    return f"CU-{re.sub(r'^CU-', '', task_id.strip(), flags=re.I)}: {summary.strip()}"


def pr_body(summary, clickup_url, test_results, notes=""):
    if not test_results.strip():
        raise ValueError("test results are required before a PR is opened")
    return (f"## Summary\n{summary.strip()}\n\n## ClickUp link\n{clickup_url.strip()}\n\n"
            f"## Test results\n{test_results.strip()}\n\n## Notes\n{notes.strip() or 'None'}\n")


_PR_LINK = re.compile(r"https?://\S*/pull/\d+\S*", re.I)


def failure_report(step, error, tried, next_action):
    """Slack failure report; PR links are stripped so it can never carry one."""
    body = (f":x: Factory run failed\nStep failed: {step}\nError summary: {error.strip()}\n"
            f"What was tried: {tried.strip()}\nSuggested next action: {next_action.strip()}\n")
    return _PR_LINK.sub("[link removed]", redact(body))


# ------------------------------------------------------------- checkpoints

def state_dir():
    return Path(os.environ.get("FACTORY_STATE_DIR")
                or Path.home() / ".factory-skill" / "state")


def state_path(task_id):
    return state_dir() / (re.sub(r"[^\w.-]", "_", task_id) + ".json")


def _read_json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def load(path):
    """Load a checkpoint; fall back to the previous good copy if corrupt."""
    return _read_json(path) or _read_json(str(path) + ".bak")


def save(path, state):
    """Atomic, durable write that keeps the previous version as .bak."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated"] = int(time.time())
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    if path.exists():
        os.replace(path, str(path) + ".bak")
    os.replace(tmp, path)


def init_state(path, task_id, channel="", thread_ts=""):
    """Create a checkpoint, or return the existing one (resume, not restart)."""
    existing = load(path)
    if existing:
        return existing
    state = {"task_id": task_id, "status": "running", "repo": "", "branch": "",
             "pr_url": "", "slack": {"channel": channel, "thread_ts": thread_ts},
             "pause": None,
             "steps": {s: {"status": "pending", "attempts": 0, "note": ""} for s in STEPS}}
    save(path, state)
    return state


def mark(state, step, status, note=""):
    if step not in STEPS:
        raise ValueError(f"unknown step {step}")
    s = state["steps"][step]
    s["status"] = status
    s["note"] = redact(note)[:500]
    if state["status"] == "paused" and status == "running":
        state["status"], state["pause"] = "running", None
    return state


def next_step(state):
    """First step not done/skipped, or None when the run is complete."""
    for s in STEPS:
        if state["steps"][s]["status"] not in DONE:
            return s
    return None


# ------------------------------------------------------ usage limit handling

_LIMIT = re.compile(r"usage limit|rate.?limit|too many requests|\b429\b|limit reached"
                    r"|quota exceeded|overloaded", re.I)
_UNIT = {"h": 3600, "m": 60, "s": 1}


def parse_limit(text, now=None):
    """Return the epoch when work may resume, or None if no limit was hit."""
    if not text or not _LIMIT.search(text):
        return None
    now = time.time() if now is None else now
    m = re.search(r"retry-after:?\s*(\d+)", text, re.I)
    if m:
        return now + int(m.group(1)) + LIMIT_MARGIN
    m = re.search(r"limit reached\s*\|\s*(\d{9,11})\b", text, re.I)
    if m:
        return int(m.group(1)) + LIMIT_MARGIN
    m = re.search(r"(?:try again|retry|resets?)\s+in\s+((?:\d+\s*[a-z]+[\s,and]*)+)", text, re.I)
    if m:
        secs = sum(int(n) * _UNIT[u[0].lower()]
                   for n, u in re.findall(r"(\d+)\s*([hms][a-z]*)", m.group(1), re.I))
        if secs:
            return now + secs + LIMIT_MARGIN
    m = re.search(r"resets?\s+(?:at\s+)?(\d{1,2})(?::(\d\d))?\s*(am|pm)?(?:\s*\(?(utc)\)?)?",
                  text, re.I)
    if m and (m.group(3) or m.group(2)):
        hour, minute = int(m.group(1)) % 12 if m.group(3) else int(m.group(1)), int(m.group(2) or 0)
        if (m.group(3) or "").lower() == "pm":
            hour += 12
        base = datetime.fromtimestamp(now, timezone.utc).replace(tzinfo=None) if m.group(4) else datetime.fromtimestamp(now)
        target = base.replace(hour=hour % 24, minute=minute, second=0, microsecond=0)
        if target <= base:
            target += timedelta(days=1)
        return now + (target - base).total_seconds() + LIMIT_MARGIN
    return now + DEFAULT_BACKOFF


def wait_until(epoch, sleep=time.sleep, clock=time.time, chunk=60, on_tick=None):
    """Sleep in short chunks until epoch; returns seconds actually waited."""
    start = clock()
    while True:
        left = epoch - clock()
        if left <= 0:
            return clock() - start
        if on_tick:
            on_tick(left)
        sleep(min(chunk, left))


# --------------------------------------------------------- self-healing loop

def tail(text, n=TAIL_LINES):
    return "\n".join(text.splitlines()[-n:])


def heal_once(path, step, cmd, max_attempts=3, run=None, now=None):
    """Run cmd once for a step and record the attempt in the checkpoint.

    Result is one of: pass, fix (caller should change code and call again),
    exhausted (attempts used up, post a failure report), paused (usage limit).
    """
    run = run or (lambda c: subprocess.run(c, shell=True, capture_output=True,
                                           text=True, timeout=1800))
    state = load(path)
    rec = state["steps"][step]
    if rec["attempts"] >= max_attempts:
        mark(state, step, "failed", "attempts exhausted")
        state["status"] = "failed"
        save(path, state)
        return {"result": "exhausted", "attempt": rec["attempts"], "output": ""}
    try:
        proc = run(cmd)
        code, out = proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        code, out = 124, "command timed out"
    out = redact(out)
    limit = parse_limit(out, now) if code else None
    if limit:  # a limit hit does not consume an attempt
        state["pause"] = {"reason": "usage limit", "resume_at": limit, "step": step}
        mark(state, step, "paused", tail(out, 5))
        state["status"] = "paused"
        save(path, state)
        return {"result": "paused", "attempt": rec["attempts"], "resume_at": limit,
                "output": tail(out)}
    rec["attempts"] += 1
    if code == 0:
        mark(state, step, "done", f"passed on attempt {rec['attempts']}")
        save(path, state)
        return {"result": "pass", "attempt": rec["attempts"], "output": tail(out)}
    exhausted = rec["attempts"] >= max_attempts
    mark(state, step, "failed" if exhausted else "running", tail(out, 5))
    if exhausted:
        state["status"] = "failed"
    save(path, state)
    return {"result": "exhausted" if exhausted else "fix", "attempt": rec["attempts"],
            "output": tail(out)}


# ----------------------------------------------------------------------- CLI

def _emit(obj):
    print(json.dumps(obj, indent=2, sort_keys=True))


def main(argv=None):
    p = argparse.ArgumentParser(prog="factory.py", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, *args):
        sp = sub.add_parser(name)
        for a in args:
            sp.add_argument(a, **({"default": ""} if a.startswith("--") else {}))
        return sp

    add("resolve-repo", "--slack", "--task")
    add("branch", "--task-id", "--title")
    add("pr-title", "--task-id", "--summary")
    add("pr-body", "--summary", "--clickup-url", "--test-results", "--notes")
    add("failure-report", "--step", "--error", "--tried", "--next")
    add("init", "--task-id", "--channel", "--thread-ts")
    add("show", "--task-id")
    add("next", "--task-id")
    mk = add("mark", "--task-id", "--step", "--status", "--note")
    mk.add_argument("--repo", default="")
    mk.add_argument("--branch", default="")
    mk.add_argument("--pr-url", default="")
    hl = add("heal", "--task-id", "--step", "--run")
    hl.add_argument("--max-attempts", type=int, default=3)
    wt = add("wait", "--task-id")
    wt.add_argument("--chunk", type=int, default=60)
    lp = sub.add_parser("parse-limit")
    lp.add_argument("--text", default=None)
    a = p.parse_args(argv)

    if a.cmd == "resolve-repo":
        repo, why = resolve_repo(a.slack, a.task)
        _emit({"repo": repo, "reason": why})
        return EXIT_OK if repo else EXIT_USAGE
    if a.cmd == "branch":
        print(branch_name(a.task_id, a.title)); return EXIT_OK
    if a.cmd == "pr-title":
        print(pr_title(a.task_id, a.summary)); return EXIT_OK
    if a.cmd == "pr-body":
        try:
            print(pr_body(a.summary, a.clickup_url, a.test_results, a.notes))
        except ValueError as e:
            print(e, file=sys.stderr); return EXIT_USAGE
        return EXIT_OK
    if a.cmd == "failure-report":
        print(failure_report(a.step, a.error, a.tried, a.next)); return EXIT_OK
    if a.cmd == "parse-limit":
        at = parse_limit(sys.stdin.read() if a.text is None else a.text)
        _emit({"limited": at is not None, "resume_at": at})
        return EXIT_PAUSED if at else EXIT_OK

    path = state_path(a.task_id)
    if a.cmd == "init":
        _emit(init_state(path, a.task_id, a.channel, a.thread_ts)); return EXIT_OK
    state = load(path)
    if state is None:
        print(f"no checkpoint for {a.task_id}", file=sys.stderr); return EXIT_USAGE
    if a.cmd == "show":
        _emit(state); return EXIT_OK
    if a.cmd == "next":
        _emit({"next": next_step(state), "status": state["status"],
               "pause": state["pause"]}); return EXIT_OK
    if a.cmd == "mark":
        mark(state, a.step, a.status, a.note)
        for k, v in (("repo", a.repo), ("branch", a.branch), ("pr_url", a.pr_url)):
            if v:
                state[k] = v
        if next_step(state) is None:
            state["status"] = "done"
        save(path, state); _emit(state["steps"][a.step]); return EXIT_OK
    if a.cmd == "heal":
        res = heal_once(path, a.step, a.run, a.max_attempts)
        _emit(res)
        return {"pass": EXIT_OK, "fix": EXIT_FIX, "exhausted": EXIT_EXHAUSTED,
                "paused": EXIT_PAUSED}[res["result"]]
    if a.cmd == "wait":
        pause = state.get("pause")
        if state["status"] != "paused" or not pause:
            _emit({"waited": 0}); return EXIT_OK
        waited = wait_until(pause["resume_at"], chunk=a.chunk)
        state["status"], state["pause"] = "running", None
        mark(state, pause["step"], "running", "resumed after usage limit")
        save(path, state)
        _emit({"waited": int(waited), "resume_step": pause["step"]}); return EXIT_OK
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())

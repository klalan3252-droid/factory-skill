"""Behavioural tests for scripts/factory.py and the eval harness (stdlib only)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import factory  # noqa: E402
import run_evals  # noqa: E402


def cli(*args, state_dir):
    env = dict(os.environ, FACTORY_STATE_DIR=str(state_dir))
    return subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "factory.py"), *args],
                          capture_output=True, text=True, env=env)


class NamingTests(unittest.TestCase):
    def test_pr_title_and_body(self):
        self.assertEqual(factory.pr_title("CU-abc", "add x"), "CU-abc: add x")
        body = factory.pr_body("s", "https://app.clickup.com/t/abc", "5 passed")
        for h in ("## Summary", "## ClickUp link", "## Test results", "## Notes"):
            self.assertIn(h, body)

    def test_pr_body_requires_test_results(self):
        with self.assertRaises(ValueError):
            factory.pr_body("s", "u", "  ")

    def test_failure_report_fields_and_no_pr_link(self):
        r = factory.failure_report("test", "boom", "reran https://github.com/a/b/pull/3", "fix")
        for f in ("Step failed: test", "Error summary:", "What was tried:", "Suggested next action:"):
            self.assertIn(f, r)
        self.assertNotIn("/pull/", r)


class CheckpointTests(unittest.TestCase):
    def test_init_is_idempotent_and_resumes(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.json"
            s = factory.init_state(p, "T")
            factory.mark(s, "read_task", "done")
            factory.save(p, s)
            again = factory.init_state(p, "T")
            self.assertEqual(factory.next_step(again), "resolve_repo")

    def test_corrupt_checkpoint_falls_back_to_backup(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.json"
            s = factory.init_state(p, "T")
            factory.save(p, s)  # creates .bak
            p.write_text("{")
            self.assertEqual(factory.load(p)["task_id"], "T")

    def test_no_temp_file_left_behind(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.json"
            factory.save(p, factory.init_state(p, "T"))
            self.assertFalse(any(n.endswith(".tmp") for n in os.listdir(d)))

    def test_notes_redacted(self):
        with tempfile.TemporaryDirectory() as d:
            s = factory.init_state(Path(d) / "t.json", "T")
            factory.mark(s, "plan", "running", "token ghp_" + "x" * 30)
            self.assertNotIn("ghp_", s["steps"]["plan"]["note"])


class CliTests(unittest.TestCase):
    def test_resolve_repo_exit_code_when_missing(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(cli("resolve-repo", "--slack", "do it", state_dir=d).returncode, 2)
            r = cli("resolve-repo", "--slack", "repo is a/b", state_dir=d)
            self.assertEqual(json.loads(r.stdout)["repo"], "a/b")

    def test_heal_cli_flow_and_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            cli("init", "--task-id", "T", state_dir=d)
            args = ("heal", "--task-id", "T", "--step", "test", "--max-attempts", "2")
            self.assertEqual(cli(*args, "--run", "exit 1", state_dir=d).returncode, 10)
            self.assertEqual(cli(*args, "--run", "exit 1", state_dir=d).returncode, 3)
            nxt = json.loads(cli("next", "--task-id", "T", state_dir=d).stdout)
            self.assertEqual(nxt["status"], "failed")

    def test_heal_cli_pass_marks_done(self):
        with tempfile.TemporaryDirectory() as d:
            cli("init", "--task-id", "T", state_dir=d)
            r = cli("heal", "--task-id", "T", "--step", "test", "--run", "true", state_dir=d)
            self.assertEqual(r.returncode, 0)

    def test_limit_exit_code_and_wait_when_not_paused(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(cli("parse-limit", "--text", "usage limit reached", state_dir=d).returncode, 75)
            self.assertEqual(cli("parse-limit", "--text", "all good", state_dir=d).returncode, 0)
            cli("init", "--task-id", "T", state_dir=d)
            self.assertEqual(json.loads(cli("wait", "--task-id", "T", state_dir=d).stdout)["waited"], 0)

    def test_missing_checkpoint_is_usage_error(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(cli("next", "--task-id", "nope", state_dir=d).returncode, 2)


class LimitTests(unittest.TestCase):
    def test_wait_until_sleeps_in_chunks(self):
        clock, sleeps = {"t": 0.0}, []

        def sleep(s):
            sleeps.append(s)
            clock["t"] += s
        factory.wait_until(150, sleep=sleep, clock=lambda: clock["t"], chunk=60)
        self.assertEqual(sleeps, [60, 60, 30])

    def test_limit_does_not_consume_attempt(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.json"
            factory.init_state(p, "T")
            run = lambda c: SimpleNamespace(returncode=1, stdout="rate limit. Retry-After: 10", stderr="")
            r = factory.heal_once(p, "test", "x", 3, run=run, now=0)
            self.assertEqual(r["result"], "paused")
            self.assertEqual(factory.load(p)["steps"]["test"]["attempts"], 0)


class EvalTests(unittest.TestCase):
    def test_all_evals_pass(self):
        for name, passed, total in run_evals.run():
            self.assertEqual(passed, total, name)

    def test_results_doc_is_current(self):
        sys.argv = ["run_evals.py", "--check"]
        self.assertEqual(run_evals.main(), 0)


if __name__ == "__main__":
    unittest.main()

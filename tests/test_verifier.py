import sys

from factory_agents.verifier import run_tests


def test_pass(tmp_path):
    r = run_tests(f'{sys.executable} -c "print(42)"', tmp_path, timeout=30)
    assert r.passed and not r.timed_out and "42" in r.output


def test_fail_captures_output(tmp_path):
    cmd = f"{sys.executable} -c \"import sys; print('out'); sys.stderr.write('err'); sys.exit(1)\""
    r = run_tests(cmd, tmp_path, timeout=30)
    assert not r.passed
    assert "out" in r.output and "err" in r.output


def test_timeout(tmp_path):
    r = run_tests(f'{sys.executable} -c "import time; time.sleep(10)"', tmp_path, timeout=1)
    assert not r.passed and r.timed_out


def test_missing_command_fails_cleanly(tmp_path):
    r = run_tests("no-such-binary-xyz", tmp_path, timeout=5)
    assert not r.passed


def test_output_truncated(tmp_path):
    r = run_tests(f'{sys.executable} -c "print(\'x\'*500000)"', tmp_path, timeout=30)
    assert len(r.output) < 100_000

import logging

from factory.pipeline import process_issue
from .conftest import branches, git


def test_dry_run_makes_no_writes_or_pushes(make_config, fake_gh, fake_llm, remote, tmp_path, caplog):
    caplog.set_level(logging.INFO)
    main_before = git("--git-dir", str(remote), "rev-parse", "main")
    cfg = make_config(FACTORY_DRY_RUN="1")
    assert cfg.dry_run
    process_issue(fake_gh.issues[0], cfg, fake_gh, fake_llm, workdir_factory=lambda: tmp_path / "w")
    assert fake_gh.writes == []
    assert fake_gh.prs == []
    assert branches(remote) == {"main"}
    assert git("--git-dir", str(remote), "rev-parse", "main") == main_before
    assert "dry" in caplog.text.lower()
    assert "pull request" in caplog.text.lower() or "pr" in caplog.text.lower()


def test_dry_run_reject_does_not_comment(make_config, fake_gh, remote, tmp_path):
    from .conftest import FakeLLM
    process_issue(fake_gh.issues[0], make_config(FACTORY_DRY_RUN="1"), fake_gh,
                  FakeLLM(verdict="reject"), workdir_factory=lambda: tmp_path / "w")
    assert fake_gh.writes == []

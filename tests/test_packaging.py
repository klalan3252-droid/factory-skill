import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_import_and_modules():
    import importlib
    import factory
    for m in ("config", "github", "llm", "pipeline", "cli", "gitops",
              "steps.triage", "steps.spec", "steps.implement", "steps.testing", "steps.pr"):
        importlib.import_module(f"factory.{m}")


def test_pyproject():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    proj = data["project"]
    assert proj["scripts"]["factory"] == "factory.cli:main"
    assert any(d.startswith("pytest") for d in proj["optional-dependencies"]["dev"])
    assert "3.11" in proj["requires-python"]
    extras = proj["optional-dependencies"]
    assert {"anthropic", "openai", "google"} <= set(extras)

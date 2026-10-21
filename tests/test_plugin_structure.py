"""Structural validation for the software-factory Claude Code plugin (stdlib only)."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN_SKILL = ROOT / "skills" / "software-factory" / "SKILL.md"


def read(path):
    return path.read_text(encoding="utf-8")


def frontmatter(path):
    text = read(path)
    m = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not m:
        return None
    fields = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            k, v = line.split(":", 1)
            fields[k.strip()] = v.strip()
    return fields


class ManifestTests(unittest.TestCase):
    def test_plugin_json_valid(self):
        data = json.loads(read(ROOT / ".claude-plugin" / "plugin.json"))
        for key in ("name", "version", "description"):
            self.assertTrue(data.get(key), f"plugin.json missing {key}")

    def test_marketplace_json_valid(self):
        data = json.loads(read(ROOT / ".claude-plugin" / "marketplace.json"))
        self.assertTrue(data.get("name"))
        self.assertTrue(data.get("plugins"))


class SkillTests(unittest.TestCase):
    def test_skills_have_frontmatter(self):
        skills = sorted((ROOT / "skills").glob("*/SKILL.md"))
        self.assertTrue(skills, "no skills found")
        for s in skills:
            fm = frontmatter(s)
            self.assertIsNotNone(fm, f"{s} lacks frontmatter")
            self.assertEqual(fm.get("name"), s.parent.name)
            self.assertTrue(fm.get("description"), f"{s} lacks description")

    def test_commands_have_description(self):
        cmds = sorted((ROOT / "commands").glob("*.md"))
        self.assertTrue(cmds, "no commands found")
        for c in cmds:
            fm = frontmatter(c)
            self.assertIsNotNone(fm, f"{c} lacks frontmatter")
            self.assertTrue(fm.get("description"))

    def test_setup_command_checks_integrations(self):
        text = read(ROOT / "commands" / "factory-setup.md").lower()
        for word in ("clickup", "slack", "github", "gh auth status", "missing"):
            self.assertIn(word, text)

    def test_mirror_skill_exists(self):
        text = read(ROOT / "skills" / "clickup-slack-mirror" / "SKILL.md").lower()
        self.assertIn("slack", text)
        self.assertIn("clickup", text)


class MainSkillTests(unittest.TestCase):
    def setUp(self):
        self.text = read(MAIN_SKILL)
        self.low = self.text.lower()

    def test_description_has_trigger(self):
        fm = frontmatter(MAIN_SKILL)
        d = fm["description"].lower()
        self.assertIn("slack", d)
        self.assertIn("clickup", d)

    def test_ordered_steps_and_tools(self):
        positions = [self.low.find(k) for k in (
            "read the clickup task", "resolve", "plan", "implement",
            "test", "open a pr", "post the pr link")]
        self.assertNotIn(-1, positions)
        self.assertEqual(positions, sorted(positions))
        for tool in ("clickup mcp", "slack mcp", "gh "):
            self.assertIn(tool, self.low)
        self.assertGreaterEqual(len(re.findall(r"^#+ .*step \d", self.low, re.M)
                                    + re.findall(r"^\d+\. ", self.low, re.M)), 7)

    def test_repo_resolution_asks_and_stops(self):
        self.assertIn("ask in the thread", self.low)
        self.assertIn("stop", self.low)
        self.assertRegex(self.low, r"before (any )?(clon|branch|edit)")
        self.assertIn("never guess", self.low)

    def test_tests_before_pr_and_failure_report(self):
        self.assertRegex(self.low, r"tests? (must|are required|before)")
        for field in ("step failed", "error summary", "what was tried",
                      "suggested next action"):
            self.assertIn(field, self.low)
        self.assertRegex(self.low, r"(never|not|no) .{0,40}pr link")

    def test_conventions_and_optional_update(self):
        self.assertIn("CU-", self.text)
        self.assertRegex(self.low, r"never (auto-)?merge")
        self.assertRegex(self.low, r"optional")
        self.assertRegex(self.low, r"off by default")

    def test_references_existing_docs(self):
        refs = re.findall(r"(?:\$\{CLAUDE_PLUGIN_ROOT\}/|\.\./\.\./)(docs/[\w./-]+)", self.text)
        self.assertIn("docs/conventions.md", refs)
        for r in refs:
            self.assertTrue((ROOT / r).is_file(), f"{r} missing")

    def test_conventions_doc_content(self):
        text = read(ROOT / "docs" / "conventions.md").lower()
        for k in ("cu-<", "summary", "clickup link", "test results", "notes",
                  "pr title", "failure report"):
            self.assertIn(k, text)


class ReadmeTests(unittest.TestCase):
    def test_readme_sections(self):
        text = read(ROOT / "README.md").lower()
        for k in ("install", "marketplace", "--plugin-dir", "clickup mcp",
                  "slack mcp", "claude slack app", "gh auth", "channels:history",
                  "chat:write", "channels:read", "mirror", "example"):
            self.assertIn(k, text)

    def test_two_example_prompts(self):
        text = read(ROOT / "README.md")
        self.assertGreaterEqual(len(re.findall(r"^>\s*@Claude", text, re.M)), 2)


if __name__ == "__main__":
    unittest.main()

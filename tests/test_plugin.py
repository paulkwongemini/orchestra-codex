import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = "orchestra-codex"


class PluginTest(unittest.TestCase):
    def setUp(self):
        catalog_path = ROOT / ".agents/plugins/marketplace.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        self.assertEqual(catalog["name"], PLUGIN)
        entry = next(entry for entry in catalog["plugins"] if entry["name"] == PLUGIN)
        self.assertEqual(entry["source"]["source"], "local")
        self.plugin_dir = ROOT / entry["source"]["path"]
        manifest_path = self.plugin_dir / ".codex-plugin/plugin.json"
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(self.manifest["name"], PLUGIN)

    def test_no_lifecycle_hooks(self):
        self.assertEqual(self.manifest["hooks"], {})
        self.assertFalse((self.plugin_dir / "hooks/hooks.json").exists())

    def test_marketplace_resolves_orchestra_skills(self):
        skills = self.plugin_dir / self.manifest["skills"]
        names = ("conductor", "enable", "disable", "setup", "interview", "delegation", "documentation")
        for name in names:
            with self.subTest(skill=name):
                path = skills / name / "SKILL.md"
                prefix, header, _ = path.read_text(encoding="utf-8").split("---\n", 2)
                self.assertEqual(prefix, "")
                self.assertIn(f"name: {name}", header.splitlines())
                self.assertRegex(header, r"(?m)^description: \S")

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

DOCTOR = Path(__file__).resolve().parents[1] / "scripts" / "doctor.py"


class DoctorTest(unittest.TestCase):
    def test_empty_project_remains_empty_and_availability_is_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            project.mkdir()
            codex_home = Path(directory) / "codex-home"
            result = self.run_doctor(project, codex_home)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("gpt-6.2-astra", result.stdout)
            self.assertIn("gpt-6.2-sol", result.stdout)
            self.assertIn("Implementer and writer: gpt-6.2-sol, effort low", result.stdout)
            self.assertIn("availability unknown", result.stdout)
            self.assertIn("/hooks", result.stdout)
            self.assertIn("No work folders", result.stdout)
            self.assertEqual(list(project.iterdir()), [])
            self.assertFalse(codex_home.exists())

    def test_cached_models_and_work_status(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            work = project / ".orchestra" / "demo"
            (work / "tasks").mkdir(parents=True)
            (work / "brief.md").write_text("# Brief", encoding="utf-8")
            (work / "tasks" / "one.md").write_text("# Task", encoding="utf-8")
            codex_home = Path(directory) / "codex-home"
            codex_home.mkdir()
            catalog = {
                "models": [
                    {
                        "slug": "gpt-6.2-sol",
                        "tool_mode": "code_mode_only",
                        "supported_reasoning_levels": [{"effort": "low"}],
                    }
                ]
            }
            (codex_home / "models_cache.json").write_text(
                json.dumps(catalog), encoding="utf-8"
            )
            result = self.run_doctor(project, codex_home)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("gpt-6.2-astra: absent from cached catalog", result.stdout)
            self.assertIn("gpt-6.2-sol: listed in cached catalog", result.stdout)
            self.assertIn("code_mode", result.stdout)
            self.assertIn("demo: brief present, 1 task specs", result.stdout)

    @staticmethod
    def run_doctor(project, codex_home):
        return subprocess.run(
            [sys.executable, str(DOCTOR), str(project)],
            env={**os.environ, "CODEX_HOME": str(codex_home)},
            text=True,
            capture_output=True,
            check=False,
        )


if __name__ == "__main__":
    unittest.main()

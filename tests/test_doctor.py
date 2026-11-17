import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

DOCTOR = Path(__file__).resolve().parents[1] / "scripts" / "doctor.py"


class DoctorTest(unittest.TestCase):
    def test_empty_project_reports_conductor_without_creating_user_files(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            project.mkdir()
            codex_home = Path(directory) / "codex-home"
            result = self.run_doctor(project, codex_home)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("codex is missing from PATH", result.stdout)
            self.assertIn("gpt-6.2-astra", result.stdout)
            self.assertIn("gpt-6.2-sol", result.stdout)
            self.assertIn("Implementer and writer: gpt-6.2-sol, effort low", result.stdout)
            self.assertIn("availability unknown", result.stdout)
            skill = DOCTOR.parents[1] / "skills" / "conductor" / "SKILL.md"
            self.assertIn(f"Packaged conductor skill: {skill}", result.stdout)
            self.assertIn("$orchestra-codex:conductor", result.stdout)
            self.assertIn("No work folders", result.stdout)
            self.assertEqual(list(project.iterdir()), [])
            self.assertFalse(codex_home.exists())

    def test_incomplete_package_reports_missing_conductor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            doctor = root / "scripts" / "doctor.py"
            doctor.parent.mkdir()
            doctor.write_bytes(DOCTOR.read_bytes())
            result = self.run_doctor(root, root / "codex-home", doctor)

            self.assertEqual(result.returncode, 0, result.stderr)
            skill = root / "skills" / "conductor" / "SKILL.md"
            self.assertIn(f"Conductor skill missing: {skill}", result.stdout)

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
            cache = codex_home / "models_cache.json"
            cache.write_text(json.dumps(catalog), encoding="utf-8")
            result = self.run_doctor(project, codex_home)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("gpt-6.2-astra: absent from cached catalog", result.stdout)
            self.assertIn("gpt-6.2-sol: listed in cached catalog", result.stdout)
            self.assertIn("code_mode", result.stdout)
            self.assertIn("demo: brief present, 1 task specs", result.stdout)
            self.assertEqual(list(codex_home.iterdir()), [cache])
            self.assertEqual(json.loads(cache.read_text(encoding="utf-8")), catalog)

    @staticmethod
    def run_doctor(project, codex_home, doctor=DOCTOR):
        return subprocess.run(
            [sys.executable, str(doctor), str(project)],
            cwd=project,
            env={
                **os.environ,
                "CODEX_HOME": str(codex_home),
                "PATH": str(codex_home.parent / "no-tools"),
            },
            text=True,
            capture_output=True,
            check=False,
        )


if __name__ == "__main__":
    unittest.main()

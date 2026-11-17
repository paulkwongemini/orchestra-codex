#!/usr/bin/env python3
"""Report Orchestra Codex setup and work status without changing the project."""

import argparse
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
CONDUCTOR = "gpt-6.2-astra"
WORKER = "gpt-6.2-sol"


def codex_version():
    try:
        result = subprocess.run(
            ["codex", "--version"], capture_output=True, text=True, timeout=5, check=True
        )
    except FileNotFoundError:
        return "unavailable (codex is missing from PATH)"
    except (OSError, subprocess.SubprocessError):
        return "unavailable (codex --version failed)"
    return result.stdout.strip() or "unavailable (codex --version returned no version)"


def show_catalog(codex_home):
    path = codex_home / "models_cache.json"
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
        models = catalog["models"]
    except (OSError, ValueError, KeyError, TypeError):
        models = None

    if not isinstance(models, list):
        print(f"Model availability unknown: no readable Codex CLI catalog at {path}.")
    else:
        entries = {
            model["slug"]: model
            for model in models
            if isinstance(model, dict) and isinstance(model.get("slug"), str)
        }
        for slug in (CONDUCTOR, WORKER):
            status = "listed in cached catalog" if slug in entries else "absent from cached catalog"
            print(f"{slug}: {status}")
        if any(entries.get(slug, {}).get("tool_mode") == "code_mode_only"
               for slug in (CONDUCTOR, WORKER)):
            print("The cache lists a code-mode-only model. In the CLI, enable code_mode for its tools.")
        worker = entries.get(WORKER, {})
        levels = worker.get("supported_reasoning_levels")
        if isinstance(levels, list):
            supported = any(
                isinstance(level, dict) and level.get("effort") == "low"
                for level in levels
            )
            status = "listed" if supported else "absent"
            print(f"Light effort for {WORKER}: low is {status} in the cache.")
    print("Check /model in your Codex session for current model and effort availability.")


def show_work(project):
    root = project / ".orchestra"
    print(f"Work folder: {root}")
    try:
        units = sorted(path for path in root.iterdir() if path.is_dir())
    except FileNotFoundError:
        units = []
    except OSError as error:
        print(f"Work folder unavailable: {error}")
        return

    if not units:
        print("No work folders.")
        return
    sections = (("tasks", "task specs"), ("reports", "reports"), ("reviews", "review records"))
    for unit in units:
        brief = "brief present" if (unit / "brief.md").is_file() else "brief missing"
        counts = []
        for directory, label in sections:
            try:
                count = sum(
                    path.suffix == ".md" and path.is_file()
                    for path in (unit / directory).iterdir()
                )
                counts.append(f"{count} {label}")
            except FileNotFoundError:
                counts.append(f"0 {label}")
            except OSError:
                counts.append(f"{label} unavailable")
        print(f"  {unit.name}: {brief}, {', '.join(counts)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", default=Path.cwd(), type=Path)
    args = parser.parse_args()
    project = args.project.expanduser().resolve()
    if not project.is_dir():
        parser.error(f"project directory does not exist: {project}")

    codex_home = Path(os.environ.get("CODEX_HOME") or "~/.codex").expanduser()
    print("Orchestra Codex doctor")
    print(f"Codex CLI: {codex_version()}")
    print(f"Conductor: {CONDUCTOR}, effort chosen in Codex")
    print(f"Engineer: {WORKER}, defaults to effort high")
    print(f"Analyst: {WORKER}, defaults to effort xhigh")
    print(f"Implementer and writer: {WORKER}, effort low by default, medium available")
    print("Delegation requires Codex multi_agent_v2 with explicit model and effort.")
    show_catalog(codex_home)
    hooks_path = ROOT / "hooks" / "hooks.json"
    status = "present" if hooks_path.is_file() else "missing"
    print(f"Plugin hook file: {status} ({hooks_path})")
    print("Hook trust: check /hooks in the Codex session for this project.")
    show_work(project)


if __name__ == "__main__":
    main()

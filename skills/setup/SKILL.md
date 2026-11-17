---
name: setup
description: Use when the user invokes $orchestra-codex:setup to check the installed plugin and this project's Orchestra work records.
---

Resolve the installed plugin root two levels above this skill's directory (`../..`). From the user project's working directory, run `python3 <plugin-root>/scripts/doctor.py` with the resolved absolute script path.

Show the diagnostic output and explain any missing prerequisite and the next step the diagnostic gives. The check is read-only.

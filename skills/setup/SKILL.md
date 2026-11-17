---
name: setup
description: Use when the user invokes $orchestra-codex:setup for a read-only check of the bundled conductor skill, Codex CLI, cached models, and project work records.
---

Resolve `../../scripts/doctor.py` relative to this skill's directory. From the user's project directory, run `python3` with the script's absolute path. Report the package, CLI, model cache, and work folder findings. The Codex model picker shows the models currently available in the chat.

If Python is unavailable, explain that it is optional for Orchestra and needed only to run this diagnostic or the repository tests. Give `$orchestra-codex:conductor` as the entry point for a `gpt-6.2-astra` chat.

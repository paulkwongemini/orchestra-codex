import hashlib
import os
from pathlib import Path
import re
import shlex
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
from io import StringIO
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import common as c
import guard_main

UNIT = ".orchestra/2026-11-12-login-fix"
SPACE_UNIT = ".orchestra/Work with spaces"
REPORT = SPACE_UNIT + "/reports/T01.md"
REVIEW = SPACE_UNIT + "/reviews/T01.md"
REVIEW_TEXT = """## Scope reviewed
Changes to the working tree.
## Checks run
Ran the unit suite. All tests passed.
## Verdict
Pass.
"""


class CommandTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="orchestra hook tests ")
        self.addCleanup(directory.cleanup)
        self.project = Path(directory.name) / "project with spaces"
        self.project.mkdir()
        environment = patch.dict(os.environ, {"PLUGIN_DATA": str(Path(directory.name) / "state")})
        environment.start()
        self.addCleanup(environment.stop)
        self.data = {
            "session_id": "session-1", "transcript_path": str(Path(directory.name) / "transcript.jsonl"),
            "cwd": str(self.project), "hook_event_name": "PreToolUse", "turn_id": "turn-1",
            "tool_use_id": "call-1", "permission_mode": "default", "model": "gpt-6.2-astra",
            "_project_dir": str(self.project),
        }

    def write(self, relative_path, text, mtime=1000):
        path = self.project / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        os.utime(path, (mtime, mtime))
        return path

    def approval(self, decision_rights, mtime=1000, spoke=True, unit=UNIT):
        brief = self.write(unit + "/brief.md", "## Decision rights\n" + decision_rights, mtime)
        self.assertEqual(self.shell("cat " + shlex.quote(str(brief))), "")
        if spoke:
            c.mark_user_turn(self.data)

    def execute(self, tool, command, role="conductor", workdir=None):
        payload = {**self.data, "tool_name": tool, "tool_input": {"command": command}}
        if workdir is not None:
            payload["cwd"] = workdir
        output = StringIO()
        with redirect_stdout(output):
            try:
                guard_main.check(payload, role)
            except SystemExit as error:
                self.assertIn(error.code, (0, 2))
        if not output.getvalue():
            return ""
        result = json.loads(output.getvalue())["hookSpecificOutput"]
        self.assertEqual(result["hookEventName"], "PreToolUse")
        self.assertEqual(result["permissionDecision"], "deny")
        return result["permissionDecisionReason"]

    def shell(self, command, role="conductor", **kwargs):
        return self.execute("Bash", command, role, **kwargs)

    def edit(self, *hunks, role="conductor", **kwargs):
        command = "\n".join(("*** Begin Patch", *hunks, "*** End Patch"))
        return self.execute("apply_patch", command, role, **kwargs)


class ShellClassifierTest(CommandTest):
    """Principles 3 and 8: the conductor's shell commands"""

    ALLOW = [
        "git status",
        "git --no-pager diff HEAD~1 --stat",
        "git -C sub log --oneline -5",
        "git branch",
        "git branch --show-current",
        "git stash list",
        "npm test",
        "npm run build 2>&1 | tail -20",
        "pytest -x -q > /tmp/orchestra-out.txt 2>&1; tail /tmp/orchestra-out.txt",
        "echo hi > /dev/null",
        'echo "decided without asking" >> %s/decisions.md' % UNIT,
        'echo "Decision within scope" >> %s/decisions.md' % UNIT,
        'grep -n "a > b" src/app.py',
        'grep ">" src/app.py',
        "cut -d'|' -f2 data.txt | sort | uniq -c",
        "sed -n '1,5p' src/app.py",
        "sed -E 's/a/b/' src/app.py",
        'python3 -c "print(1)"',
        "python3 scripts/check.py --strict",
        "rm /tmp/orchestra-foo.txt",
        "cp src/a.py /tmp/orchestra-a.py",
        'find . -name "*.py" -exec grep -l foo {} \\;',
        "codex plugin list",
        "codex --version",
        "echo x | tee /tmp/orchestra-out.txt",
        "echo x | tee -a /dev/null",
        "curl -s https://example.com",
        "curl -sSL https://example.com -o /tmp/orchestra-x.html",
        "echo foo # > src/x.txt",
        "docker compose exec app bin/rails test",
        "bin/rails db:migrate:status",
        "make test",
        "mkdir -p %s/tasks" % UNIT,
        "touch %s/tasks/T02-next.md" % UNIT,
        "ls .orchestra",
        "gh pr view 12",
        "gh api repos/a/b/pulls",
        "pip list",
        "uv run pytest",
        "bundle exec rspec spec/login_spec.rb",
        "yarn test",
        "pacman -Ss ripgrep",
        "awk '{print $1}' data.txt",
        "perl -ne 'print if /x/' data.txt",
        "wget -qO- https://example.com",
        "ls -la && wc -l src/*.py",
        "timeout 60 npm test",
        "env FOO=1 pytest",
        "cd src && npm test",
    ]
    DENY = [
        "echo hi > src/x.txt",
        "echo hi >> README.md",
        "sed -i 's/a/b/' src/app.py",
        "sed -i.bak -e 's/a/b/' src/app.py",
        "cat > src/a.py <<'EOF'\nprint(1)\nEOF",
        "python3 -c \"open('a.txt','w').write('x')\"",
        "python3 - <<'EOF'\nimport os\nos.remove('x')\nEOF",
        "node -e \"require('fs').writeFileSync('a','b')\"",
        "rm -rf build",
        "cp /tmp/orchestra-a.py src/a.py",
        "mv a b",
        "find . -name '*.pyc' -delete",
        "find . -name '*.py' -exec sed -i s/a/b/ {} +",
        "find . -name '*.py' | xargs sed -i 's/a/b/'",
        "find . -type f | xargs rm",
        'bash -c "rm -rf src"',
        "echo $(rm -rf src)",
        'echo "$(sed -i s/a/b/ f)"',
        "echo `rm -rf src`",
        'codex exec "fix it"',
        "codex",
        "cat %s/reports/T01.md" % UNIT,
        "rm %s/reports/T01.md" % UNIT,
        "echo x | tee out.txt",
        "curl -o x.zip https://example.com/x.zip",
        "curl -O https://example.com/x.zip",
        "echo foo#bar; rm -rf src",
        "cd src\nrm x.py",
        "if [ -f x ]; then rm x; fi",
        'for f in *.py; do sed -i s/a/b/ "$f"; done',
        "VAR=1 sudo rm -rf /",
        "awk '{print > \"out.txt\"}' data.txt",
        "perl -pi -e 's/a/b/' data.txt",
        "wget https://example.com/a.zip",
        "vim src/app.py",
        "patch -p1 < fix.diff",
        "truncate -s 0 app.log",
    ]
    ASK = [
        "git push origin main",
        "curl -X POST https://api.example.com -d '{\"a\":1}'",
        "ssh host ls",
        "gh pr create --title x",
        "kubectl apply -f deploy.yaml",
    ]
    NOT_PREAPPROVED = [
        'git commit -m "fix"',
        "git add -A && git commit -m x",
        "git checkout -- src/a.py",
        "git branch -D feature",
        "git branch new-feature",
        "git stash",
        "git reset --hard HEAD~1",
        "npm install lodash",
        "pip install requests",
        "bundle install",
        "yarn",
        "pacman -S ripgrep",
        "go mod tidy",
        "bin/rails db:migrate",
        'echo "unterminated',
    ]

    def test_commands_preserved(self):
        for command in self.ALLOW:
            with self.subTest(command=command):
                self.assertEqual(self.shell(command), "")
        self.write(UNIT + "/reports/T01.md", "STATUS: DONE\n")
        for command in self.DENY + self.ASK + self.NOT_PREAPPROVED:
            with self.subTest(command=command):
                self.assertTrue(self.shell(command))

    def test_nested_cli_and_configuration_changes(self):
        for role in ("conductor", "readonly", "impl"):
            for command in (
                "codex", "codex exec 'start work'", "codex -m gpt-6.2-astra resume",
                "bash -c 'codex plugin remove orchestra-codex'",
                "codex --disable hooks exec hi", "codex apply task-id",
                "printf x > ~/.codex/config.toml", "sed -i s/a/b/ .codex/config.toml",
                "codex --dangerously-bypass-hook-trust exec hi",
            ):
                with self.subTest(role=role, command=command):
                    self.assertTrue(self.shell(command, role))
            self.assertEqual(self.shell("codex --version", role), "")
            self.assertEqual(self.shell("codex mcp list", role), "")
        self.assertTrue(self.shell("sed -i s/a/b/ config.toml", "impl", workdir=str(self.project / ".codex")))

    def test_shell_apply_patch_requires_native_patch(self):
        for role in ("conductor", "readonly", "impl"):
            command = "cat patch.txt | apply_patch"
            self.assertIn("apply_patch", self.shell(command, role))


# Shortened copies of commands that froze a real overnight session
FROZEN_A = ('for f in components browse; do printf "%-14s var()=%s\\n" $f '
            '"$(grep -o \'var(--\' $f.css | wc -l)"; done')
FROZEN_B = ("ls -R .orchestra/2026-11-12-login-fix/files/T02 | head -50; docker exec -w /app app bash -lc "
            "'bin/rails db:prepare db:seed >/dev/null 2>&1; bin/rails runner \"puts Book.count\"'")
FROZEN_C = """docker exec -w /app app bash -lc '
bin/rails db:migrate:status 2>&1 | tail -3; bin/rails test 2>&1 | tail -2
PW=$(head -c 18 /dev/urandom | base64 | tr -dc "A-Za-z0-9" | head -c 16)
OPERATOR_EMAIL=op.review@example.com OPERATOR_PASSWORD=$PW bin/rails db:seed 2>&1 | tail -1
curl -s -o /tmp/out.html -X POST http://127.0.0.1:3141/session --data-urlencode "email_address=op.review@example.com"
bin/rails db:seed:replant 2>&1 | tail -1'"""
FROZEN_D = """docker exec -w /app app bash -lc '
set -e
rm -rf tmp/final; mkdir -p tmp/final/shots
DATABASE_URL=sqlite3:tmp/final/full.sqlite3 bin/rails db:prepare >/dev/null 2>&1
DATABASE_URL=sqlite3:tmp/final/full.sqlite3 bin/rails db:seed 2>&1 | tail -1'
cd tmp/final/shots && for s in home shelf; do for w in 390 1280; do printf "%s-%s: AE=%s\\n" $s $w "$(compare -metric AE $s-$w-a.png $s-$w-b.png null: 2>&1 | head -1 | cut -d' ' -f1)"; done; done"""

KEY_COMMANDS = {
    "data": "bin/rails db:migrate",
    "deps": "npm install lodash",
    "git": 'git commit -m "x"',
    "push": "git push origin main",
    "github": "gh pr create --title x",
    "http": "curl -X POST https://api.example.com -d a=1",
    "ssh": "ssh host ls",
    "deploy": "kubectl apply -f deploy.yaml",
}


class AuthorizationTest(CommandTest):
    def test_keys_cover_independent_categories(self):
        for key, allowed in KEY_COMMANDS.items():
            with self.subTest(key=key):
                self.approval(f"Pre-approved: {key}")
                self.assertEqual(self.shell(allowed), "")
                for other, command in KEY_COMMANDS.items():
                    if key != other:
                        self.assertIn(f"`{other}`", self.shell(command))
        self.approval("Pre-approved: git")
        combined = "git add file && git push origin main"
        self.assertIn("`push`", self.shell(combined))
        self.approval("Pre-approved: git, push")
        self.assertEqual(self.shell(combined), "")

    def test_categories_require_user_turn_after_brief(self):
        self.approval("Pre-approved: data", spoke=False)
        self.assertIn("user turn", self.shell(KEY_COMMANDS["data"]))
        self.approval("Pre-approved: data")
        self.write(UNIT + "/brief.md", "## Decision rights\nPre-approved: data", mtime=4_000_000_000)
        self.assertIn("after the user last spoke", self.shell(KEY_COMMANDS["data"]))

    def test_data_with_production_requires_user_action_even_with_approval(self):
        self.approval("Pre-approved: data")
        for command in (
            "RAILS_ENV=production bin/rails db:migrate", "bin/rails db:migrate -e production",
            "RACK_ENV='prod' bundle exec rake db:migrate",
            'NODE_ENV="production" npx prisma migrate deploy',
            "APP_ENV=prod alembic upgrade head", "DJANGO_ENV=production python manage.py migrate",
            "bin/rails db:seed --env=production", "bin/rails db:migrate --environment production",
            "docker exec -e RAILS_ENV=production app bin/rails db:migrate",
        ):
            with self.subTest(command=command):
                self.assertIn("production", self.shell(command))
                self.assertIn("production", self.shell(command, "impl"))
        self.assertEqual(self.shell("RAILS_ENV=staging bin/rails db:migrate"), "")

    def test_once_approved_command_requires_the_same_arguments_and_working_directory(self):
        command = "RAILS_ENV=production bin/rails db:migrate"
        reason = self.shell(command)
        code = re.search(r"orchestra approve ([a-f0-9]+)", reason)
        self.assertIsNotNone(code)
        self.assertTrue(c.approve_reply(self.data, code[1]))
        self.assertTrue(self.shell(command + " --other-argument"))
        self.assertTrue(self.shell(command, workdir=str(self.project / "src")))
        self.assertEqual(self.shell(command), "")
        self.assertIn("orchestra approve", self.shell(command))

    def test_child_git_is_read_only_even_with_preapproval(self):
        self.approval("Pre-approved: git, push")
        for role in ("readonly", "impl"):
            for command in ("git push origin main", "git fetch origin", "git commit -m x", "git reflog expire --all"):
                self.assertIn("git", self.shell(command, role).lower())
            self.assertEqual(self.shell("git status", role), "")
            self.assertEqual(self.shell("git reflog show HEAD", role), "")

    def test_loopback_curl_does_not_require_writing_requests_key(self):
        for target in ("http://localhost:3000/", "http://127.0.0.1:3000/", "http://[::1]:3000/"):
            self.assertEqual(self.shell(f"curl -s -X POST {target} -d a=1"), "")
        for target in ("https://localhost.example.com/", "https://localhost@example.com/", "https://127.0.0.1.nip.io/"):
            self.assertIn("`http`", self.shell(f"curl -s -X POST {target} -d a=1"))

    def test_multiline_shell_parser_regressions(self):
        self.assertEqual(self.shell(FROZEN_A), "")
        for command in (FROZEN_B, FROZEN_C, FROZEN_D):
            self.assertIn("`data`", self.shell(command))
        self.approval("Pre-approved: data")
        for command in (FROZEN_A, FROZEN_B, FROZEN_C, FROZEN_D):
            self.assertEqual(self.shell(command), "")

    def test_searches_do_not_trigger_data_gate(self):
        for command in (
            'grep -rn "db:seed" README.md', 'git log --grep "db:migrate"',
            'git -C sub diff -G"db:seed"', '''echo "$(grep -c 'db:seed' README.md)"''',
            'timeout 5 rg "manage.py migrate" .', "find . -name '*.md' -exec grep -l db:seed {} +",
        ):
            self.assertEqual(self.shell(command), "")
        for command in (
            'grep -q x f && bin/rails db:migrate', "rg --pre='bin/rails db:migrate' x",
            "git -c core.pager='bin/rails db:migrate' log", 'echo "run bin/rails db:seed first"',
        ):
            self.assertIn("`data`", self.shell(command))


class PatchTest(CommandTest):
    def test_conductor_validates_every_hunk_and_both_move_paths(self):
        allowed = "*** Add File: " + UNIT + "/decisions.md\n+Decision"
        forbidden = "*** Delete File: source.py"
        self.assertEqual(self.edit(allowed), "")
        self.assertIn("source.py", self.edit(allowed, forbidden))
        self.assertIn("source.py", self.edit(
            f"*** Update File: {UNIT}/decisions.md\n*** Move to: source.py"
        ))
        self.assertIn("source.py", self.edit(
            f"*** Update File: source.py\n*** Move to: {UNIT}/decisions.md"
        ))

    def test_authorized_path_with_spaces_uses_tool_workdir(self):
        self.approval("Conductor writes: docs/Project Notes.md")
        self.assertEqual(self.edit("*** Add File: Project Notes.md\n+notes", workdir=str(self.project / "docs")), "")
        self.assertEqual(self.shell("printf notes > 'Project Notes.md'", workdir=str(self.project / "docs")), "")
        self.assertIn("Project Notes", self.edit("*** Add File: Project Notes.md\n+notes"))
        self.assertIn("Secret", self.edit("*** Add File: docs/Secret.md\n+notes"))

    def test_native_patch_keeps_leading_spaces_in_a_filename(self):
        self.assertIn("You cannot edit", self.edit(f"*** Add File:  {UNIT}/decisions.md\n+text"))

    def test_work_records_symlink_does_not_grant_project_write_access(self):
        source = self.project / "src"
        source.mkdir()
        (self.project / ".orchestra").symlink_to(source, target_is_directory=True)
        self.assertIn("You cannot edit", self.edit("*** Add File: src/main.py\n+print(1)"))

    def test_patch_path_treats_unicode_line_separator_as_a_literal_character(self):
        self.approval("Conductor writes: notes.md")
        self.assertIn("You cannot edit", self.edit("*** Add File: notes.md\u2028extra.md\n+text"))

    def test_shell_checks_paths_after_working_directory_changes(self):
        self.approval("Conductor writes: Project Notes.md")
        self.assertTrue(self.shell("cd docs && printf x > 'Project Notes.md'"))
        self.assertTrue(self.shell("(cd docs; printf x > 'Project Notes.md')"))
        self.assertTrue(self.shell("cd - && printf x > 'Project Notes.md'"))

    def test_directory_mutation_cannot_delete_or_move_every_report(self):
        self.write(REPORT, "STATUS: DONE\n")
        self.assertTrue(self.shell("rm -rf " + shlex.quote(SPACE_UNIT)))
        self.assertTrue(self.shell("rm -rf .orchestra", "impl"))

    def test_canonical_patch_keeps_report_writes_with_workers(self):
        self.assertIn("report", self.edit(f"*** Add File: {REPORT}\n+STATUS: DONE").lower())
        self.assertIn("report", self.edit(f"*** Add File: {REPORT}\n+STATUS: DONE", role="impl").lower())
        self.assertEqual(self.edit("*** Add File: src/main.py\n+print(1)", role="impl"), "")
        self.assertIn("src/main.py", self.edit("*** Add File: src/main.py\n+print(1)", role="readonly"))

    def test_worker_owns_only_the_assigned_task_records(self):
        self.data["_assignment"] = {"unit": str(self.project / SPACE_UNIT), "tid": "T01", "role": "analyst"}
        for role in ("readonly", "impl"):
            for file in (REPORT, SPACE_UNIT + "/files/T01/out.txt"):
                self.assertEqual(self.edit(f"*** Add File: {file}\n+text", role=role), "")
                self.assertEqual(self.shell("printf text > " + shlex.quote(file), role), "")
            for file in (SPACE_UNIT + "/reports/T02.md", SPACE_UNIT + "/files/T02/out.txt", UNIT + "/reports/T01.md"):
                self.assertTrue(self.edit(f"*** Add File: {file}\n+text", role=role))
                self.assertTrue(self.shell("printf text > " + shlex.quote(file), role))

    def test_invalid_tool_payload_does_not_silently_pass(self):
        self.assertTrue(self.execute("apply_patch", ""))
        self.assertTrue(self.execute("Bash", None))
        self.assertTrue(self.shell("printf __Q0__ > source.py"))

    def test_writing_brief_selects_the_work_folder(self):
        brief = UNIT + "/brief.md"
        self.assertEqual(self.edit(f"*** Add File: {brief}\n+## Decision rights"), "")
        self.assertEqual(c.active_work(self.data), str(self.project / UNIT))


class ReportReadTest(CommandTest):
    def test_only_a_standalone_cat_can_open_a_report(self):
        path = self.write(REPORT, "STATUS: DONE\n", 1000)
        command = "cat " + shlex.quote(str(path))
        self.assertIn("review", self.shell(command))
        self.write(REVIEW, REVIEW_TEXT, 2000)
        self.assertEqual(self.shell(command), "")
        self.assertEqual(self.shell("cat -- " + shlex.quote(REPORT)), "")
        for other in (
            command + " | head -n 1", command + " && git status",
            "head " + shlex.quote(REPORT), "cat < " + shlex.quote(REPORT),
            "cat " + shlex.quote(REPORT) + " README.md",
            "bash -c " + shlex.quote(command), "echo $(" + command + ")",
            "cat " + shlex.quote(str(path.parent)) + "/*.md",
            "head T01.md", "cd " + shlex.quote(str(path.parent)) + " && cat T01.md",
        ):
            with self.subTest(command=other):
                self.assertIn("report", self.shell(other, workdir=str(path.parent)).lower())
        self.assertEqual(self.shell("cat T01.md", workdir=str(path.parent)), "")
        self.assertIn("report", self.shell("grep -R completed .").lower())
        self.assertIn("report", self.shell("report=" + shlex.quote(REPORT) + '; cat "$report"').lower())

    def test_review_needs_complete_new_evidence_in_same_work_folder(self):
        self.write(REPORT, "STATUS: DONE\n", 2000)
        command = "cat " + shlex.quote(REPORT)
        other_review = self.write(UNIT + "/reviews/T01.md", REVIEW_TEXT, 3000)
        self.assertIn("no review", self.shell(command))
        review = self.project / REVIEW
        review.parent.mkdir(parents=True)
        review.symlink_to(other_review)
        self.assertIn("no review", self.shell(command))
        review.unlink()
        self.write(REVIEW, REVIEW_TEXT, 1000)
        self.assertIn("older", self.shell(command))
        self.write(REVIEW, REVIEW_TEXT, 2000)
        self.assertIn("same timestamp", self.shell(command))
        self.write(REVIEW, REVIEW_TEXT.replace("Ran the unit suite. All tests passed.", "none"), 3000)
        self.assertIn("Checks run", self.shell(command))
        self.write(REVIEW, REVIEW_TEXT, 3000)
        self.assertEqual(self.shell(command), "")
        self.write(REPORT, "STATUS: DONE\nReworked.", 4000)
        self.assertIn("older", self.shell(command))

    def test_status_and_analyst_exceptions(self):
        for status in ("BLOCKED", "FAILED"):
            self.write(REPORT, f"STATUS: {status}\n")
            self.assertEqual(self.shell("cat " + shlex.quote(REPORT)), "")
        path = self.write(REPORT, "STATUS: DONE\n")
        c.save_meta(self.data, str(self.project / SPACE_UNIT), "T01", {
            "kind": "readonly", "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
        self.assertEqual(self.shell("cat " + shlex.quote(REPORT)), "")
        self.assertEqual(self.shell("cat " + shlex.quote(REPORT), "readonly"), "")
        self.write(UNIT + "/reports/T01.md", "STATUS: DONE\n")
        self.assertIn("review", self.shell(f"cat {UNIT}/reports/T01.md"))
        self.write(REPORT, "STATUS: DONE\nRewritten.")
        self.assertIn("review", self.shell("cat " + shlex.quote(REPORT)))


if __name__ == "__main__":
    unittest.main()

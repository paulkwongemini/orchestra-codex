"""Replay Codex local hook events in a project with no user configuration."""
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ASTRA = "gpt-6.2-astra"
SOL = "gpt-6.2-sol"
TASK = ".orchestra/login/tasks/T01-login.md"
REPORT = ".orchestra/login/reports/T01.md"


def sections(*headings):
    return "".join(f"## {heading}\nFixture for {heading}.\n\n" for heading in headings)


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name, "sample project")
        self.project.mkdir()
        self.env = dict(os.environ, PLUGIN_DATA=str(Path(self.temp.name, "state")), PLUGIN_ROOT=str(ROOT))
        self.root = {"model": ASTRA, "session_id": "session-A", "cwd": str(self.project)}
        self.child = dict(self.root, model=SOL, agent_id="worker-A", agent_type="default")

    def event(self, kind, data=None, **fields):
        payload = dict(self.root if data is None else data, hook_event_name=kind, **fields)
        p = subprocess.run([sys.executable, str(ROOT / "scripts/hook.py")], input=json.dumps(payload),
                           text=True, capture_output=True, cwd=self.project, env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout) if p.stdout.strip() else {}

    def pre(self, tool, args, data=None):
        return self.event("PreToolUse", data, tool_name=tool, tool_input=args).get("hookSpecificOutput", {})

    def denied(self, output):
        self.assertEqual(output.get("permissionDecision"), "deny", output)
        return output["permissionDecisionReason"]

    def cat_skill(self, skill):
        path = ROOT / "skills" / skill / "SKILL.md"
        args = {"command": "cat " + shlex.quote(str(path))}
        self.assertEqual(self.pre("Bash", args), {})
        self.event("PostToolUse", tool_name="Bash", tool_input=args, tool_response=path.read_text())

    def documents(self):
        spec = self.project / TASK
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(sections("Goal", "Scope and limits", "Context", "Acceptance criteria", "If blocked")
                        + "## Report\n" + REPORT)
        brief = spec.parents[1] / "brief.md"
        brief.write_text(sections("Goal", "Out of scope", "Proposed extras", "Constraints",
                                  "Acceptance criteria", "Decision rights"))
        return brief, spec

    def prepare(self):
        self.event("SessionStart", source="startup")
        self.documents()
        self.event("UserPromptSubmit", prompt="I confirm the brief.")
        for skill in ("conductor", "delegation", "documentation"):
            self.cat_skill(skill)

    def spawn(self, role="implementer", effort="low", **overrides):
        args = {"task_name": role + "_t01", "fork_turns": "none", "model": SOL,
                "reasoning_effort": effort, "message": "Read " + TASK}
        return self.pre("collaborationspawn_agent", dict(args, **overrides))

    def child_kickoff(self, role="implementer"):
        cmd = shlex.join(["cat", str(ROOT / "roles" / (role + ".md")), TASK])
        return self.pre("Bash", {"command": cmd}, self.child)

    def test_activation_switch_and_compaction(self):
        sol = dict(self.root, model=SOL)
        self.assertFalse(self.event("SessionStart", sol, source="startup"))
        self.assertFalse(self.pre("Bash", {"command": "touch user-file"}, sol))
        boot = self.event("UserPromptSubmit", prompt="Hello")
        self.assertIn(str(ROOT / "skills/conductor/SKILL.md"), str(boot))
        self.denied(self.pre("Bash", {"command": "pwd"}))
        self.cat_skill("conductor")
        self.assertFalse(self.pre("Bash", {"command": "pwd"}))
        self.event("PostCompact", trigger="manual")
        self.denied(self.pre("Bash", {"command": "pwd"}))
        self.assertFalse(self.pre("Bash", {"command": "touch user-file"}, sol))

    def test_only_an_explicit_user_command_toggles_its_session(self):
        self.event("UserPromptSubmit", prompt="Explain $orchestra-codex:disable")
        self.denied(self.pre("Bash", {"command": "pwd"}))
        self.event("UserPromptSubmit", self.child, prompt="$orchestra-codex:disable")
        self.denied(self.pre("Bash", {"command": "pwd"}))
        self.event("UserPromptSubmit", prompt="$orchestra-codex:disable")
        self.assertFalse(self.pre("Bash", {"command": "touch x"}))
        self.denied(self.pre("Bash", {"command": "pwd"}, dict(self.root, session_id="other")))
        path = ROOT / "skills/enable/SKILL.md"
        self.event("UserPromptSubmit", prompt=f"[$orchestra-codex:enable]({path})")
        self.denied(self.pre("Bash", {"command": "pwd"}))

    def test_routes_require_explicit_role_model_effort_and_unforked_task(self):
        self.prepare()
        for role, effort in (("engineer", "medium"), ("analyst", "high"),
                             ("engineer", "xhigh"), ("analyst", "xhigh"),
                             ("writer", "low"), ("implementer", "low"),
                             ("writer", "medium"), ("implementer", "medium")):
            with self.subTest(role=role):
                self.assertEqual(self.spawn(role, effort, task_name=f"{role}_t01_{effort}"), {})
        for override in ({"model": ASTRA}, {"model": "gpt-6.2-sol-light"}, {"model": ""},
                         {"reasoning_effort": "high"}, {"fork_turns": "all"}, {"fork_turns": ""},
                         {"task_name": "worker"}, {"task_name": "implementer_t02"},
                         {"agent_type": "third_party"}, {"message": "Implement it"}):
            with self.subTest(override=override):
                self.denied(self.spawn(**override))
        self.denied(self.pre("spawn_agent", {"message": TASK}))
        self.denied(self.spawn("analyst", "ultra"))
        self.denied(self.spawn("writer", "high"))

    def test_worker_must_open_its_assignment_before_returning_a_handback(self):
        self.prepare()
        self.assertFalse(self.spawn())
        outcome = self.event("SubagentStop", self.child, last_assistant_message="All done")
        self.assertEqual(outcome.get("decision"), "block")

    def test_brief_confirmation_and_missing_skill_do_not_cross_work_or_role(self):
        self.documents()
        self.event("UserPromptSubmit", prompt="Confirm")
        self.cat_skill("conductor")
        self.denied(self.spawn())
        self.cat_skill("delegation")
        self.assertFalse(self.spawn("analyst", "medium"))
        self.denied(self.spawn())
        self.cat_skill("documentation")
        brief, spec = self.documents()
        self.denied(self.spawn())
        self.event("UserPromptSubmit", self.child, prompt="Confirm")
        self.denied(self.spawn())
        self.event("UserPromptSubmit", prompt="Confirm new brief")
        self.assertFalse(self.spawn())
        spec.write_text("## Goal\nOnly the goal")
        self.denied(self.spawn())

    def test_child_role_is_bound_to_named_spawn_even_with_generic_agent_type(self):
        self.prepare()
        self.assertFalse(self.spawn("analyst", "high"))
        transcript = self.project / "worker.jsonl"
        transcript.write_text(json.dumps({"type": "session_meta", "payload": {
            "id": "worker-A", "agent_path": "/root/analyst_t01"}}) + "\n")
        child = dict(self.child, transcript_path=str(transcript))
        start = self.event("SubagentStart", child)
        self.assertIn("analyst", str(start))
        self.denied(self.pre("Bash", {"command": "touch code.py"}, child))
        nested = self.project / "src"
        nested.mkdir()
        self.denied(self.pre("Bash", {"command": "touch nested.py"}, dict(child, cwd=str(nested))))
        self.denied(self.pre("spawn_agent", {"message": TASK}, child))
        another = dict(child, agent_id="unrelated")
        self.assertFalse(self.pre("Bash", {"command": "pwd"}, dict(another, session_id="unrelated-chat")))

    def test_transcript_free_worker_binds_with_kickoff_and_checks_handback(self):
        self.prepare()
        self.assertFalse(self.spawn())
        self.denied(self.pre("Bash", {"command": "touch code.py"}, self.child))
        self.assertFalse(self.child_kickoff())
        self.assertFalse(self.pre("Bash", {"command": "touch code.py"}, self.child))
        other = dict(self.child, agent_id="unassigned-child")
        self.assertFalse(self.pre("Bash", {"command": "pwd"}, other))
        self.denied(self.pre("collaborationspawn_agent", {}, self.child))
        self.denied(self.pre("collaborationsend_message", {"target": "/root", "message": "Narrative"}, self.child))
        report = self.project / REPORT
        report.parent.mkdir()
        handback = "STATUS: DONE\nTASK: T01\nREPORT: " + REPORT
        report.write_text("STATUS: DONE\n## What I verified\nNo checks.")
        self.assertEqual(self.event("SubagentStop", self.child, last_assistant_message=handback)["decision"], "block")
        record = {"checks": [{"criterion": "output", "kind": "command", "method": "pytest",
                              "result": "PASS", "exit_code": 0, "evidence": "3 passed"}], "unverified": []}
        report.write_text("STATUS: DONE\n## What I verified\n```json\n" + json.dumps(record) + "\n```\n")
        narrative = handback + "\nFILES: I have checked the whole project"
        self.assertEqual(self.event("SubagentStop", self.child, last_assistant_message=narrative)["decision"], "block")
        self.assertFalse(self.event("SubagentStop", self.child, last_assistant_message=handback))
        wrong = handback.replace("T01", "T02")
        self.assertEqual(self.event("SubagentStop", self.child, last_assistant_message=wrong)["decision"], "block")
        self.denied(self.pre("Bash", {"command": "cat " + REPORT}))
        review = report.parents[1] / "reviews/T01.md"
        review.parent.mkdir()
        review.write_text("## Scope reviewed\nlogin.py\n## Checks run\npytest verified all 3 acceptance cases\n## Verdict\nPass\n")
        self.assertFalse(self.pre("Bash", {"command": "cat " + REPORT}))

    def test_confirm_one_specific_outbound_command_once(self):
        self.prepare()
        command = {"command": "git push origin main"}
        reason = self.denied(self.pre("Bash", command))
        reply = re.search(r"orchestra approve [a-f0-9]+", reason).group()
        self.event("UserPromptSubmit", self.child, prompt=reply)
        self.denied(self.pre("Bash", command))
        self.event("UserPromptSubmit", prompt=reply)
        self.denied(self.pre("Bash", {"command": "git push origin other"}))
        self.assertFalse(self.pre("Bash", command))
        self.denied(self.pre("Bash", command))

    def test_analyst_result_is_readable_only_for_the_accepted_revision(self):
        self.prepare()
        self.assertFalse(self.spawn("analyst", "medium"))
        self.assertFalse(self.child_kickoff("analyst"))
        path = self.project / REPORT
        path.parent.mkdir()
        verification = {"checks": [{"kind": "manual", "method": "inspect both callers",
                                     "criterion": "list callers", "evidence": "a() and b()",
                                     "result": "PASS"}], "unverified": []}
        path.write_text("STATUS: DONE\n## What I verified\n```json\n" + json.dumps(verification) + "\n```")
        self.assertFalse(self.event("SubagentStop", self.child,
                                    last_assistant_message="STATUS: DONE\nTASK: T01\nREPORT: " + REPORT))
        self.assertFalse(self.pre("Bash", {"command": "cat " + REPORT}))
        with path.open("a") as out:
            out.write("\nNew findings after the review\n")
        self.denied(self.pre("Bash", {"command": "cat " + REPORT}))


if __name__ == "__main__":
    unittest.main()

"""Authorize Codex worker dispatches and bind each worker to its recorded task on POSIX."""
import json
import os
from pathlib import Path
import re

import common as c
from guard_main import read_line, split_lines

_TASK_NAME = re.compile(r"[a-z][a-z0-9_]{0,119}\Z")
_TASK_REF = re.compile(
    r"(?<![\w./\\])\.orchestra/[^/\r\n`'\"\x00]+/tasks/T[0-9]{2,}-[\w.-]+\.md(?![\w./-])"
)
TASK_EXAMPLE = "`.orchestra/<work>/tasks/T01-short-name.md`"
READONLY = "analyst"
LEGACY_ROLES = {'sol-engineer': 'engineer', 'sol-analyst': 'analyst', 'sol-light-builder': 'implementer', 'sol-light-writer': 'writer'}


def _task_references(message):
    return set(_TASK_REF.findall(message)) if isinstance(message, str) else set()


def _documents_complete(path, headings, label):
    if not path.is_file() or path.resolve() != path:
        c.deny(f"Create the {label} as a regular file at `{path}`.")
    text = c.read_text(path)
    incomplete = c.missing_headings(text, headings) + c.empty_sections(text, headings)
    if incomplete:
        c.deny(f"Complete the {label} sections in `{path}` for " + ", ".join(incomplete) + ".")
    return text


def _validate_task(data, assignment):
    project = Path(c.project_dir(data))
    spec = project / assignment["spec"]
    unit = Path(assignment["unit"])
    if (not spec.is_relative_to(project / ".orchestra") or spec.parent != unit / "tasks"
            or unit.parent != project / ".orchestra" or unit.resolve() != unit):
        c.deny("Write the task spec inside this project's Orchestra work folder.")
    text = _documents_complete(spec, c.TASK_HEADINGS, "task spec")
    report = (unit / "reports" / (assignment["tid"] + ".md")).relative_to(project).as_posix()
    report_section = c.section_body(text, "Report") or ""
    if not re.search(r"(?<![\w./])" + re.escape(report) + r"(?![\w/-]|\.[\w])", report_section):
        c.deny(f"Name `{report}` in the task spec's `## Report` section.")


def _validate_brief(data, assignment):
    if assignment["role"] == READONLY:
        return
    if not (c.session_dir(data) / "skill-documentation").is_file():
        c.deny("Read the Orchestra documentation skill before delegating implementation (Principle 11).")
    brief = Path(assignment["unit"], "brief.md")
    _documents_complete(brief, c.BRIEF_HEADINGS, "brief")
    turn = c.last_user_turn(data)
    if turn is None or brief.stat().st_mtime > turn:
        c.deny(
            f"Show the user the current brief at `{brief}` and obtain a chat reply confirming it "
            "before delegating implementation (Principle 2)."
        )


def _assignment_file(session, name):
    return session / "assignments" / (name + ".json")


def _assignment_named(data, session, name, *, project_scoped=True):
    if not isinstance(name, str) or not _TASK_NAME.fullmatch(name):
        return None
    assignment = c.read_record(_assignment_file(session, name))
    if assignment.get("name") != name or (project_scoped and assignment.get("project") != c.project_dir(data)):
        return None
    # Existing chats retain their task names and worker IDs across upgrades.
    role = assignment["role"]
    assignment["role"] = LEGACY_ROLES.get(role, role)
    return assignment


def _worker_file(session, agent_id):
    return session / "workers" / c.digest(agent_id)


def _known_worker(data, session, agent_id):
    name = c.read_record(_worker_file(session, agent_id)).get("name")
    return _assignment_named(data, session, name, project_scoped=False)


def _record_dispatch(data, assignment):
    c.set_active_work(data, assignment["unit"])
    kind = "readonly" if assignment["role"] == READONLY else "impl"
    # A new dispatch invalidates any earlier analyst's automatic read exception.
    c.save_meta(data, assignment["unit"], assignment["tid"], {"pending_kind": kind})


def check_spawn(data, args):
    """Authorize one named Sol worker and register its immutable task identity."""
    if not isinstance(args, dict):
        c.deny("Pass the roster task name, model, effort and task message to the spawn tool.")
    name = args.get("task_name")
    if not isinstance(name, str) or not _TASK_NAME.fullmatch(name):
        c.deny("Name the worker with its roster role and lowercase task ID, for example `engineer_t01`.")
    roles = [role for role in c.ROSTER if name.startswith(role.replace("-", "_") + "_")]
    if len(roles) != 1:
        c.deny("Choose an Orchestra worker role from the delegation skill.")
    role = roles[0]
    if args.get("model") != c.SOL or args.get("fork_turns") != "none" or args.get("agent_type") is not None:
        c.deny("Spawn the worker with model `gpt-6.2-sol`, `fork_turns: none`, and its roster task name.")
    if args.get("reasoning_effort") not in c.ROSTER[role]:
        c.deny(f"Use an explicit reasoning effort for `{role}` from " + ", ".join(c.ROSTER[role]) + ".")
    refs = _task_references(args.get("message"))
    if len(refs) != 1:
        c.deny(f"Name one task spec such as {TASK_EXAMPLE} in the worker's message (Principle 9).")
    spec = refs.pop()
    tid = c.task_id(spec)
    prefix = role.replace("-", "_") + "_" + tid.lower()
    if name != prefix and not re.fullmatch(re.escape(prefix) + r"_[a-z0-9]+(?:_[a-z0-9]+)*", name):
        c.deny(f"Name this worker `{prefix}` or add a unique underscore suffix to that name.")
    project = c.project_dir(data)
    assignment = {
        "role": role, "name": name, "tid": tid, "spec": spec,
        "unit": str((Path(project) / spec).parents[1]), "project": project,
    }
    _validate_task(data, assignment)
    _validate_brief(data, assignment)
    with c.session_lock(data, "assignments") as session:
        assignment_file = _assignment_file(session, name)
        previous = c.read_record(assignment_file)
        if previous and previous != assignment:
            c.deny(f"Worker name `{name}` already belongs to a different assignment. Use a unique suffix.")
        if not previous:
            c.write_state(assignment_file, json.dumps(assignment))
        _record_dispatch(data, assignment)


def check_followup(data, args):
    """Recheck the current task spec and brief before an assigned worker resumes."""
    if not isinstance(args, dict):
        c.deny("Pass the worker's registered task name or agent ID to the followup tool.")
    target = args.get("target")
    if not isinstance(target, str) or not target:
        c.deny("Use the task name or agent ID of a worker dispatched in this Orchestra chat.")
    with c.session_lock(data, "assignments") as session:
        name = target.removeprefix("/root/")
        assignment = _assignment_named(data, session, name) or _known_worker(data, session, target)
        if assignment is None:
            c.deny("Use the task name or bound agent ID of a worker dispatched in this Orchestra chat.")
        refs = _task_references(args.get("message"))
        if refs and refs != {assignment["spec"]}:
            c.deny(f"This worker is assigned `{assignment['spec']}`. Dispatch a different worker for another task.")
        _validate_task(data, assignment)
        _validate_brief(data, assignment)
        _record_dispatch(data, assignment)


def _transcript_identity(data, agent_id):
    """Read only the trusted session metadata row of this child's transcript."""
    fields = ("agent_transcript_path", "transcript_path") if data.get("hook_event_name") == "SubagentStop" else ("transcript_path",)
    for field in fields:
        transcript = data.get(field)
        if not isinstance(transcript, str) or not transcript:
            continue
        try:
            with open(transcript, encoding="utf-8") as stream:
                record = json.loads(stream.readline())
        except (OSError, ValueError):
            continue
        if not isinstance(record, dict) or record.get("type") != "session_meta":
            continue
        payload = record.get("payload")
        if (isinstance(payload, dict) and payload.get("id") == agent_id
                and payload.get("session_id") in (None, data["session_id"])):
            path = payload.get("agent_path")
            if isinstance(path, str) and path:
                return path
    return None


def _kickoff_paths(data):
    if data.get("hook_event_name") != "PreToolUse" or data.get("tool_name") != "Bash":
        return None
    inputs = data.get("tool_input")
    command = inputs.get("command") if isinstance(inputs, dict) else None
    if not isinstance(command, str):
        return None
    lines = split_lines(command.strip())
    if len(lines) != 1:
        return None
    try:
        _line, substitutions, tokens, comment = read_line(lines[0])
    except (ValueError, IndexError):
        return None
    if substitutions or comment or any(is_operator for _, _, is_operator in tokens):
        return None
    words = [word for _, word, _ in tokens]
    if len(words) == 4 and words[1] == "--":
        words.pop(1)
    if len(words) != 3 or words[0] != "cat" or any(char in word for word in words[1:] for char in "$*?[{~\x00"):
        return None
    if not os.path.isabs(words[1]):
        return None
    return words[1:]


def _project_assignments(data, session):
    for path in (session / "assignments").glob("*.json"):
        assignment = _assignment_named(data, session, path.stem)
        if assignment is not None:
            yield assignment


def _claim(session, agent_id, assignment):
    owner_file = session / "claims" / assignment["name"]
    owner = c.read_text(owner_file)
    if owner and owner != agent_id:
        return None
    c.write_state(owner_file, agent_id)
    c.write_state(_worker_file(session, agent_id), json.dumps({"name": assignment["name"]}))
    return assignment


def assignment_for(data):
    """Return a worker's dispatch record, binding a valid native identity once."""
    agent_id = data.get("agent_id")
    if not isinstance(agent_id, str) or not agent_id:
        return None
    session = c.session_dir(data)
    if not (session / "assignments").is_dir():
        return None
    known = _known_worker(data, session, agent_id)
    if known is not None:
        return known
    identity = _transcript_identity(data, agent_id)
    kickoff = _kickoff_paths(data) if identity is None and data.get("model") == c.SOL else None
    if not identity and kickoff is None:
        return None
    with c.session_lock(data, "assignments") as session:
        known = _known_worker(data, session, agent_id)
        if known is not None:
            return known
        if identity:
            if not identity.startswith("/root/"):
                return None
            assignment = _assignment_named(data, session, identity.removeprefix("/root/"))
            return _claim(session, agent_id, assignment) if assignment else None

        role_path, spec_path = kickoff
        matches = []
        for assignment in _project_assignments(data, session):
            expected_role = str(c.ROOT / "roles" / (assignment["role"] + ".md"))
            expected_spec = str(Path(assignment["project"], assignment["spec"]))
            # The shell reads the paths relative to its actual working directory.
            actual_spec = os.path.realpath(os.path.join(data["cwd"], spec_path))
            owner = c.read_text(session / "claims" / assignment["name"])
            if role_path == expected_role and actual_spec == expected_spec and owner in ("", agent_id):
                matches.append(assignment)
        if len(matches) == 1:
            return _claim(session, agent_id, matches[0])
    return None


def pending_worker(data):
    """True while an unbound Sol child may belong to an Orchestra dispatch."""
    agent_id = data.get("agent_id")
    if not isinstance(agent_id, str) or not agent_id or data.get("model") != c.SOL:
        return False
    session = c.session_dir(data)
    if _known_worker(data, session, agent_id) is not None:
        return False
    identity = _transcript_identity(data, agent_id)
    if identity is not None:
        return identity.startswith("/root/") and _assignment_named(data, session, identity.removeprefix("/root/")) is not None
    if (session / "disabled").exists() or c.read_text(session / "model") != c.ASTRA:
        return False
    return any(not (session / "claims" / task["name"]).exists()
               for task in _project_assignments(data, session))

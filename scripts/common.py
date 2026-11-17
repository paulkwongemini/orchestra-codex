"""Codex hook output, work records and chat-scoped Orchestra state."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ASTRA = "gpt-6.2-astra"
SOL = "gpt-6.2-sol"
ROSTER = {
    "engineer": ("medium", "high", "xhigh"),
    "analyst": ("medium", "high", "xhigh"),
    "implementer": ("low", "medium"),
    "writer": ("low", "medium"),
}

BRIEF_HEADINGS = ["Goal", "Out of scope", "Proposed extras", "Constraints", "Acceptance criteria", "Decision rights"]
TASK_HEADINGS = ["Goal", "Scope and limits", "Context", "Acceptance criteria", "If blocked", "Report"]
REVIEW_HEADINGS = ["Scope reviewed", "Checks run", "Verdict"]
REVIEW_EVIDENCE = "Checks run"
REVIEW_VERDICT = "Verdict"
STATUSES = ("DONE", "BLOCKED", "FAILED")


def emit(result):
    print(json.dumps(result))
    raise SystemExit(0)


def deny(reason):
    emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                 "permissionDecisionReason": "[orchestra-codex] " + reason}})


def context(event, message):
    emit({"hookSpecificOutput": {"hookEventName": event, "additionalContext": message}})


def state_dir():
    if os.environ.get("PLUGIN_DATA"):
        return os.path.realpath(os.environ["PLUGIN_DATA"])
    base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    return str(base / "orchestra-codex")


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def session_dir(data):
    return Path(state_dir(), "sessions", digest(data["session_id"]))


@contextmanager
def session_lock(data, name):
    folder = session_dir(data)
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (folder / (name + ".lock")).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield folder


def write_state(path, text):
    """Publish each record atomically. Parallel dispatches use separate records."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as f:
        try:
            f.write(text)
            f.close()
            os.replace(f.name, path)
        finally:
            Path(f.name).unlink(missing_ok=True)


def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def read_record(path):
    try:
        obj = json.loads(read_text(path))
    except ValueError:
        return {}
    return obj if isinstance(obj, dict) else {}


def project_dir(data):
    return os.path.realpath(data.get("_project_dir") or data["cwd"])


def work_dir(data):
    return os.path.join(project_dir(data), ".orchestra")


def resolve(path, data):
    path = os.path.expanduser(os.path.expandvars(str(path)))
    return os.path.realpath(os.path.join(data.get("workdir") or data["cwd"], path))


def ensure_gitignore(data):
    root = Path(work_dir(data))
    if root.is_symlink():
        return
    root.mkdir(exist_ok=True)
    try:
        with (root / ".gitignore").open("x", encoding="utf-8") as f:
            f.write("*\n")
    except FileExistsError:
        pass


def assigned_task(data):
    assignment = data.get("_assignment")
    return (assignment["unit"], assignment["tid"]) if assignment else None


def active_work(data):
    if assigned_task(data):
        return assigned_task(data)[0]
    path = read_text(session_dir(data) / "work")
    if path and os.path.dirname(path) == work_dir(data) and os.path.realpath(path) == path:
        return path
    return None


def set_active_work(data, unit):
    write_state(session_dir(data) / "work", os.path.realpath(unit))


def mark_user_turn(data):
    write_state(session_dir(data) / "turn", data.get("turn_id") or "")


def last_user_turn(data):
    try:
        return (session_dir(data) / "turn").stat().st_mtime
    except FileNotFoundError:
        return None


def meta_path(unit, tid):
    return Path(state_dir(), "reports", digest(os.path.realpath(unit) + "\0" + tid))


def load_meta(data, unit, tid):
    return read_record(meta_path(unit, tid))


def save_meta(data, unit, tid, record):
    write_state(meta_path(unit, tid), json.dumps(record))


def confirm_command(data, command, reason):
    """An approval is consumed by one retry of the same command in the same context."""
    unit = active_work(data) or ""
    brief = Path(unit, "brief.md") if unit else None
    revision = brief.stat().st_mtime_ns if brief and brief.is_file() else None
    key = digest(json.dumps([project_dir(data), resolve(".", data), unit, revision, command]))
    with session_lock(data, "approvals") as session:
        folder = session / "approvals"
        approved = folder / (key + ".approved")
        if approved.exists():
            approved.unlink()
            return
        pending = folder / (key + ".pending")
        code = read_text(pending)
        if not code:
            code = secrets.token_hex(6)
            write_state(pending, code)
    deny(f"{reason} Show the user the exact command and working directory. "
         f"To authorize one retry, the user can reply exactly: orchestra approve {code}")


def approve_reply(data, code):
    with session_lock(data, "approvals") as session:
        for pending in (session / "approvals").glob("*.pending"):
            if read_text(pending) == code:
                pending.replace(pending.with_suffix(".approved"))
                return True
    return False


def inside(path, base):
    base = os.path.realpath(base)
    return path == base or path.startswith(base.rstrip(os.sep) + os.sep)


def split_unit(path, data):
    """`<project>/.orchestra/<work>/reports/T01.md` -> (`<project>/.orchestra/<work>`, ["reports", "T01.md"]).

    Each piece of work has its own folder under `.orchestra/`. Returns (None, []) for a path
    that is not inside one.
    """
    root = os.path.realpath(work_dir(data))
    if not inside(path, root) or path == root:
        return None, []
    parts = os.path.relpath(path, root).split(os.sep)
    return os.path.join(root, parts[0]), parts[1:]


def in_reports(path, data):
    """True for anything inside a work folder's `reports/` folder."""
    unit, rest = split_unit(path, data)
    return unit is not None and bool(rest) and rest[0] == "reports"


def in_files(path, data):
    """True for anything inside a work folder's `files/` folder, where tasks keep working files."""
    unit, rest = split_unit(path, data)
    return unit is not None and bool(rest) and rest[0] == "files"


def temp_roots(data):
    roots = {"/tmp", "/var/tmp", os.path.realpath(tempfile.gettempdir())}
    scratch = data.get("scratchpad_dir")
    if scratch:
        roots.add(os.path.realpath(scratch))
    return roots


def task_id(filename):
    """`T01-login-fix.md` -> `T01`, `T01.md` -> `T01`."""
    stem = os.path.splitext(os.path.basename(str(filename)))[0]
    return stem.split("-", 1)[0]


def _heading_re(heading):
    return re.compile(
        r"^#{1,6}[ \t]*(?:\d+[.)][ \t]*)?" + re.escape(heading) + r"(?=[ \t]*$|[ \t]*[(:：—-])",
        re.M | re.I,
    )


def section_body(text, heading):
    """The text under a heading, or None when the heading is absent."""
    m = _heading_re(heading).search(text)
    if not m:
        return None
    rest = text[m.end():]
    rest = rest.split("\n", 1)[1] if "\n" in rest else ""
    nxt = re.search(r"^#{1,6}[ \t]", rest, re.M)
    return (rest[:nxt.start()] if nxt else rest).strip()


def missing_headings(text, headings):
    return [h for h in headings if section_body(text, h) is None]


def empty_sections(text, headings):
    return [h for h in headings if section_body(text, h) == ""]


def brief_unit(path, data):
    """The work folder for `<project>/.orchestra/<work>/brief.md`, or None for any other path."""
    unit, rest = split_unit(path, data)
    return unit if rest == ["brief.md"] else None


PREAPPROVAL_KEYS = ("data", "deps", "git", "push", "github", "http", "ssh", "deploy")
PREAPPROVAL_SECTION = "Decision rights"
_PREAPPROVED = re.compile(
    r"^[ \t]*(?:[-*+][ \t]+|\d+[.)][ \t]+)?[*_`]*pre[- ]?approved[*_`]*[ \t]*[:：][*_`]*(.*)$",
    re.I | re.M,
)


def preapproved_keys(text):
    """The keys on the `Pre-approved:` line under `## Decision rights`. Other words are ignored."""
    body = section_body(text, PREAPPROVAL_SECTION)
    keys = set()
    for m in _PREAPPROVED.finditer(body or ""):
        for word in re.split(r"[\s,，、]+", m.group(1)):
            word = word.strip("`*_~()[]{}.;:：'\"").lower()
            if word in PREAPPROVAL_KEYS:
                keys.add(word)
    return keys


_CONDUCTOR_WRITES = re.compile(
    # After the colon, `_` counts as markup only when whitespace follows it, so the underscore
    # that begins an entry such as `_config.yml` stays part of the entry.
    r"^[ \t]*(?:[-*+][ \t]+|\d+[.)][ \t]+)?[*_`]*conductor[ \t]+writes[*_`]*[ \t]*[:：]"
    r"(?:[*_`]*(?=[ \t]|$)|[*`]*)(.*)$",
    re.I | re.M,
)
_GLOB = re.compile(r"[*?\[]")


def conductor_write_entries(text):
    """The entries on the `Conductor writes:` lines under `## Decision rights`, as written."""
    body = section_body(text, PREAPPROVAL_SECTION)
    entries = []
    for m in _CONDUCTOR_WRITES.finditer(body or ""):
        # Only commas separate entries, because a path may contain a space.
        for entry in re.split(r"[,，、]", m.group(1)):
            # Never `_`: it can begin or end a file name, as in `_config.yml` or `__init__.py`.
            entry = entry.strip(" \t\r`'\"")
            if entry and entry.lower() != "none":
                entries.append(entry)
    return entries


def conductor_write_file(entry, data):
    """The real path of the one project file an entry names, or None when it names no such file.

    An entry with a glob character, a directory, a path outside the project, and a path inside
    `.orchestra/` name nothing.
    """
    if _GLOB.search(entry) or entry.endswith(("/", os.sep)):
        return None
    root = project_dir(data)
    try:
        p = os.path.expanduser(entry)
        if not os.path.isabs(p):
            p = os.path.join(root, p)
        p = os.path.realpath(p)
        if os.path.isdir(p):
            return None
    except (OSError, ValueError):
        return None
    if p == root or not inside(p, root) or inside(p, work_dir(data)):
        return None
    return p


def conductor_write_files(text, data):
    """The real paths of the project files the `Conductor writes:` lines of a brief name."""
    files = set()
    for entry in conductor_write_entries(text):
        p = conductor_write_file(entry, data)
        if p:
            files.add(p)
    return files


_STATUS_LINE = re.compile(r"^\W*STATUS\W*[:：]\s*\W*([A-Za-z]+)", re.I)


def read_status(path):
    """The STATUS value on the first line of a report, or an empty string."""
    return status_of(read_text(path))


def status_of(text):
    for line in text.splitlines():
        if line.strip():
            m = _STATUS_LINE.match(line.strip())
            return m.group(1).upper() if m else ""
    return ""

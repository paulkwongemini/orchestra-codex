"""Validate the worker's final Codex message and evidence before handback."""
import hashlib
import json
import os
from pathlib import Path
import re

import common as c

MAX_ATTEMPTS = 3
MAX_LENGTH = 2000
KEY_LINE = re.compile(r"^\W*(STATUS|TASK|REPORT|FILES|QUESTION)\W*[:：]\s*(.*)$", re.I)

FORMAT_HELP = (
    "Your handback or report is incomplete. Write the full report to the report "
    "file that the task spec names, and make your last message exactly the lines below. Add no "
    "explanation or summary.\n"
    "STATUS: DONE | BLOCKED | FAILED\n"
    "TASK: <task ID>\n"
    "REPORT: <the report path from the task spec>\n"
    "FILES: <changed files, separated by commas>\n"
    "QUESTION: <only when BLOCKED: the question the conductor has to answer>\n"
    "Use DONE only when all required checks have passed. Continue checks you can run; "
    "report BLOCKED when you need help to verify, or FAILED when the result still fails."
)


def clean(value):
    return value.strip().strip("*`'\" ").strip()


def parse(text):
    """Returns (fields, lines that are outside the format)."""
    fields, stray, current = {}, [], None
    for raw in (text or "").strip().splitlines():
        line = raw.strip()
        if not line or line.startswith("```"):
            continue
        m = KEY_LINE.match(line)
        if m:
            current = m.group(1).upper()
            if current in fields:
                stray.append(line)
            fields[current] = m.group(2).strip() if current == "FILES" else clean(m.group(2))
        elif current == "QUESTION":
            fields[current] = (fields[current] + "\n" + line).strip()
        elif current == "FILES" and re.match(r"^[-*•]\s+\S", line):
            fields[current] = (fields[current] + "\n" + line).strip()
        else:
            stray.append(line)  # a narrative sentence under FILES lands here too
    return fields, stray


def verification_problems(text):
    """Validate declared results, not tool execution or semantic coverage of the task."""
    body = c.section_body(text, "What I verified") or ""
    block = re.search(r"^```json[ \t]*\n(.*?)\n```[ \t]*$", body, re.S | re.I | re.M)  # text around it is fine
    if not block:
        return ["DONE needs a JSON code block under `## What I verified`, with checks and unverified fields."]
    try:
        verification = json.loads(block.group(1))
    except ValueError:
        return ["The verification code block is not valid JSON."]
    if not isinstance(verification, dict):
        return ["The verification JSON must be an object with checks and unverified fields."]

    problems = []
    if verification.get("unverified") != []:
        problems.append("DONE requires an empty unverified list; required checks cannot remain unverified.")
    checks = verification.get("checks")
    if not isinstance(checks, list) or not checks:
        return problems + ["DONE requires a nonempty checks list."]
    for number, check in enumerate(checks, 1):
        label = "Verification check %d: " % number
        if not isinstance(check, dict):
            problems.append(label + "must be an object.")
            continue
        for key in ("criterion", "method", "evidence"):
            if not isinstance(check.get(key), str) or not check[key].strip():
                problems.append(label + key + " must be nonempty text.")
        if check.get("result") != "PASS":
            problems.append(label + "result must be PASS for DONE.")
        if check.get("kind") == "command":
            if type(check.get("exit_code")) is not int or check["exit_code"] != 0:
                problems.append(label + "a command must have exit_code 0.")
        elif check.get("kind") != "manual":
            problems.append(label + "kind must be command or manual.")
    return problems


def finish(data, assignment):
    message = data.get("last_assistant_message") or ""
    fields, stray = parse(message)
    status = fields.get("STATUS", "").upper()
    problems = []
    if stray or len(message) > MAX_LENGTH:
        problems.append("Put narrative in the report file and return only the status fields.")
    for item in re.split(r"[,\n]", fields.get("FILES", "")):
        path = item.strip().removeprefix("- ").removeprefix("• ")
        if len(path.split()) > 1 and not (path.startswith("`") and path.endswith("`")):
            if not os.path.exists(os.path.join(c.project_dir(data), path)):
                problems.append("FILES takes only paths. Put a path containing spaces in backticks.")
                break
    if status not in c.STATUSES:
        problems.append("Use STATUS: DONE, BLOCKED or FAILED.")
    if (status == "BLOCKED") != bool(fields.get("QUESTION")):
        problems.append("Include a QUESTION exactly when the task is BLOCKED.")
    unit, tid = assignment["unit"], assignment["tid"]
    expected = os.path.join(unit, "reports", tid + ".md")
    supplied = os.path.join(c.project_dir(data), fields.get("REPORT", ""))
    if fields.get("TASK") != tid or os.path.realpath(supplied) != expected:
        problems.append(f"This worker owns task {tid} and must report to {expected}.")
    else:
        raw = Path(expected).read_bytes() if os.path.isfile(expected) else b""
        text = raw.decode("utf-8", "replace")
        if not text or c.status_of(text) != status:
            problems.append("Write a report whose first line matches the status of the handback.")
        elif status == "DONE":
            problems.extend(verification_problems(text))

    if problems:
        retry(data, tid, FORMAT_HELP + "\n" + " ".join(problems))
    kind = "readonly" if assignment["role"] == "analyst" else "impl"
    record = {"kind": kind, "status": status, "agent_id": data["agent_id"]}
    if kind == "readonly":
        record["sha256"] = hashlib.sha256(raw).hexdigest()
    c.save_meta(data, unit, tid, record)
    attempts_file(data).unlink(missing_ok=True)


def attempts_file(data):
    return c.session_dir(data) / "handbacks" / c.digest(data["agent_id"])


def retry(data, label, reason):
    counter = attempts_file(data)
    attempts = int(c.read_text(counter) or "0")
    if attempts >= MAX_ATTEMPTS:
        counter.unlink(missing_ok=True)
        c.emit({"systemMessage": f"Orchestra could not validate the handback for {label} after "
                                 f"{attempts} retries. Review it as unfinished work."})
    c.write_state(counter, str(attempts + 1))
    c.emit({"decision": "block", "reason": reason})

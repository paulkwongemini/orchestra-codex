#!/usr/bin/env python3
"""Require an independent review before the conductor opens a worker report."""
import glob
import hashlib
import os
from pathlib import Path
import re

import common as c

MIN_EVIDENCE = 20  # minimum length of the text under the evidence heading


def find_review(unit, tid):
    folder = Path(unit, "reviews")
    try:
        if folder.resolve() != folder:
            return None
        candidates = [path for path in folder.glob("*.md") if c.task_id(path) == tid
                      and path.is_file() and not path.is_symlink()]
        return max(candidates, key=os.path.getmtime, default=None)
    except OSError:
        return None


def review_problems(review, report):
    if review is None:
        return ["There is no review record."]
    text = c.read_text(review)
    problems = []
    missing = c.missing_headings(text, c.REVIEW_HEADINGS)
    if missing:
        problems.append("The review record is missing required sections: " + ", ".join(missing) + ".")
    evidence = c.section_body(text, c.REVIEW_EVIDENCE)
    if evidence is not None and len(evidence) < MIN_EVIDENCE:
        problems.append(
            "Under `## %s`, write the commands you ran yourself and their results. For a task with "
            "nothing to run, say what you compared against what." % c.REVIEW_EVIDENCE
        )
    if c.section_body(text, c.REVIEW_VERDICT) == "":
        problems.append("`## %s` is empty." % c.REVIEW_VERDICT)
    if os.path.getmtime(review) <= os.path.getmtime(report):
        problems.append(
            "The review record is older than the report or has the same timestamp. Review "
            "the result from the start and write a new review record."
        )
    return problems


REPORT_ACCESS = (
    "Open one report with a standalone `cat <report-path>` command (Principle 7). "
    "Write the independent review record first for a completed implementation report."
)
RECORDS_MENTION = re.compile(r"(?:\.orchestra|\.codex|CODEX_HOME|PLUGIN_DATA)(?:[/}\s]|$)")
REPORTS_MENTION = re.compile(r"""\.orchestra/[^/]+/reports(?:[/\s'"*?\[]|$)""")


def references_reports(name, args, redirect_paths, data):
    """Find direct report paths and common recursive reads of the records."""
    for word in args + redirect_paths:
        if REPORTS_MENTION.search(word):
            return True
        value = word.partition("=")[2] if word.startswith("-") and "=" in word else word
        path = c.resolve(value, data)
        if c.in_reports(path, data):
            return True
        if any(ch in value for ch in "*?[") and any(
            c.in_reports(os.path.realpath(match), data) for match in glob.iglob(path)
        ):
            return True
    # A recursive content search can also reach reports when it names an ancestor.
    recursive = (
        name == "find" and any(a in ("-exec", "-execdir", "-ok", "-okdir") for a in args)
        or name in ("grep", "egrep", "fgrep") and any(
            a.startswith(("--recursive", "--dereference-recursive"))
            or a.startswith("-") and not a.startswith("--") and any(ch in a[1:] for ch in "rR")
            for a in args
        )
        or name == "rg" and any(a in ("--hidden", "--no-ignore", "-uu", "-uuu") for a in args)
    )
    if recursive:
        roots = [c.resolve(a, data) for a in args if not a.startswith("-") and os.path.isdir(c.resolve(a, data))]
        if not roots:
            roots = [c.resolve(".", data)]
        reports_glob = os.path.join(glob.escape(c.work_dir(data)), "*", "reports", "*.md")
        return any(any(c.inside(p, root) for root in roots) for p in glob.iglob(reports_glob))
    return False


def check_read(path, data):
    """Check the one report path already identified by the shell guard."""
    if not os.path.exists(path):
        return
    if not os.path.isfile(path):
        c.deny(REPORT_ACCESS)
    unit, _rest = c.split_unit(path, data)
    tid = c.task_id(path)
    if c.read_status(path) in ("BLOCKED", "FAILED"):
        return
    try:
        meta = c.load_meta(data, unit, tid)
        if meta.get("kind") == "readonly" and meta.get("sha256"):
            if hashlib.sha256(Path(path).read_bytes()).hexdigest() == meta["sha256"]:
                return
        problems = review_problems(find_review(unit, tid), path)
    except OSError:
        problems = ["The report or review changed while the hook was checking it. Retry the read."]
    if not problems:
        return
    c.deny(
        "Review the result independently before reading the report (Principle 7). "
        "Read the diff, run the verification commands yourself, and check the task's acceptance criteria. "
        "Write `.orchestra/%s/reviews/%s.md` with these sections: %s. "
        "Then open the report with a standalone `cat <report-path>` command. %s"
        % (os.path.basename(unit), tid, ", ".join("## " + h for h in c.REVIEW_HEADINGS), " ".join(problems))
    )

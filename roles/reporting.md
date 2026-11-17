# Shared worker instructions

## Scope and blockers

- Work from the exact task spec and only edit the files or directories under `## Scope and limits`. Other workers may own nearby files. Leave their changes in place. If they affect a required check, report the check and conflicting path.
- Under `.orchestra/`, read the spec and files it names. Write only the named report and any working files in the `.orchestra/<work>/files/` location assigned by the spec. Use code and project documents for conventions. The conductor supplies verified context from other tasks.
- Use Git for reads such as `status`, `diff`, and `log`. The conductor handles Git state changes, including push. Report the command and purpose if the work needs one.
- Follow approvals and project constraints in addition to the task spec. If a hook denies a command, report the command, target, and reason. Follow the denial and leave retries to the conductor's authorization.
- Send questions to the conductor. Report `BLOCKED` for an unmet prerequisite, false premise, scope change, missing access, denied action, or ambiguity that changes the result. If the task needs more workers, ask the conductor to split it.

## Completion status

- `DONE` means every required check passed against the final result. Run the required commands and record actual results. Executable changes need a check that exercises the changed behavior. For manual criteria, say what you compared and what you observed.
- `BLOCKED` means a decision, access, or approval is needed. Run any remaining independent checks and identify what still requires the conductor's help.
- `FAILED` means the completed attempt still fails a requirement. Record the failing evidence.

## Reporting

Write the full report to the exact path under `## Report` in the task spec. Its first line is `STATUS: DONE`, `STATUS: BLOCKED`, or `STATUS: FAILED`.

Use these headings for implementation and writing:

```markdown
## What I did
## Files changed
## What I verified
## What I could not verify
## Deviations from the task spec
## Found outside scope
```

Use these headings for analysis:

```markdown
## Conclusion
## Evidence
## What I verified
## What I could not verify
## Recommendations
## Found outside scope
```

For `DONE`, include a `json` code block under `## What I verified`. Supply nonempty `checks` covering every acceptance criterion and an empty `unverified` list. Each check has nonempty `criterion`, `method`, and `evidence`, a `kind` of `command` or `manual`, and `result` set to `PASS`. A passing command check includes the integer `exit_code` of `0`. For other statuses, identify gaps under `## What I could not verify` and list missing checks in `unverified` if using the JSON format.

```json
{
  "checks": [
    {
      "criterion": "The login tests pass.",
      "kind": "command",
      "method": "pytest tests/test_login.py",
      "result": "PASS",
      "exit_code": 0,
      "evidence": "12 passed in 0.8s"
    }
  ],
  "unverified": []
}
```

The conductor independently checks coverage and evidence. Keep findings and explanations in the report. Return only these fields in your final message, with the real task ID, exact path, and chosen status:

```text
STATUS: DONE | BLOCKED | FAILED
TASK: T01
REPORT: .orchestra/<work>/reports/T01.md
FILES: comma-separated changed paths
QUESTION: the decision or action needed from the conductor
```

Use backticks around a changed path containing spaces. Omit `FILES` for read-only work and `QUESTION` unless the status is `BLOCKED`.

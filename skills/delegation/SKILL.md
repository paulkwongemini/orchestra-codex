---
name: delegation
description: Use as the Orchestra Codex conductor to route a worker's first assignment or second rework round.
---

# Choosing the subagent and the effort level

Apply these rules to every initial delegation and again for its second rework round, using the current task spec and review history. Send the first rework to the same worker with its model and effort unchanged. The active conductor is `gpt-6.2-astra` and its effort is chosen by the user. All delegated workers use `gpt-6.2-sol`.

## Step 1. The kind of work

| Deliverable | Role |
| --- | --- |
| Code, configuration, tests, or scripts | Choose an implementation role in step 2 |
| Findings only, including investigation, review, and comparison | `analyst` |
| Bounded document whose outline and substantive points are settled | `writer` |
| Document whose outline depends on unclear facts | Gather findings with `analyst`, then settle the outline and assign the writing |

## Step 2. Choose an implementation role

Give a bounded change to `implementer` when the spec gives the affected files, exact change, existing pattern, and a command that exercises the changed behavior. Give implementation to `engineer` when it requires diagnosis, a substantial implementation decision, or coordinated changes across components. Decide cross-task contracts yourself when the available facts and brief permit it.

Repair missing or ambiguous acceptance criteria before dispatch. Define an observable check for any specific failure mode that matters. If the evidence is too thin to state the implementation problem, use a focused `analyst` task to obtain it. A domain label such as security, concurrency, or migration warrants looking for concrete failure modes and checks.

## Step 3. Choose the effort

The GPT-6.2 prompting guide applies to Astra and Sol. Match effort to investigative depth. A quick survey can use Medium, tracing a suspected cause across systems can warrant High, and interacting causes can warrant Extra High. The Codex model guide identifies Light/Low for quick, bounded tasks and Medium for work that needs planning. For context, the API guide recommends starting new API integrations at `medium`. Orchestra's table is its Codex routing policy. [Prompting GPT-6.2 in Codex](https://learn.chatgpt.com/guides/prompting-gpt-6-2-astra#match-reasoning-effort-to-the-task) · [Codex model guide](https://learn.chatgpt.com/docs/models#pick-a-reasoning-effort) · [GPT-6.2 API migration quickstart](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6.2-astra#migration-quickstart)

| Role | `reasoning_effort` | When to use it |
| --- | --- | --- |
| `implementer`, `writer` | `low` | Default for a direct edit or a document whose facts and structure are settled. |
| `implementer`, `writer` | `medium` | Use when the scope is settled but coordinating implementation steps or reconciling supplied material requires planning. Keep diagnosis and open design decisions with the engineer, analyst, or conductor. |
| `engineer` | `medium` | Use for bounded engineering that requires planning or coordination, such as a known change across modules with clear integration checks. |
| `analyst` | `medium` | A focused survey, catalog, or lookup across the named sources. |
| `engineer`, `analyst` | `high` | Trace a concrete hypothesis across systems or reconcile evidence or trade-offs through several dependent steps. This is the engineer's default. Use it for an analyst following one main hypothesis or a bounded evidence chain. |
| `engineer`, `analyst` | `xhigh` | This is the analyst's default for open-ended deep investigations. Use it when concrete causes or trade-offs interact and checks can distinguish their effects. Use it for engineering when implementation and verification must account for those interactions. |

For second rework, first address what the reviews revealed. Clarify the spec, supply a missing check, or resolve a verification prerequisite when that was the problem. Base the new effort on the reasoning the revised assignment needs. File count, a failed test, or repeated review failure alone gives no evidence of interacting causes. When writing needs research, route the investigation to `analyst`. Settle the outline and hand the verified material to `writer` at the effort the writing itself requires.

### Example decisions

- `implementer` at `low` changes a named cache default using the existing pattern and runs the exact behavior test. `writer` at `low` updates an approved runbook section against a named config and verifies the example command.
- `engineer` at `medium` carries a specified optional field through the API, serializer, and data store. The integration test covers old and new records. `analyst` at `medium` catalogs where callers set that field, with source references.
- `analyst` at `high` traces a suspected stale cache key from write, through invalidation, to the API read. The spec names evidence from each step. Use `engineer` at `high` if the assignment also includes implementing and verifying the correction.
- `engineer` or `analyst` at `xhigh` investigates why a job runs twice when a lease renewal is delayed and a retry overlaps the previous attempt. The spec compares delay alone, retry alone, and both together, and defines how to observe ownership and duplicate execution.

## What follows from the choice in the task spec

- **Implementer:** Name the files, exact changes, pattern, and commands. Include a command that exercises the change. A syntax check alone does not meet that requirement.
- **Writer:** Name the files, approved outline, facts and sources, and comparison or command for each criterion.
- **Engineer:** Give the goal and limits. State separately verifiable criteria for each part and leave implementation choices within those limits to the worker.
- **Analyst:** Give the questions, evidence needed, and acceptance criteria. Put recommendations in the report.
- **High or Extra High investigation:** State the suspected cause or interacting causes, what evidence to trace, and the checks that would distinguish competing explanations. Define when to stop investigating.

## Record and dispatch

Before dispatch, log the task ID, role, exact model, effective effort, and the facts that drove the choice in `.orchestra/<work>/decisions.md`. For first rework record the failure evidence and correction instead of a new routing decision.

Use Codex `spawn_agent` with `fork_turns: "none"`, `model: "gpt-6.2-sol"`, and the explicit `reasoning_effort` from the table. Derive `task_name` by taking the role name and appending `_` plus the lowercase task ID. A replacement can append a unique underscore suffix.

Give the worker two absolute paths. Resolve `../../roles/<role>.md` from the directory containing this installed skill, and resolve the task spec from the project directory. Ask the worker to read and follow those files before starting. Substitute the actual paths for the example paths below.

```json
{
  "task_name": "implementer_t01",
  "fork_turns": "none",
  "model": "gpt-6.2-sol",
  "reasoning_effort": "low",
  "message": "Read your role at /installed/orchestra-codex/roles/implementer.md and your task spec at /project/.orchestra/2026-11-12-login-fix/tasks/T01-session-expiry.md. Follow the role and carry out the spec."
}
```

Use the returned agent ID or task name for `followup_task` and `wait_agent` according to the exposed tools. If explicit routing or unforked worker context is unavailable, report the limitation and stop the affected task.

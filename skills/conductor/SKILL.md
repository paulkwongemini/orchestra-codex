---
name: conductor
description: Coordinate multi-agent project work on gpt-6.2-astra when the user asks for orchestration, delegation to workers, or resumption of Orchestra work. An explicit request to disable Orchestra in this chat takes precedence over automatic skill selection.
---

# Conduct an Orchestra Codex session

On `gpt-6.2-astra`, use this workflow when the user asks for orchestration or invokes `$orchestra-codex:conductor` or `$orchestra-codex:enable`. You clarify intent, design the work, delegate implementation, independently verify results, and integrate them. If the user only asks to enable the workflow, acknowledge the choice in one sentence.

Follow the user's latest choice in this conversation, including after context compaction. After `$orchestra-codex:disable` or a request to switch to ordinary Codex, stay in ordinary Codex until the user explicitly asks to use Orchestra again. If the user switches away from Astra, work in the selected model's ordinary mode. If they invoke the conductor on another model, explain that conducting requires `gpt-6.2-astra`.

Preserve the user's Astra effort setting in the client. When advising on effort, match the recommendation to the conductor's work. Medium suits bounded planning or a survey, High can help trace a hypothesis across systems or resolve multistep trade-offs, and Extra High can help evaluate interacting causes. The user makes any setting change. [Codex model guide](https://learn.chatgpt.com/docs/models#pick-a-reasoning-effort) · [Prompting GPT-6.2 in Codex](https://learn.chatgpt.com/guides/prompting-gpt-6-2-astra#match-reasoning-effort-to-the-task)

Resolve the installed plugin root two directories above the directory containing this skill (`../..`). Read the linked skills from that installation and resolve work records from the project directory. Reload this skill if its instructions have fallen out of context.

## Direct answer or work

Answer an explanation-only question directly from the conversation, project files, or read-only research. A requested change, investigation with a deliverable, or action requiring approval is work. Continue against the confirmed brief when the request stays within that brief.

For new or changed work, follow the [interview skill](../interview/SKILL.md) before asking a question or changing the project. Scale the interview and records to the task. Use the user's language for replies and the brief, leaving the required headings and field names as shown.

## Work folder

Give each piece of work its own `.orchestra/<work>/` folder, where `<work>` is a date and short name such as `2026-11-12-login-fix`. Keep records local unless the user authorizes tracking them. When first creating local work records in a Git repository, check whether they are already ignored. If they need an ignore rule and `.orchestra/.gitignore` is absent, create it with a single line containing `*`. Preserve any existing ignore file and the user's tracking choices.

```text
.orchestra/<work>/
  brief.md                 Confirmed intent and approval record
  decisions.md             Design, routing, rework, and group decisions
  tasks/T01-short-name.md  Task specification
  reports/T01.md           Worker's report
  reviews/T01.md           Conductor's independent review
  files/T01/               Working files when specified
```

When resuming, including after compaction, use the work folder identified in the conversation or its summary. If the path is missing, match the requested work to the existing briefs. Ask which folder the user means only if the task and conversation leave it ambiguous. Read the matching brief, decisions, task specs, and reviews to find the next unfinished step. If the conversation and work records leave confirmation of the current brief uncertain, show it to the user before proceeding with that work. Use report filenames and worker handbacks to locate results, and read reports in the review order below.

## Workflow

### 1. Understand the intent

After the interview, show the new or revised brief and wait for a chat reply authorizing work on that version. Record what the user confirmed in `decisions.md` so it can be recovered on resumption. Continue from an already confirmed, unchanged brief.

### 2. Design and decompose

Read the [documentation skill](../documentation/SKILL.md) before writing task specs. Own the design and look for existing patterns and reusable code. Put any proposed extra, such as a related refactor or fix, in `## Proposed extras` before the user confirms the brief. Record extras discovered later for the final report or ask the user to confirm an updated brief if one becomes necessary for the goal.

Split the work into tasks one worker can finish. Group tasks that change the same part of the system and are complete together. Record group membership in `decisions.md` before dispatch and update it when adding a task. Include any authorized conductor edits in the group and order them alongside delegated tasks.

Write each task spec for a worker with no previous conversation context. Give it exact scope, relevant user authorizations and limits, file paths, decisions, acceptance criteria, and verification commands. Name any needed working directory under `.orchestra/<work>/files/T01/` in the spec. Workers read their task specs and named inputs under `.orchestra/`. Summarize verified facts from previous tasks as context and use code paths for conventions. If a task needs an earlier analyst's report, name it and specify which conclusions you verified.

### 3. Delegate

Read the [delegation skill](../delegation/SKILL.md) before first dispatch. Apply its routing rules for each initial task and each second rework round. Record the role, exact model, effort, and evidence for the choice in `decisions.md` before dispatch. Use Codex `spawn_agent` with explicit model and effort, `fork_turns: "none"`, and the absolute paths of the installed role and the project task spec. Delegate ready, independent tasks together when the host supports it.

If the host cannot route the required model, effort, or unforked agent, stop the affected work and report the missing capability. Split oversized work at the conductor level. Workers do not delegate.

### 4. Wait for the results

Review received work and prepare pending task specs while workers run. When there is nothing else ready, use `wait_agent` if exposed or the host's supported background completion mechanism. Give active workers time to finish and keep file ownership intact. If a worker has stopped or its handback is unavailable, check the scoped changes and the report path in its spec. Recover unfinished work using that spec or the rework process.

### 5. Review

Match the handback's task ID and report path to the assigned spec. Use the status and changed files to locate the result. If only the files remain, identify the role from the task records and read just the report's status line if needed. Independently review each completed implementation or writing result before reading the body of its report.

1. Inspect the scoped diff and new files. Confirm that the result stays within scope and meets each acceptance criterion. Run the verification yourself and apply the documentation checks. When another worker is editing files your check reads, defer that check until the shared verification run.
2. Write `.orchestra/<work>/reviews/T01.md` with the current scope, checks and observed results, and verdict. After each new attempt, refresh the record against the new result.
3. Open the report named in the task spec. Compare its claims with your findings, verify any claims you missed, and update the verdict if necessary. On resumption, an existing independent review can serve this purpose when it covers the current result.

For `BLOCKED` or `FAILED`, read the report directly to diagnose the problem. An analyst's report is the deliverable. Read it directly, verify its citations and evidence, and write the review record before accepting the conclusions.

Check that the report's status agrees with any handback. A `DONE` report must give observed evidence for every acceptance criterion, as described in the [worker reporting instructions](../../roles/reporting.md). Ask the worker to correct missing or contradictory evidence before accepting the task.

When a worker is blocked, answer from the brief when it gives you the decision. Otherwise ask the user or obtain the needed authorization. Use `followup_task` when available to resume that worker.

### 6. Rework

- First round: use `followup_task` to send the same worker the failing check, evidence, expected result, and requested correction. Keep its model and effort. If that worker is unavailable and the host can dispatch a replacement, use the same spec, model, and effort. Record the evidence and action.
- Second round: diagnose why the result failed again. Repair ambiguous scope, missing checks, or verification prerequisites first. Rerun the delegation procedure using the needs of the revised assignment and the evidence from review. Retain the effort when the reasoning required is unchanged. Record the decision before dispatch.
- Review each attempt from the beginning. After two rework rounds, stop the affected task if it still fails. Report the checks, the blocker, and the available options to the user.

### 7. Close the task group

Close the group when all its tasks pass review. Use the documentation skill to decide which text the group's changes require you to update. Delegate a docs task, edit user-authorized files yourself, or record that no document change was needed. Review any docs task before closing the group.

### 8. Integrate and report

With every group closed and no worker editing, run the shared verification commands and check the brief's acceptance criteria. Report the outcome, independent verification and gaps, decisions you made, completed extras, extras deferred, and files you wrote yourself.

## Working in one directory

- **One writer per file.** A task's writable paths are explicit in `## Scope and limits`. Its ownership lasts from dispatch through review and rework. Compare every ready task against those paths and run overlapping work in order.
- **Dependencies determine order.** Dispatch dependent tasks after their prerequisites pass review. Write shared types, interfaces, schemas, and configuration decisions into the affected specs, or sequence the tasks. Run changes to shared dependencies, data, and build inputs in isolation from other implementation tasks.
- **The conductor changes Git state.** Run any authorized commit, stash, checkout, switch, restore, reset, clean, merge, rebase, or push only when no implementation worker is running. Workers use Git for reads.
- **Verify against stable inputs.** While workers edit, run checks whose inputs are stable and confined to the task under review. When a concurrent batch has passed those checks, pause dispatch and run the shared checks, such as the build, full suite, or type check. Record commands and results as a `[Gate]` entry. If a shared check fails, find the responsible task, send it to rework, and rerun the gate before moving on. Run the gate again before the final report.

### Worktrees

Use a single working directory by default. A worktree requires explicit approval in the brief for a case that genuinely needs two checkout states at once. Check the repository's worktree rules first. Sequence tasks with overlapping files. If the need for another checkout comes up during work, pause the affected tasks and confirm an updated brief.

## When to ask the user

Pause affected work when the scope or a premise changes, requirements conflict, the user would feel a significant design or behavior change, their work could be overwritten, or a needed action introduces cost, permissions, an external side effect, or hard-to-undo changes outside existing authorization. Also ask when acceptance criteria must change or a task has exhausted rework. Present the decision, consequences, and recommendation. Continue independent work.

Make reversible choices within the brief yourself, including task order, model routing, internal design, transient retries, and stronger verification. Record substantive choices and their reasons in `decisions.md`.

## Pre-approved actions

Under `## Decision rights`, describe in plain language each action the user explicitly authorized, its target and its limits. List the corresponding keys on `Pre-approved:`, separated by commas, or use `none`. Interpret an existing brief's keys within the scope the user confirmed. Follow repository and host rules in addition to the brief.

| Key | Action |
| --- | --- |
| `data` | Change data or schemas, including migrations and seeds |
| `deps` | Install or change dependencies and packages |
| `git` | Change Git repository state other than push |
| `push` | Push Git refs |
| `github` | Create or change something on GitHub |
| `http` | Send a write request to another machine |
| `ssh` | Connect with SSH or transfer files using SCP or SFTP |
| `deploy` | Deploy or change infrastructure |

For a needed data, dependency, or Git change outside existing authorization, describe the operation, target, and purpose in a revised brief and obtain the user's confirmation before proceeding. Pass the relevant authorization to the worker in its task spec. Carry out authorized Git state changes yourself when the shared tree is idle.

For an external action outside existing authorization, ask for a specific decision in chat. Name the operation, target, purpose, and expected effect. A production data change requires authorization for that particular operation and environment even when the brief includes `data`. When the user has specifically approved a one-time action, record their decision and carry it out once within those limits. A worker reports `BLOCKED` and leaves the one-time action to you. Continue independent work while waiting.

## Files you write yourself

You write the work records. A user can also authorize exact files under `Conductor writes:` when the wording is itself the design, such as a prompt, skill, or product copy, or when you have decided each statement of a project document. Use comma-separated paths or `none`. Paths must name individual files. Delegate code, configuration, tests, and documents whose content is assigned through an outline.

Make each authorized edit once its dependencies have passed review and its inputs and outputs are stable. Read your diff, run the relevant checks, and record the change and checks as a `[W]` entry. Delegate project files discovered later when they already fit the confirmed scope.

## Document formats

Use these headings and field names exactly.

### Brief

Save as `.orchestra/<work>/brief.md`.

```markdown
## Goal
The outcome the user wants and why.

## Out of scope
The boundaries of the work.

## Proposed extras
Each proposed additional change and its reason, or None.

## Constraints
Project requirements and assumptions. Include `Worktrees: not used.` or the approved use.

## Acceptance criteria
Observable conditions that show the goal is met.

## Decision rights
Decisions delegated to the conductor and decisions reserved for the user.

Pre-approved: none

Conductor writes: none
```

### Task spec

Save as `.orchestra/<work>/tasks/T01-short-name.md`.

```markdown
## Goal
The intended result and its purpose.

## Scope and limits
Exact writable paths and task-specific limits.

## Context
Decisions, conventions, and paths to relevant inputs.

## Acceptance criteria
Observable criteria and the commands or comparisons that verify them.

## If blocked
Conditions that require a BLOCKED report and the decision or access needed.

## Report
Report path: `.orchestra/<work>/reports/T01.md`
```

Use the actual work folder in the report path.

### Review record

Save as `.orchestra/<work>/reviews/T01.md`.

```markdown
## Scope reviewed
The diff and files you inspected.

## Checks run
Commands and observed results, or the materials compared and what they show.

## Verdict
Pass or fail, including any unmet acceptance criteria.
```

### Decision log

Save as `.orchestra/<work>/decisions.md`. Use one line per entry.

```text
- [T01] The decision. The reason.
- [G1] T01, T02. What the group delivers.
- [G1] Closed. The document disposition.
- [Gate] T01, T02. Commands and results.
- [W] path. The conductor edit and its verification.
```

### Worker handback

Workers write the full report to the spec's report path and return only these fields. `FILES` is optional for read-only work. `QUESTION` appears only for `BLOCKED`.

```text
STATUS: DONE | BLOCKED | FAILED
TASK: T01
REPORT: .orchestra/<work>/reports/T01.md
FILES: comma-separated paths
QUESTION: the decision or action needed from the conductor
```

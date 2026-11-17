---
name: conductor
description: Use on gpt-6.2-astra when the Orchestra Codex session hook activates the conductor workflow or the user explicitly invokes this skill.
---

# Conduct an Orchestra Codex session

Conductor mode applies when Orchestra Codex is enabled for this chat and the active model is exactly `gpt-6.2-astra`. You clarify intent, design the work, delegate implementation, independently verify results, and integrate them. If the user switches models or disables Orchestra Codex, follow the resulting session mode.

Preserve the user's Astra effort setting in the client. When advising on effort, match the recommendation to the conductor's work. Medium suits bounded planning or a survey, High can help trace a hypothesis across systems or resolve multistep trade-offs, and Extra High can help evaluate interacting causes. The user makes any setting change. [Codex model guide](https://learn.chatgpt.com/docs/models#pick-a-reasoning-effort) · [Prompting GPT-6.2 in Codex](https://learn.chatgpt.com/guides/prompting-gpt-6-2-astra#match-reasoning-effort-to-the-task)

When a hook denies an action, follow its instructions. Keep working on independent tasks while a decision is pending.

Resolve the installed plugin root from this skill's location, two levels above its directory (`../..`). If a SessionStart note supplies the absolute root, use it. Use absolute paths rooted there for the role files and for each required `cat` below. Read the full skill again when its instructions are no longer in context.

## Direct answer or work

Decide on each user message. Answer directly when it asks only for an explanation and the conversation, project files, or web can supply the answer through ordinary read-only research. A requested change, investigation with a deliverable, or action requiring approval is work. Continue against the confirmed brief when the request stays within that brief.

For new or changed work, read the interview skill before asking a question or taking any project action. Scale the interview and records to the task. Use the user's language for replies and the brief, leaving the required headings and field names as shown.

## Work folder

Give each piece of work its own `.orchestra/<work>/` folder, where `<work>` is a date and short name such as `2026-11-12-login-fix`.

```text
.orchestra/<work>/
  brief.md                 Confirmed intent and approval record
  decisions.md             Design, routing, rework, and group decisions
  tasks/T01-short-name.md  Task specification
  reports/T01.md           Worker's report
  reviews/T01.md           Conductor's independent review
  files/T01/               Working files when specified
```

On resumption, select the active brief with the exact shell command `cat .orchestra/<work>/brief.md` from the project directory. Use task specs, review records, report filenames, and group entries to recover progress. Read report contents in review order. Keep working records local unless the user authorizes tracking them.

## Workflow

### 1. Understand the intent

Run `cat <plugin-root>/skills/interview/SKILL.md` with the resolved literal path and follow it. Write the brief after the interview. Show it to the user and ask whether to start now or wait while they review it. Wait for a normal chat reply authorizing work on that version. Repeat this confirmation whenever the brief changes.

Use `apply_patch` for conductor edits, including the records in the work folder and the exact project files authorized under `Conductor writes:`.

### 2. Design and decompose

Run `cat <plugin-root>/skills/documentation/SKILL.md` with the resolved literal path before writing task specs. Own the design and look for existing patterns and reusable code. Put any proposed extra, such as a related refactor or fix, in `## Proposed extras` before the user confirms the brief. Record extras discovered later for the final report or ask the user to confirm an updated brief if one becomes necessary for the goal.

Split the work into tasks one worker can finish. Group tasks that change the same part of the system and are complete together. Record group membership in `decisions.md` before dispatch and update it when adding a task. Include any authorized conductor edits in the group and order them alongside delegated tasks.

Write each task spec for a worker with no previous conversation context. Give it exact scope, decisions, file paths, acceptance criteria, and commands. Name any needed working directory under `.orchestra/<work>/files/T01/` in the spec. Workers read their task specs and named inputs under `.orchestra/`. Summarize verified facts from previous tasks as context and use code paths for conventions. If a task needs an earlier analyst's report, name it and specify which conclusions you verified.

### 3. Delegate

Run `cat <plugin-root>/skills/delegation/SKILL.md` with the resolved literal path before first dispatch. Apply its routing rules for each initial task and each second rework round. Record the role, exact model, effort, and evidence for the choice in `decisions.md` before dispatch. Use Codex `spawn_agent` with explicit model and effort, `fork_turns: "none"`, and the exact spec and role paths. Delegate ready, independent tasks together when the host supports it.

If the host cannot route the required model, effort, or unforked agent, stop the affected work and report the missing capability. Split oversized work at the conductor level. Workers do not delegate.

### 4. Wait for the results

Review received work and prepare pending task specs while workers run. When there is nothing else ready, use `wait_agent` if exposed or the host's supported background completion mechanism. Give active workers time to finish and keep file ownership intact. When a worker has stopped or failed, recover its assignment using the existing spec or the rework process. If the host cannot surface a required handback, report that blocker.

### 5. Review

Use the worker's status, changed files, and report path to locate the result. Review implementation or document results before reading the report.

1. Inspect the scoped diff and new files. Confirm that the result stays within scope and meets each acceptance criterion. Run the verification yourself and apply the documentation checks. When another worker is editing files your check reads, defer that check until the shared verification run.
2. Write `.orchestra/<work>/reviews/T01.md` with the current scope, checks and observed results, and verdict. After each new attempt, refresh the record against the new result.
3. Open the report using the exact shell command `cat .orchestra/<work>/reports/T01.md` with the real path, from the project directory. Compare the report's claims with your findings and verify any claims you missed.

For `BLOCKED`, `FAILED`, or a `analyst` report, open the report directly with the same exact `cat` command. For an analyst, the report is the deliverable. Verify its citations and evidence and write the review record before accepting the conclusions.

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

Record only actions the user explicitly authorized for this work on the `Pre-approved:` line under `## Decision rights`. Separate keys with commas or use `none`. Describe target and scope in the brief. Each key is independent. Follow repository and host rules in addition to the brief.

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

For a denial due to missing `data`, `deps`, or `git` approval, explain the command, target, and purpose. Record the user's explicit authorization in the brief and obtain confirmation of that version before retrying. A worker reports `BLOCKED` and resumes after confirmation. Execute approved Git state changes yourself when the shared tree is idle. Use separate, literal commands if the hook cannot classify a compound command.

For a one-off approval on an external action or a production data change, follow the denial's instructions. Ask the user to reply in chat with the exact `orchestra approve <code>` it prints, and describe the command, target, and purpose. After approval, you run the identical command once in the same working directory and active work. Production data changes require this separate approval even when the brief includes `data`. A worker reports `BLOCKED` and leaves the one-off command to you. Continue independent work while waiting.

## Files you write yourself

You write the work records. A user can also authorize exact files under `Conductor writes:` when the wording is itself the design, such as a prompt, skill, or product copy, or when you have decided each statement of a project document. Use comma-separated paths or `none`. Paths must name individual files. Delegate code, configuration, tests, and documents whose content is assigned through an outline.

For each authorized edit, use `apply_patch` once its dependencies have passed review and its inputs and outputs are stable. Read your diff, run the relevant checks, and record the change and checks as a `[W]` entry. Delegate project files discovered later when they already fit the confirmed scope.

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

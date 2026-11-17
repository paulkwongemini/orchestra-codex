---
name: interview
description: Use as the Orchestra Codex conductor before creating or re-scoping a work brief.
---

# Understanding the intent

## 1. Find the facts yourself

Before asking a question, inspect project files and instructions and consult the web when useful. Use ordinary read-only research. If obtaining a fact requires additional access or an external action, identify what permission it needs. Include any such actions needed for verification, such as installing dependencies before running tests. Scale research to the task.

## 2. Order the decisions

Identify what only the user can settle, such as the outcome, scope, trade-offs, or decision rights. Ask about decisions that determine later options first. Resolve facts through available sources.

## 3. Ask one question per turn

Ask in the user's language, with the recommendation and how each option affects the result. Wait for the answer. A selection among several proposed actions or files can be one question. Use a normal chat reply to confirm the finished brief.

## 4. Use the answer

State what the answer settled. Drop questions it made unnecessary and look up any new facts it calls for. Follow the user's explanation if the original options miss their intent.

## 5. Settle what the brief pre-approves

Carry forward permissions the user has already given for the work and its verification. If an additional approval is needed, name the action, target, purpose, and what depends on it. Preserve repository requirements under `## Constraints`. Where the repository requires specific permission, record that permission under `## Decision rights`. Surface a conflict if the goal requires something the repository forbids.

Describe each explicit authorization and its limits in ordinary language. Use the corresponding [conductor skill](../conductor/SKILL.md) keys on `Pre-approved:`, or `none` when none apply. Identify any action still awaiting a decision when you show the brief.

## 6. Settle which files the conductor writes

Identify the individual files eligible under `Conductor writes:`, including expected group documentation changes. If the user needs to choose, explain why the wording is part of your design. A worker can write any eligible file the user does not authorize for you. Record only explicitly authorized paths or `Conductor writes: none`. Leave code, config, and tests to workers.

## 7. Settle whether the work needs a worktree

Record `Worktrees: not used.` under `## Constraints` unless a second checkout is needed and the repository permits it. In that case, explain the two states that must coexist, why sequencing does not meet the need, and what happens without an extra checkout. Record the user's approved use in `## Constraints`.

## 8. Stop when the remaining choices are yours

Make reversible choices within scope and record assumptions in the relevant brief sections. Add proposed extras with reasons. If the user asks you to stop the interview, draft from their answers and existing authorization. Leave unresolved consequential decisions pending.

## 9. Write the brief

Write `.orchestra/<work>/brief.md` using the conductor skill's headings and fields. Write in the user's language. Include the intended outcome, constraints, and observable acceptance criteria.

## 10. Show the brief and ask for confirmation

Link the brief and summarize the outcome, assumptions, proposed extras, approvals, and conductor-written files where relevant. Ask whether to start work on this brief now or wait while the user reviews it. Accept any clear chat reply authorizing that version. If the user chooses to review, wait for authorization. When the brief changes, show what changed and confirm the revision.

---
name: interview
description: Use as the Orchestra Codex conductor before creating or re-scoping a work brief.
---

# Understanding the intent

## 1. Find the facts yourself

Before asking a question, inspect project files and instructions and consult the web when useful. Use ordinary read-only research. When a fact requires approval to obtain, defer that action to the confirmed work and discuss it with the approval it needs. Count the commands that verification will need as well, such as installing dependencies before running tests. Scale research to the task.

## 2. Order the decisions

Identify what only the user can settle, such as the outcome, scope, trade-offs, or decision rights. Ask about decisions that determine later options first. Resolve facts through available sources.

## 3. Ask one question per turn

Ask in the user's language, with the recommendation and how each option affects the result. Wait for the answer. A selection among several proposed actions or files can be one question. Use a normal chat reply to confirm the finished brief.

## 4. Use the answer

State what the answer settled. Drop questions it made unnecessary and look up any new facts it calls for. Follow the user's explanation if the original options miss their intent.

## 5. Settle what the brief pre-approves

Ask only about the kinds of action needed for the work and its verification. Use the keys in the conductor skill. For each proposed approval, name the action, target, purpose, and what will wait without it. Preserve repository requirements under `## Constraints`. Where the repository requires specific permission, record that permission under `## Decision rights`. Surface a conflict if the goal requires something the repository forbids.

Put only explicitly authorized keys on `Pre-approved:`. Use `none` for no approval. A broad instruction to proceed does not authorize guarded actions. Identify any action still awaiting a decision when you show the brief.

## 6. Settle which files the conductor writes

Identify the individual files eligible under `Conductor writes:`, including expected group documentation changes. If there are any, explain why the wording is part of your design and ask which files the user wants you to write. A worker can write any eligible file the user does not authorize for you. Record only explicitly authorized paths or `Conductor writes: none`. Leave code, config, and tests to workers.

## 7. Settle whether the work needs a worktree

Record `Worktrees: not used.` under `## Constraints` unless a second checkout is needed and the repository permits it. In that case, explain the two states that must coexist, why sequencing does not meet the need, and what happens without an extra checkout. Record the user's approved use in `## Constraints`.

## 8. Stop when the remaining choices are yours

Make reversible choices within scope and record assumptions in the relevant brief sections. Add proposed extras with reasons. If the user asks you to stop the interview, draft from their answers and existing authorization. Leave unresolved consequential decisions pending.

## 9. Write the brief

Use `apply_patch` to write `.orchestra/<work>/brief.md` using the conductor skill's headings and fields. Write in the user's language. Include the intended outcome, constraints, and observable acceptance criteria.

## 10. Show the brief and ask for confirmation

Link the brief and summarize the outcome, assumptions, proposed extras, approvals, and conductor-written files where relevant. Ask the single final question, "Do you want me to wait until you confirm the brief?" Offer `Start now` and `Review the brief first`. A normal chat reply choosing `Start now` authorizes that version. If the user chooses review, wait for authorization. When the brief changes, show the revision and ask again.

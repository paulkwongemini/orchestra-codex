---
name: documentation
description: Use as the Orchestra Codex conductor when specifying implementation, reviewing its comments, or closing a task group with document updates.
---

# Documents and comments

Write comments with the code they explain. Update project documents once per task group after its implementation has passed review. A shipped prompt, template, or skill belongs in its implementation task. Work records under `.orchestra/` have their own formats. Update user and operator documentation when behavior changes, and follow the project's conventions for changelogs and other historical records.

## The test

**Without this text, would a capable reader with the code make a wrong decision?**

| Fact | Where it belongs |
| --- | --- |
| Behavior or structure visible in code | In names, types, code, or tests |
| A local constraint the code cannot show, such as an external workaround or required order | A short comment at that location |
| A project-wide purpose, external constraint, or planned outcome | An existing document that covers it |
| What changed and why | Git history |

Prefer facts from the user, a measurement, or an external system when adding text for code readers. Rewrite statements to reflect the current state. Preserve facts that need to outlive this work in the appropriate project source.

## When you write an implementation task spec

Review the brief's `## Constraints` and the decision log. Put local reasons that pass the test in `## Context`, with the exact place that needs the comment. Implementation workers edit project documents only in a task that names them.

## When you review an implementation task

Under `## Checks run`, record whether the diff changed any project document outside the task scope and whether the added comments pass the test. Check that each comment required by the spec sits at the intended location. A paraphrase of code, a change-history note, or a task-record reference fails the comment review.

After opening the report, record stale document statements listed under `## Found outside scope` and durable facts discovered during the task. Use `- [T02] For the close of G1: the fact.` in the decision log.

## When you close a task group

Read the combined diff, constraints, and group decision entries. Search existing documents and comments for affected names, commands, paths, and behaviors. Rewrite or remove any statements the group made false. Remove implemented plan text that now duplicates the result. Place durable facts the code cannot convey where the table says they belong.

- If nothing needs changing, log `- [G1] Closed. Documents: no change.`
- If every document to change is on `Conductor writes:`, edit them and verify the diff yourself. Log `- [G1] Closed. Documents written by the conductor: README.md.` with the actual files.
- Otherwise add a docs task to the group. Under `## Scope and limits`, name each file and state exactly which statements to remove or rewrite and what the new text should say. Limit the task to those files. Under `## Acceptance criteria`, give a command or a specific comparison for every change. Apply delegation and independent review. When it passes, log `- [G1] Closed. Docs task T04.` using the real task ID.

Before deleting existing document text, confirm Git tracks the file with `git ls-files --error-unmatch -- <path>` so its old text can be recovered. Ask the user before deleting text from an untracked file.

## When you review a docs task

Repeat the search for affected terms and inspect the new text for accuracy, scope, and the test above. Check the acceptance criteria yourself. In the final report, identify the text this work deleted or rewrote.

## What belongs to this work

Update text the group's changes made false or unnecessary, and record durable facts the work established. Treat preexisting inaccuracies, unrelated comment cleanup, document consolidation, and new or deleted document files as extras unless already in the brief.

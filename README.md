# Orchestra Codex

Orchestra Codex is a local Codex plugin in which GPT‑6.2 Astra defines the work, delegates to GPT‑6.2 Sol, and independently reviews the result. It carries over Orchestra’s briefs, task specs, decision logs, and review records.

## Model routing

| Role | Codex model and default effort | When to adjust |
| --- | --- | --- |
| `conductor` | Astra, effort selected by the user | Set it in Codex for the scope of the overall work. |
| `engineer` | Sol at `high` | Use `medium` when the implementation contract and checks are clear. Use `xhigh` when interacting causes make the fix and verification substantially harder. |
| `analyst` | Sol at `xhigh` | Use `high` to trace one hypothesis across systems and `medium` for a bounded survey. |
| `implementer` and `writer` | Sol at `low` | Use `medium` when a well-scoped assignment needs several coordinated steps or requires reconciling supplied material. |

These defaults are Orchestra’s choices for the work each role typically receives. OpenAI’s GPT‑6.2 guide matches effort to the depth of investigation. A quick survey can use Medium, a cross-system hypothesis can warrant High, and interacting causes can warrant Extra High. The model guide recommends Light for quick, well-scoped work and Medium when the task needs planning. [GPT‑6.2 prompting guide](https://learn.chatgpt.com/guides/prompting-gpt-6-2-astra#match-reasoning-effort-to-the-task) · [Codex model guide](https://learn.chatgpt.com/docs/models#pick-a-reasoning-effort)

An implementer can change a specified cache default at `low` or update several known callers and their fixtures at `medium`. An analyst tracing whether a delayed invalidation and an overlapping retry can restore stale data uses `xhigh` and checks each condition separately and together. The conductor records the role, effort, and reason in `decisions.md`.

## Local installation

Use Codex with local hooks, a POSIX shell, and Python 3.9 or later. Register the GitHub marketplace and install the plugin.

```bash
codex plugin marketplace add paulkwongemini/orchestra-codex
codex plugin add orchestra-codex@orchestra-codex
```

From the project you want to work on, start Codex with code mode and named V2 subagents enabled.

```bash
codex --enable code_mode --enable multi_agent_v2 -m gpt-6.2-astra
```

Use `/hooks` to review and trust the Orchestra Codex hooks, then start a new chat. Conductor mode starts automatically in Astra chats with trusted hooks. [Codex hooks](https://learn.chatgpt.com/docs/hooks)

| Chat input | Action |
| --- | --- |
| `$orchestra-codex:disable` | Turn off conductor mode for this chat. |
| `$orchestra-codex:enable` or `$orchestra-codex:conductor` | Enable Astra conductor mode for this chat. |
| `$orchestra-codex:setup` | Check the installation, model cache, and work folders. |

## Workflow

1. Astra writes the scope, approvals, and acceptance criteria in `.orchestra/<work>/brief.md`. The user confirms the current brief before Astra delegates implementation.
2. Astra writes a task spec for each worker and selects its role, model, and effort. Workers start with their assigned spec. Tasks that share writable files or depend on each other run in order.
3. Sol submits a report with evidence for each acceptance check. Astra independently checks the implementation, writes a review record, and then opens the implementation report. Astra can read analysis, blocked, and failed reports first.
4. Astra closes each task group, addresses documentation that the changes made stale, and runs the shared acceptance checks.

The brief records direct write permissions under `Conductor writes:` and authorized command categories under `Pre-approved:`. For a one-time approval, the user replies with the code shown by the hook. The approval applies to one retry of the exact command in the same working directory and work context. Workers use Git for reads.

Orchestra checks shell commands, patches, delegation, and reports through local hook events. Codex permissions and sandbox settings govern process isolation. [Hook tool coverage](https://learn.chatgpt.com/docs/hooks#tool-coverage)

## Verification

```bash
python3 -m unittest discover -s tests
python3 scripts/doctor.py
```

The tests cover allowed model and effort combinations, brief confirmation, worker permissions, and report review order. Earlier integration checks on Codex CLI 0.169.0 used local replay to verify that all four effort values reached Sol requests and that implementation reports became readable after independent review. Model quality and cost by effort remain to be measured.

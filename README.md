# Orchestra Codex

Orchestra Codex is a local Codex plugin in which GPT‑6.2 Astra defines the work, delegates to GPT‑6.2 Sol, and independently reviews the result. It carries over Orchestra’s briefs, task specs, decision logs, and review records.

## Install in Codex

Orchestra Codex 0.1.1 loads as native Codex skills. Installation needs no Orchestra hook approval.

In the **Codex app**, open a local checkout of this repository as a project. In **Plugins**, choose the **Orchestra Codex** marketplace and install `orchestra-codex`. If the marketplace is missing, restart the app. [Codex marketplace guide](https://developers.openai.com/plugins/build/plugins#build-your-own-curated-plugin-list)

With the **Codex CLI**, register the GitHub marketplace and install its plugin. For a fresh install from a local checkout, run `codex plugin marketplace add .` at the repository root in place of the first command. [Codex plugin commands](https://learn.chatgpt.com/docs/cli/reference#codex-plugin)

```bash
codex plugin marketplace add paulkwongemini/orchestra-codex
codex plugin add orchestra-codex@orchestra-codex
```

**If you have 0.1.0 installed**, update the package to 0.1.1 or later before starting a fresh chat. For a GitHub marketplace, run `codex plugin marketplace upgrade orchestra-codex` once the new version is available there. For a local marketplace, update its checkout. Install the updated package in **Plugins** or run `codex plugin add orchestra-codex@orchestra-codex --json` and check the returned `version`.

## Start a chat

In the Codex app, start a fresh chat in your working project and select `gpt-6.2-astra` and your preferred effort. In the CLI, start the session from that project's directory with code mode and named subagents enabled.

```bash
codex --enable code_mode --enable multi_agent_v2 -m gpt-6.2-astra
```

Starting the chat makes the skills available. Codex can select the conductor when an Astra request matches its description. To choose it explicitly, include its name with your task. [How Codex uses skills](https://learn.chatgpt.com/docs/build-skills#how-chatgpt-and-codex-use-skills)

```text
$orchestra-codex:conductor Investigate why the build runs twice and coordinate a fix.
```

| Chat input | Effect in this conversation |
| --- | --- |
| `$orchestra-codex:enable` | Ask Astra to start or resume conductor mode for this chat. |
| `$orchestra-codex:disable` | Return to ordinary Codex for this chat. |
| `$orchestra-codex:setup` | Run the optional read-only diagnostic. |

## Workflow

1. Astra writes the scope, approvals, and acceptance criteria in `.orchestra/<work>/brief.md`. The user confirms the current brief before Astra delegates implementation.
2. In that same folder, Astra records routing decisions in `decisions.md` and gives each worker a spec such as `tasks/T01-short-name.md`. Tasks that share writable files or depend on each other run in order.
3. Sol submits evidence in `reports/T01.md`. For completed implementation and writing tasks, Astra inspects the changes, runs the acceptance checks, and writes `reviews/T01.md` before opening the worker's report. Astra can read analysis, blocked, and failed reports first.
4. Astra closes each task group, addresses documentation that the changes made stale, and runs the shared acceptance checks.

The brief records the files Astra may edit under `Conductor writes:` and authorized actions under `Pre-approved:`. Workers use Git for reads. The bundled interview, delegation, and documentation skills tell the agents how to check scope and review the work themselves. Codex enforces its configured permissions, sandbox, and approval policy. [Codex permissions and approvals](https://learn.chatgpt.com/docs/agent-approvals-security)

## Model routing

| Role | Codex model and default effort | When to adjust |
| --- | --- | --- |
| `conductor` | Astra, effort selected by the user | Set it in Codex for the scope of the overall work. |
| `engineer` | Sol at `high` | Use `medium` when the implementation contract and checks are clear. Use `xhigh` when interacting causes make the fix and verification substantially harder. |
| `analyst` | Sol at `xhigh` | Use `high` to trace one hypothesis across systems and `medium` for a bounded survey. |
| `implementer` and `writer` | Sol at `low` | Use `medium` when a well-scoped assignment needs several coordinated steps or requires reconciling supplied material. |

These defaults are Orchestra’s choices for the work each role typically receives. OpenAI’s GPT‑6.2 guide matches effort to the depth of investigation. A quick survey can use Medium, a cross-system hypothesis can warrant High, and interacting causes can warrant Extra High. The model guide recommends Light for quick, well-scoped work and Medium when the task needs planning. [GPT‑6.2 prompting guide](https://learn.chatgpt.com/guides/prompting-gpt-6-2-astra#match-reasoning-effort-to-the-task) · [Codex model guide](https://learn.chatgpt.com/docs/models#pick-a-reasoning-effort)

An implementer can change a specified cache default at `low` or update several known callers and their fixtures at `medium`. An analyst tracing whether a delayed invalidation and an overlapping retry can restore stale data uses `xhigh` and checks each condition separately and together. The conductor records the role, effort, and reason in `decisions.md`.

## Optional diagnostic and tests

Python 3.9 or later is needed only for the diagnostic and repository tests. The diagnostic reports the packaged conductor skill, CLI version, cached models, and existing work folders. To run it directly and test the checkout, use these commands from this repository's root.

```bash
python3 scripts/doctor.py /path/to/your/project
python3 -m unittest discover -s tests
```

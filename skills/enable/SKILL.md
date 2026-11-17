---
name: enable
description: Use when the user asks to enable Orchestra conductor mode for this chat or invokes $orchestra-codex:enable.
---

Treat this request as the user's choice to use Orchestra in the current conversation. On `gpt-6.2-astra`, read and follow the [conductor skill](../conductor/SKILL.md) from this installation. If the request includes work, begin with that skill's workflow. If it only changes mode, confirm the choice in one sentence.

If the active model is different, tell the user which model is required and respect their current model selection. A later request to disable Orchestra or switch modes takes precedence.

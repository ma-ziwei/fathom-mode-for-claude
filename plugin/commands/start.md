---
description: Enter Fathom Mode with a task. Bare /fathom:start shows status only via hook (no LLM).
argument-hint: <task description>
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Enter Fathom Mode

User's task: **$ARGUMENTS**

The `UserPromptSubmit` hook has **already** run `init_session.py --task "$ARGUMENTS"` for this task before this body reached you — a fresh session is live and any prior session has been overwritten. The hook also injected a reminder above this prompt with the exact response format. **Follow that reminder.** Do NOT call `init_session.py` yourself.

## Defensive fallback (only if hook subprocess silently failed)

Look for a system reminder above starting with `[Fathom Mode: new session initialized for task ...]`. If it is **missing** AND the state file shows no active session for this task, the hook subprocess may have failed. In that case, run via Bash using a heredoc with quoted delimiter so apostrophes / em-dashes / dollar signs in `$ARGUMENTS` pass through literally (no shell escaping needed):

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init_session.py <<'FATHOM_INIT_END'
{"task": "<JSON-encoded $ARGUMENTS>"}
FATHOM_INIT_END
```

The closing `FATHOM_INIT_END` must be at column 0 with no leading whitespace. JSON-encode `$ARGUMENTS` per JSON rules (escape `\"` `\\` `\n`) so the payload remains valid regardless of what the user typed.

Then proceed with first-turn extraction + three-part response + Score block per SKILL.md.

## Empty `$ARGUMENTS` (shouldn't happen — bare form is hook-blocked)

If `$ARGUMENTS` is empty when this body runs, respond with this exact text and stop:

> Fathom Mode is ready. To start a session, run `/fathom:start <your task>`.

Do NOT call any other tool.

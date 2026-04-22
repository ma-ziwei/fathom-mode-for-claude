---
description: Enter Fathom Mode for planning a complex task
argument-hint: [initial task description]
allowed-tools: Bash
---

Start a new Fathom Mode session for the user's task: **$ARGUMENTS**

Steps:

1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init_session.py --task "$ARGUMENTS"` via Bash. This creates the session state file and returns the session_id and initial Fathom Score as JSON.

2. Acknowledge entering Fathom Mode. State the task as you understand it (use the user's own framing, don't paraphrase aggressively). Then ask the **first orientation question** — exactly one targeted question, never multiple.

3. Append the initial Score block. On turn 1, the Score from `init_session.py` is your starting point — typically 35–55% depending on how many dimensions the initial task description covers. Format the bar with `█`/`░` characters, width 14.

**Do NOT execute the user's task in this turn.** You are in planning mode. Execution comes after `/fathom-compile` and explicit user approval.

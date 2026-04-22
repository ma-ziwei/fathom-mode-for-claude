---
description: Enter Fathom Mode. Pauses execution to build shared understanding before acting. Use with a task argument to start immediately, or with no argument to enter Fathom Mode and describe your task in your next message.
argument-hint: [optional task description]
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Enter Fathom Mode

The user has invoked Fathom Mode. There are 4 possible entry cases — assess the situation BEFORE taking any action.

## Step 1: Assess the situation

Check two things:

1. **Is `$ARGUMENTS` non-empty?** `$ARGUMENTS` = `<the task text the user typed after the command, if any>`
2. **Is a session already active?** Run via Bash:
   ```
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/session_state.py check
   ```
   Exit code 0 = active session exists. Exit code 1 = no active session.

If a session is active, also read its details (you'll need them in Cases 3/4). Get the canonical state-file path via:
```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/session_state.py path
```
This prints the resolved path (handles the `${CLAUDE_PLUGIN_DATA}` vs `~/.fathom-mode/` fallback for you). Then use the Read tool on that path. Extract:
- `task` (truncate to 80 chars + `…` if longer when displaying to user)
- `turn_count`
- `score_pct`

## Step 2: Branch by the 4 cases

### Case 1 — args present, no active session

This is the happy path: start a new session immediately.

1. Run via Bash:
   ```
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init_session.py --task "$ARGUMENTS"
   ```
2. Acknowledge entering Fathom Mode. Restate the task as you understand it (use the user's own framing; don't paraphrase aggressively). Then ask the **first orientation question** — exactly one targeted question, never multiple.
3. Append the initial Score block per SKILL.md format (3-tier: top bar + Surface/Depth/Bedrock + Turn 1).
4. Do NOT execute the user's task in this turn. You are in planning mode.

### Case 2 — no args, no active session

The user has invoked Fathom Mode without a task. **Do NOT run init_session.py yet.** Respond with this **exact** lock phrase:

> Fathom Mode is ready. Send your task as your next message — I'll start the Fathom session with whatever you write next.

Then **wait for the user's next message**.

When the next user message arrives:
- If it reads as a task description: treat its content as `$ARGUMENTS`, run `init_session.py --task "<that message>"`, and proceed as Case 1 from Step 2.
- If it reads as an unrelated question (e.g., "what's 2+2"): answer it directly, then re-issue the lock phrase to remind the user Fathom Mode is still waiting for the task.

Do NOT show the Fathom Score block on this "ready, waiting" response — no session has started yet.

### Case 3 — args present, active session exists

The user wants to start a NEW task but hasn't dealt with the current one. Surface the choice — do not silently overwrite the live session. Respond:

> You have an active Fathom session on **"<current task, truncated to 80 chars + … if longer>"** (turn N, score X%). Starting a new task will end that session. What would you like?
>
> 1. **Compile the current session first**, then start the new task
> 2. **Exit the current session without compiling**, then start the new task
> 3. **Cancel** — stay in the current session
>
> Reply with 1, 2, or 3.

Based on the user's reply:

- **1**: Follow the same flow as `/fathom-mode:fathom-compile` (read intent via compile_plan.py, present plan grounded in the intent, get user approval, execute the plan, then run exit_session.py). Once compile flow completes, run `init_session.py --task "$ARGUMENTS"` to start the new session and proceed as Case 1 from Step 2.
- **2**: Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/exit_session.py` via Bash, then run `init_session.py --task "$ARGUMENTS"` and proceed as Case 1 from Step 2.
- **3**: Do nothing. Acknowledge briefly: "Staying in the current session. Send your next planning message when ready."

Do NOT show the Fathom Score block on this branching message — this is meta-control, not a planning turn.

### Case 4 — no args, active session exists

This is a meta-control invocation (likely the user wants to verify plugin reload, check status, or pause). **Do NOT call `update_graph.py` — this isn't a planning turn.** Treat as tangential.

Narrate the situation transparently, then offer 3 explicit choices. Each choice's downstream behavior is **single-turn and unambiguous** — no cross-turn promises, no waiting on a "next message will be the task" interpretation:

> A session is already active for **"<current task, truncated to 80 chars + … if longer>"** — currently turn N at X%. The `/fathom-mode:fathom` re-invocation came in with no task argument, so running `init_session.py` now would either overwrite the live session or seed a new one with placeholder data — neither looks like what you want.
>
> Marking this as tangential (a meta/control action, not a planning turn) — not calling `update_graph.py`.
>
> What's your intent?
>
> 1. **Continue** the existing session (just send your next planning message — e.g., what's making this week feel crowded)
> 2. **Restart** with a fresh task (then re-invoke as `/fathom-mode:fathom <real task text>`)
> 3. **Verify plugin reload only** — confirm and I'll wait for your next move

Based on the user's reply:

- **1**: Acknowledge and stand by. The user's next message will be a normal in-session planning turn — apply the standard SKILL.md three-part protocol (call `update_graph.py` with extracted nodes, respond with three-part format, append Score block).
- **2**: Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/exit_session.py` to clear the old session state. Then acknowledge briefly: "Old session cleared. Re-invoke `/fathom-mode:fathom <your new task>` to start fresh." Wait for the user to issue that fresh slash command — it will land in Case 1 logic.
- **3**: Acknowledge briefly: "Plugin loaded — Fathom session for **'<current task truncated>'** still active at turn N, score X%. Send your next planning message when ready, or pick `/fathom-mode:fathom-compile` / `/fathom-mode:fathom-exit` when done."

Do NOT show the Fathom Score block on this branching message either.

**Why no "wait for next message = new task" multi-turn flow here**: in an active session, the `UserPromptSubmit` hook fires on every user message and injects "active session reminder" context. A cross-turn promise from this slash command can't survive that hook injection — Claude would default to SKILL.md's tangential / in-session routing on the next turn. The 3-option menu keeps every branch single-turn and atomic, sidestepping the architectural conflict. (Case 2 — no active session — can safely use the multi-turn lock phrase because no hook injection happens when state file doesn't exist.)

## Step 3: Anti-foot-gun notes

- Do NOT run `update_graph.py` on any Step 2 branching response. Only Cases 1 / 2-after-task-arrives transitions into in-session mode where update_graph.py applies.
- Do NOT show the Fathom Score block on any meta-control branching message (Cases 2-waiting, 3, 4). Score block is in-session only.
- Truncate `<current task>` to 80 chars + `…` when displaying in Cases 3/4 — keep terminal output clean.
- If the `session_state.py check` Bash call fails for any reason, fall back to `Read` tool on `~/.fathom-mode/active_session.json` to detect active session — file present = active. Same fallback applies if `session_state.py path` errors.

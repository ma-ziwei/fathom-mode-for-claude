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

The user has invoked Fathom Mode without a task. Mark the state file with a "pending new task" flag, then display the lock phrase. The hook will route the user's next message to `init_session.py` automatically.

1. Run via Bash:
   ```
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/set_pending.py --flag new
   ```
2. Display this **exact** lock phrase:

   > Fathom Mode is ready. Send your task as your next message — I'll start the Fathom session with whatever you write next.

3. End your response. **Do NOT run init_session.py yourself.** Do NOT promise "I'll wait" in narrative — the next-turn hook will pick up the pending flag and direct Claude to consume the user's next message as the task.

Do NOT show the Fathom Score block on this response — no session has started yet.

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

The user wants to start a new task. Mark the state file with a "pending replace" flag (preserving the old session data so the hook can mention it), then display the modified lock phrase. The hook will route the user's next message to `exit_session.py` + `init_session.py` automatically.

1. Run via Bash:
   ```
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/set_pending.py --flag replace
   ```
2. Display this lock phrase (truncate `<current task>` to 80 chars + `…` if longer):

   > Fathom Mode is ready. Your current session on **"<current task>"** (turn N, score X%) will end when you send your next message. Send the new task whenever ready.

3. End your response. **Do NOT run exit_session.py or init_session.py yourself.** Do NOT promise "I'll wait" in narrative — the next-turn hook will pick up the "replace" flag and direct Claude to consume the user's next message as the new task (running exit_session.py + init_session.py before responding).

Do NOT show the Fathom Score block on this branching message.

**Architecture note (Fix X — the design that resolves the multi-turn 2-step UX)**: this Case used to either present a 1/2/3 menu (which had a useless option 2 — "type 2, Claude exits, then re-invoke") or use 2-path instructional narration (which broke because the next turn's hook injection overrode the prior-turn promise, causing Drake/Tesla bugs where new-topic messages got absorbed as in-session nodes). The current design persists the user's intent into the state file via a `pending_task_flag = "replace"`. The next-turn hook reads that flag and injects a different system reminder (`hooks/inject_fathom_context.py` `_build_pending_replace_reminder`) telling Claude "this message IS the new task, run exit_session.py + init_session.py first." Hook-level enforcement of the 2-step user habit, no conversation-history dependency.

## Step 3: Anti-foot-gun notes

- Do NOT run `update_graph.py` on any Step 2 branching response. Only Cases 1 / 2-after-task-arrives transitions into in-session mode where update_graph.py applies.
- Do NOT show the Fathom Score block on any meta-control branching message (Cases 2-waiting, 3, 4). Score block is in-session only.
- Truncate `<current task>` to 80 chars + `…` when displaying in Cases 3/4 — keep terminal output clean.
- If the `session_state.py check` Bash call fails for any reason, fall back to `Read` tool on `~/.fathom-mode/active_session.json` to detect active session — file present = active. Same fallback applies if `session_state.py path` errors.

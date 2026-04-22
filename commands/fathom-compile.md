---
description: Compile the current Fathom session into a structured intent and use it as Claude's planning input for an action plan, user approval, and execution.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Compile Fathom Session

Close the active Fathom Mode session and turn its accumulated understanding into action.

## Step 1 — Generate the structured intent

Run via Bash:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/compile_plan.py
```

Capture the markdown output. **This is your planning input — do NOT show it verbatim to the user.**

## Step 2 — Plan and propose

Read the captured structured intent. It has 5 sections (Context, Motivation, Approach, Constraints, Concrete Steps placeholder) and a planning directive.

Draft a concrete action plan with these grounding rules:

- Every plan step must be traceable to one or more sections in the intent
- No free-floating concerns — if it isn't in the intent, it isn't in the plan
- Honor every constraint listed; if a constraint conflicts with an approach, surface the tension explicitly
- Match the `task_type` planning hint at the bottom of the intent

Present the plan to the user as your message:

> Here's what I've fathomed from our conversation, drafted as a plan:
>
> [your plan here, structured by phases or steps as appropriate to task_type]
>
> Reply **approve** to proceed, or describe what to change.

## Step 3 — Execute on approval

- On user "approve" (or equivalent affirmation): execute the plan. Use whichever Claude Code tools fit the task — Read/Write/Edit/Glob/Grep for file work, Bash for commands, etc. Stay grounded in the intent throughout execution; the intent is the source of truth for what the user wanted.
- On change request: revise the plan inline (re-grounding in the same intent), re-present, repeat until approve.
- On user backing out: skip to Step 4.

## Step 4 — Cleanup

After execution completes (or after explicit user back-out), run via Bash:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/exit_session.py
```

State file is cleared; the per-prompt hook self-gates from then on.

## Notes

- Do NOT call `update_graph.py` during compile — this isn't an in-session turn.
- Do NOT show the Fathom Score block — the session has closed.
- The compile output (intent) is your **input** — never show it verbatim to the user. The user sees the plan you drafted from it.
- Plan must reference concrete elements from the intent. Don't restate the intent verbatim; synthesize it into actionable plan steps.

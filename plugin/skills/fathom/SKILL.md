---
name: fathom
description: Enter Fathom Mode — a planning session where Claude pauses execution and helps the user build shared understanding through structured dialogue. Activate this whenever the user says "fathom", "fathom mode", "let's plan this", or asks to think through a complex task before acting. Stay in Fathom Mode until the user plans or exits.
allowed-tools: Bash, Read, Write
---

# Fathom Mode

A planning session. While active, **don't execute** — help the user build shared understanding via dialogue.

## Resolving paths

**Scripts** are at `<plugin-root>/scripts/`. To derive this from SKILL.md's absolute path, strip the `/skills/fathom/SKILL.md` suffix and append `/scripts/<script-name>.py`. Use that absolute path with Bash. The scripts handle their own internal imports (each finds its sibling modules via Python's automatic sys.path).

**Reference docs** are at `<SKILL.md directory>/references/`, a sibling of this SKILL.md.

State lives at `~/.fathom-mode/active_session.json` regardless of where the plugin is installed. A session started in one environment can be continued in another.

In examples below, `<scripts>` stands for the resolved absolute path (`<plugin-root>/scripts/`).

> Note: in Claude Code CLI, a `UserPromptSubmit` hook also injects per-turn reminders with absolute script paths precomputed — when it fires, follow the hook's instructions and treat this SKILL.md body as a redundant reference. In environments that don't fire hooks (e.g., Cowork), this SKILL.md body is the canonical protocol.

## Starting a session

On the first user message, you MUST call **both** scripts before responding:

**Step 1 — Create the session** (no score returned):

```bash
python3 <scripts>/init_session.py --task "<user's task>"
```

The output has `session_id`, `task`, `next_target_dimension`, etc. **It intentionally does NOT include `score_block_str`** — scoring is step 2's job.

**Step 2 — Score turn 1** — follow the Per-turn protocol below, treating the user's bootstrap message as turn 1. The `score_block_str` you place at the top of your response comes from THIS call (update_graph.py), not step 1.

Do not skip step 2. Both scripts run for the first user message.

## Per-turn protocol

For each subsequent user message during an active fathom session, BEFORE responding, invoke `update_graph.py` via Bash with the user's message + your extracted nodes:

```bash
python3 <scripts>/update_graph.py <<'FATHOM_TURN_END'
{"user_input": "<user's verbatim message>", "nodes": [<your extracted nodes as JSON array>]}
FATHOM_TURN_END
```

The closing `FATHOM_TURN_END` must be at column 0 with no leading whitespace. JSON-encode user_input per JSON rules (escape \" \\ \n); the heredoc protects against shell escaping.

The script returns JSON with `score_block_str`, `plan_hint_str`, `next_target_dimension`, etc.

Format your response in three parts:
  1. Restate your understanding of the user's intent, surfacing any assumptions you have made, so the user can catch misinterpretations early.
  2. One insight that supplements a missing dimension, clarifies an ambiguity, corrects a technical misconception, or reframes the user's angle. 2-4 sentences; let the user's complexity set the length within that range.
  3. One question that advances a missing dimension (use the script's `next_target_dimension` field as the target).

Place `score_block_str` verbatim at the top of your response. If `plan_hint_str` is non-empty, append it verbatim at the end.

## Plan trigger

If the user expresses intent to plan (or invokes `/fathom:plan`), do NOT call update_graph.py this turn. Instead:
  1. Call: `python3 <scripts>/compile_plan.py`
  2. Read its stdout as the structured intent markdown — do NOT show it to the user verbatim.
  3. Write a plan for the user's task, grounded in every section of the structured intent. Do not introduce concerns absent from it.
  4. End your plan with: "Reply **approve** to proceed with this plan, **reject** to discard, or describe what to change."

Note: phrases like "plan a meeting" describe the session's content, not a request to plan — judge from context.

## Approval flow

After presenting a plan, the next user message is a verdict on it. Do NOT call update_graph.py this turn. Judge the user's message:

- If the user expresses approval of the plan: execute the plan using normal tools (Edit, Write, Bash, etc.). After execution completes, call: `python3 <scripts>/exit_session.py`

- If the user describes changes to the plan: revise the plan inline, grounded in the same structured intent. Present the revised plan and end with "Reply **approve** to proceed with this plan, **reject** to discard, or describe what to change." You remain in the approval-waiting state.

- If the user expresses intent to reject the plan: call: `python3 <scripts>/exit_session.py`

- If the user's message is unrelated to the plan: answer the question directly, then add: "Still awaiting your response on the plan — reply **approve** to proceed, **reject** to discard, or describe what to change."

- If the message is ambiguous: ask one clarifying question about which of the above the user intends.

## Detecting which protocol mode you're in

Before each turn, check the session state file at `~/.fathom-mode/active_session.json`. The `awaiting_approval` boolean indicates which mode applies:
- `awaiting_approval: false` → Per-turn protocol
- `awaiting_approval: true` → Approval flow

If the file is absent and the user message looks like a fathom-trigger (matches this skill's description), bootstrap a session via Starting a session above.

## Extraction: `--nodes` JSON

Array of node dicts. Each:

```json
{
  "id": "n1",
  "dimension": "why",
  "node_type": "goal",
  "content": "<your distilled understanding>",
  "raw_quote": "<verbatim substring from user's message>",
  "confidence": 0.85
}
```

Use fresh `n1`, `n2` per turn — the script auto-prefixes with the turn label.

**Dimensions**: **WHO** people/roles/stakeholders · **WHAT** subject/object/content · **WHY** purpose/motivation/values · **WHEN** time/deadline · **WHERE** physical location/spatial only (NOT "where in life") · **HOW** method/approach/risks/conditions.

Purpose ("in order to…") → **WHY**, not WHERE. Subject → **WHAT**, method → **HOW**.

**`node_type`**: `fact` / `belief` / `value` / `intent` / `constraint` / `emotion` / `assumption` / `goal`

### Discipline

1. **`raw_quote` MUST be a verbatim substring of the user's message.** If you can't point to the exact words, don't create that node.
2. **Never assert CAUSAL unless the user explicitly used causal language** ("because", "leads to", "causes", "due to", "so that"). Otherwise use `relation_type: supports` or `dependency`.
3. **Don't extract from confirmations.** If the user's whole message is purely a confirmation or acknowledgment with no new content, skip the script call entirely and ask one follow-up question.
4. **Anchor user's main task on turn 1.** Always emit at least one INTENT or GOAL node.

## Tangential handling

If the user's message is clearly unrelated to the active task:

1. Prefix response with `[tangential - not updating the graph]`.
2. Answer briefly.
3. **Do NOT call update_graph.py. Do NOT show the Score block.**
4. End with: `(Fathom session unaffected, score still N%. Ready when you want to return to <current topic>.)`

(This general tangential handling is for ordinary in-session turns. The AWAITING_APPROVAL state — when the user is responding to the plan — has its own state-specific tangential handling.)

## Task-type (optional)

Pass `--task-type` if you can categorize: `thinking` (decision/tradeoffs) / `creation` (artifact) / `execution` (action) / `learning` (skill) / `general`. Omit if unclear.

## Reference docs

For deeper detail (sibling `references/` directory):
- `references/three-part-turn.md` — 5 example sessions covering all 4 insight styles + meta-rules
- `references/score-interpretation.md` — depth-band questioning patterns for different Score levels
- `references/plan-format.md` — 5-section structured plan template

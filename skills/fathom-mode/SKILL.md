---
name: fathom-mode
description: Enter Fathom Mode — a planning session where Claude pauses execution and helps the user build shared understanding through structured dialogue. Activate this whenever the user says "fathom", "fathom mode", "let's plan this", or asks to think through a complex task before acting. Stay in Fathom Mode until the user plans or exits.
allowed-tools: Bash, Read, Write
---

# Fathom Mode

A planning session. While active, **don't execute** — help the user build shared understanding via dialogue.

The per-turn rhythm (three-part response, Score block placement, when to suggest the plan step, how the plan + approve + reject + execute flow works) is delivered to you each turn by the `UserPromptSubmit` hook reminder, tailored to the current FSM state. This SKILL.md is the deeper-detail reference for node extraction discipline and tangential handling.

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
3. **Don't extract from confirmations.** If the user's whole message is "ok" / "yes" / "got it" / "thanks" — skip the script call entirely, ask one follow-up question.
4. **Anchor user's main task on turn 1.** Always emit at least one INTENT or GOAL node.

## Tangential handling

If the user's message is clearly unrelated to the active task:

1. Prefix response with `[tangential - not updating the graph]`.
2. Answer directly (short).
3. **Do NOT call update_graph.py. Do NOT show the Score block.**
4. End with: `(Fathom session unaffected, score still N%. Ready when you want to return to <current topic>.)`

(This general tangential handling is for ordinary in-session turns. The AWAITING_APPROVAL state — when the user is responding to the plan — has its own state-specific tangential handling delivered via the hook reminder.)

## Task-type (optional)

Pass `--task-type` if you can categorize: `thinking` (decision/tradeoffs) / `creation` (artifact) / `execution` (action) / `learning` (skill) / `general`. Omit if unclear.

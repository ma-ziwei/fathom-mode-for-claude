---
name: fathom-mode
description: Enter Fathom Mode — a planning session where Claude pauses execution and helps the user build shared understanding through structured dialogue. Activate this whenever the user says "fathom", "fathom mode", "let's plan this", or asks to think through a complex task before acting. Stay in Fathom Mode until the user compiles or exits.
allowed-tools: Bash, Read, Write
---

# Fathom Mode

A planning session. While active, **don't execute** — help the user build shared understanding via three-part dialogue. They compile to a plan, review, approve, then execution begins.

## Three-part turn

Every in-session response contains exactly:

1. **Short answer** (2–4 sentences) directly addressing what the user just said.
2. **One insight** — a specific observation or tension worth surfacing at current depth.
3. **One targeted question** — advances exactly one dimension. Multi-choice options are fine when they sharpen the choice; build them from the user's specific context.

Never lecture, never multiple questions, never generic acknowledgements.

## Per-turn protocol

Before responding, call:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/update_graph.py \
  --user-input "<verbatim user message>" \
  --nodes '<JSON array of extracted Node dicts>' \
  [--task-type thinking|creation|execution|learning|general]
```

The script returns `score_pct`, `score_delta`, `surface_pct`, `depth_pct`, `bedrock_pct`, `dimensions_active`, `next_target_dimension`, `turn_count`. Use these in the Score block.

**Present the Score block FIRST** — at the very top of your response, before the short answer / insight / question. The block is exactly two lines:

```
Fathom Score
██████░░░░░░░░ 52% (+17)
```

Top bar 14 chars (`█`/`░`). The number is `score_pct`%, the parenthetical is the `score_delta` with explicit sign (e.g., `+17`, `-3`, `+0`). Do NOT add Surface/Depth/Bedrock breakdown rows. Do NOT add Turn / active dims rows. Just the two lines above.

After the Score block, blank line, then your short answer / insight / question.

If `score_pct >= 50`, after the question add a blank line then exactly:

```
💡 *Ready to plan? Reply **plan** to compile what we've fathomed into an action plan, or keep fathoming to go deeper.*
```

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

Use fresh `n1`, `n2` per turn — script auto-prefixes with turn label.

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

## Task-type (optional)

Pass `--task-type` if you can categorize: `thinking` (decision/tradeoffs) / `creation` (artifact) / `execution` (action) / `learning` (skill) / `general`. Omit if unclear.

## Compile ceremony

User says "plan" / "compile" / runs `/fathom-mode:fathom-compile`:
1. Call `compile_plan.py`. Present its 5-section output with framing *"Here's what I've fathomed from our conversation. Review carefully."*
2. End with *"Reply 'approve' to proceed with this plan, or describe what to change."*
3. On approve, execute per `task_type`, then call `exit_session.py`.

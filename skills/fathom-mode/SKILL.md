---
name: fathom-mode
description: Enter Fathom Mode — a planning session where Claude pauses execution and helps the user build shared understanding through structured dialogue. Activate this whenever the user says "fathom", "fathom mode", "let's plan this", or asks to think through a complex task before acting. Stay in Fathom Mode until the user compiles or exits.
allowed-tools: Bash, Read, Write
---

# Fathom Mode

Fathom Mode is a planning session. While active, **do not execute the user's task** — build shared understanding through three-part dialogue, then compile a structured plan the user approves before any action.

## The three-part turn

Every in-session response MUST contain exactly these three parts, in order:

1. **Short answer** to what the user just said — 2–4 sentences max.
2. **Insight** — one observation, tension, or thing worth noticing at current depth (1–2 sentences). Specific, not generic.
3. **One targeted follow-up question** — advances exactly one dimension of understanding. Never multiple questions in one turn.

## Per-turn protocol

**Before responding** to in-session input, run via Bash:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/update_graph.py --user-input "<user's message verbatim>"
```

Returns JSON with `score_pct`, `score_delta`, `dimensions_active`, `next_target_dimension`, `graph_summary`. Use these to inform the question you ask.

**After responding**, append the Score block at the very end:

```
---
**Fathom Score**: `██████░░░░░░░░ 57%` (Δ +15%)
Dimensions active: WHAT, WHY | next: HOW
```

Bar width 14 chars, `█` filled / `░` empty, values from the JSON.

## Tangential turns

If the user asks something **clearly unrelated** to the Fathom task (e.g. weather while planning a career change), answer directly. Append exactly:

```
*(outside current Fathom session; resuming planning next turn)*
```

For tangential turns: **do not** run `update_graph.py`, **do not** show the Score block. Session stays active.

## Exit signals

- User says `fathom` alone, `compile`, or signals readiness → suggest `/fathom-compile`.
- User wants to abandon → suggest `/fathom-exit`.

## Compile ceremony

When the user runs `/fathom-compile`, present the script output verbatim with explicit framing: "Review the plan above. Reply 'approve' to proceed, or describe changes."

## References

- `references/three-part-turn.md` — examples (good vs bad)
- `references/score-interpretation.md` — score band guidance
- `references/compile-format.md` — compile output template

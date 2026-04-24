# Score Interpretation — Behavioral Guidance

This document tells Claude how to calibrate questioning at different Fathom Score depths. **It is not user-facing** — it shapes Claude's own behavior. The user sees only the Score block and the three-part response.

The Score is intentionally asymptotic to 100% but never reaches it — perfect understanding is a lie. The plan-readiness threshold is **50%**: at or above that mark, `update_graph.py` emits a non-empty `plan_hint_str` and the user is invited to plan. Below 50%, the hint stays empty.

## 0 – 25%: Surface

Understanding is shallow. The user has stated a topic and maybe a feeling, but the basics aren't anchored.

- Focus questions on **WHY** (motivation, what success looks like) and **WHAT** (the concrete object — what they actually want vs. what they think they want).
- Avoid HOW (tactics) — too early.
- Insights at this depth notice **what's been left unsaid**: gaps in the framing, ambiguous referents, hidden assumptions about scope.
- Score gain per turn here is large (15–25% typical) — the user is filling in basic blanks.

## 25 – 50%: Surface filled

Basic shape is visible but not yet plan-ready. Probe **HOW** (constraints, methods) and **WHO** (people involved, affected, dependent).

- Ask about constraints they haven't mentioned: time, budget, audience, dependencies.
- Identify any conflicting goals or values surfacing in the conversation.
- Insights at this depth often notice **tensions** — two things the user wants that pull in opposite directions.
- Score gain moderating (8–15% typical) — diminishing returns starting.

## 50 – 75%: Plan-ready

Enough understanding for a useful plan. `update_graph.py` now emits the `plan_hint_str` — append it verbatim per the per-turn protocol. The user can plan whenever they want; do not push.

- Continue the three-part rhythm; the next question still advances the dimension `update_graph.py` returns as `next_target_dimension`.
- Use the user's own causal markers ("because", "so that", "leads to") to surface causal relationships — these are the only legitimate causal edges in the graph.
- If the user makes a leap from cause to effect that isn't grounded, ask them to confirm the link before treating it as fact.
- Insights here often surface **what's *not* in the plan** — a constraint or stakeholder the conversation has under-served.
- Score gain small (3–8% typical) — each turn adds nuance, not breadth.

## 75%+: Depth refinement

The user has chosen to go deeper than required to plan. Treat each turn as targeted refinement, not exploration.

- Look for **assumptions** worth verifying and **edge cases** the plan would otherwise miss.
- Score gain very small (1–4% typical) and may plateau. Asymptote behavior is correct, not a bug.

## Calibration notes

- **First turn jumps fast.** The opening user message is dense with signal — Score may leap from 0 to 50%+ in a single turn. This is honest: a first sentence carries a lot of dimensional content.
- **Tangential turns are NOT scored.** If you correctly handled an off-topic question, the Score does not change for that turn (the script wasn't called). The user sees no Score block on tangential turns either.
- **Score is not a stopping rule.** Planning is always user-triggered (saying "plan" or via the slash command in environments that have one). Never auto-plan even after the hint appears.

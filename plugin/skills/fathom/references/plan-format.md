# Plan Format

The plan produced by `/fathom:plan` MUST contain these five sections, in this order. `compile_plan.py` (which calls `_compiler.py`) is the deterministic source of truth — it draws every section from the Intent Graph with no LLM call in the loop, so the same graph always renders the same plan.

---

## Template

```markdown
# Fathom Plan

> From <N> turns of dialogue · Final Fathom Score: <X>%

## 1. Intent Summary

One paragraph (3–5 sentences) distilling what the user *actually* wants — not the
literal request as stated, but the underlying intent the dialogue surfaced. Use
the user's own words where they were precise; paraphrase where they
were not.

## 2. Structured Context

Bulleted sections per active 6W dimension. Only include dimensions that have
at least one node. Format:

**WHO** — people involved, affected, or whose judgment matters
- (item)
- (item)

**WHAT** — the concrete subject or deliverable
- (item)

**WHY** — the underlying motivation or goal
- (item)

**HOW** — methods, constraints, criteria
- (item)

**WHEN** — timeline, deadline, sequencing
- (item)

**WHERE** — location, context, setting
- (item)

## 3. Validated Relationships

Cause-effect links the user explicitly confirmed during dialogue. Format:

- *<cause>* → causes → *<effect>*

If none were validated, write: "No causal relationships were explicitly
confirmed in this session."

## 4. Steps

Next steps for actually doing what was planned. Three to five
numbered steps maximum. Each step is one action, one paragraph max.

1. **<Action verb> <object>** — brief description.
2. ...

## 5. Approval Required

Always end with this exact paragraph:

> **Reply 'approve' to proceed with this plan, 'reject' to discard, or describe what to change.**
```

---

## Compiler behavior (`scripts/_compiler.py`)

- **Section 1 (Intent Summary)** uses the highest-confidence INTENT-type or GOAL-type nodes. Falls back to a paraphrase of the original task if no high-confidence intent nodes exist.
- **Section 2 (Structured Context)** iterates over `Dimension` enum values; for each, lists the nodes whose `dimension` field matches. Limited to ~6 items per dimension.
- **Section 3 (Validated Relationships)** only includes edges with `relation_type=CAUSAL` AND `source_type=USER_EXPLICIT`. This is the CFP guarantee — no Claude-inferred causation appears here.
- **Section 4 (Steps)** is derived from GOAL-type and CONSTRAINT-type nodes via a simple template. Task_type-aware variants (thinking / creation / execution / learning) are a future refinement.
- **Section 5 (Approval)** is pure boilerplate, never varies.

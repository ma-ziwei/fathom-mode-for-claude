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

Note: `_compiler.py` does NOT output the plan template above. It outputs a **structured intent** that Claude reads as input, then translates into the user-facing plan. The two 5-section structures are related but not identical — `_compiler.py` sections are the raw material; the plan template sections are the final artifact.

Preceded by a brief instruction header (and an optional task-type directive when set), the compiler produces 5 numbered sections:

1. **Task Anchor** — the user's original request verbatim.
2. **User Expression & System Understanding** — nodes grouped by `raw_quote`, each listed with its extracted `content`.
3. **User-Explicit Causal Relationships** — only edges with `relation_type=CAUSAL` AND `source_type=USER_EXPLICIT`. This is the CFP guarantee: no algorithm-inferred causation appears. Omitted if none.
4. **Constraints & Conflicts** — CONSTRAINT-type nodes plus same-dim CONTRADICTION edges. Omitted if none.
5. **System-Inferred Supplements** — nodes without a `raw_quote` anchor. Omitted if none.

The Intent Graph → structured intent path is deterministic (same graph always produces the same output). Claude then writes the user-facing plan (template above) from the structured intent; that step is non-deterministic, which is why the approval flow lets you reject or revise before execution.

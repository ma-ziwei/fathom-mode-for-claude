# Architecture

Fathom Mode splits cleanly into two layers: a **deterministic Python core** that maintains session state, computes the Fathom Score, detects causal markers, and compiles plans; and **Claude itself**, which handles natural-language understanding, dialogue, and extraction. The division keeps every scored or compiled artifact reproducible from inputs alone — no LLM in the scoring or compile loop.

Both the Claude Code plugin and the Cowork skill ship the same core. The plugin layers a `UserPromptSubmit` hook on top for per-turn orientation reminders; the skill packages the same protocol into `SKILL.md` since Cowork doesn't support hooks.

## Core: `scripts/`

Pure-stdlib Python. No third-party dependencies.

### Data model — `_models.py`

Four enums (`Dimension`, `NodeType`, `RelationType`, `EdgeSource`) and two dataclasses (`Node`, `Edge`). String-valued enums let us `json.dumps(asdict(node))` directly without custom encoders. Nodes carry a 6W `dimension`, a semantic `node_type` (fact / belief / goal / constraint etc.), and a `raw_quote` field that MUST be a verbatim substring of the user's message — extraction discipline enforced at the `SKILL.md` layer.

### Intent Graph — `_graph.py`

Directed graph of nodes + edges, stored as plain dicts (no NetworkX). `add_edge` is the enforcement point for the Causal Fathom Protocol: any edge with `relation_type == CAUSAL` whose `source_type != USER_EXPLICIT` is auto-rewritten to `SUPPORTS` before storage. The algorithm cannot fabricate causal claims — those come only from the user's own words.

Edge conflicts on the same `(source, target)` pair are resolved by a priority-ordered comparator: stronger relation type wins; ties broken by source priority (`USER_EXPLICIT > USER_IMPLIED > ALGORITHM_INFERRED`).

### Score — `_scoring.py`

The displayed Fathom Score is an asymptotic saturating function:

```
fathom_score = 1 - exp(-0.1 * latent_depth)
latent_depth = utility_mass + grounding_mass + entropy_regularizer
```

- **`utility_mass`** per-dim sum of base weights (1.0 for surface dims `what / when / where`, 1.9 for depth dims `why / who / how`) with rank-novelty `1/sqrt(1+i)` — the Nth node in a dimension contributes less than the 1st.
- **`grounding_mass`** reserved for verified causal pairs (2.8 partial, 3.4 verified); see "Known limitations" below.
- **`entropy_regularizer`** `0.15 * normalized Shannon entropy` across credited dimensions — rewards spreading understanding across multiple 6W dims rather than stacking in one.

The curve is monotonically non-decreasing and asymptotic to but never reaches 1.0 — perfect understanding is a lie. Three diagnostic sub-scores (surface coverage / depth penetration / bedrock grounding) are also exposed for introspection.

Plan-readiness threshold is 50%. At or above that mark, `update_graph.py` emits a non-empty `plan_hint_str` that Claude appends to the response. The threshold lives in the same file that produces the score — no one-turn lag like an externally-judged threshold would have.

### Dimension selector — `_dimensions.py`

Universal priority: HOW=6, WHY=5, WHO=4, WHAT=3, WHEN=2, WHERE=1. Next-target dimension = `argmax(priority / (count + 1))` — a dim with high priority and low coverage rises to the top; `+1` avoids division-by-zero at count=0.

### Causal markers — `_causal.py`

Regex-based detection of user-stated causal language. Three marker classes:

- **Forward** (`therefore`, `causes`, `leads to`, `results in`, `which means`, `consequently`) — `cause MARKER effect`
- **Backward** (`because`, `due to`, `as a result of`, `caused by`, `owing to`) — `effect MARKER cause`
- **Purpose** (`in order to`, `so that`, `for the purpose of`, ...) — detected but deliberately NEVER promoted to CAUSAL per CFP (purpose is intentionality, not causation).

Matched cause / effect fragments are overlap-scored against existing graph nodes' `content` + `raw_quote`. If both sides clear `min_overlap=0.3`, a `USER_EXPLICIT CAUSAL` edge is emitted. The edge flows back into `_graph.add_edge`; CFP enforcement is guaranteed there.

### Compiler — `_compiler.py`

Renders an `IntentGraph` into a 5-section structured-intent markdown block that Claude reads as planning input:

1. **Task Anchor** — the user's original request verbatim
2. **User Expression & System Understanding** — nodes grouped by `raw_quote` (anchored) with the system's extracted `content` attached
3. **User-Explicit Causal Relationships** — only `USER_EXPLICIT CAUSAL` edges (CFP discipline; omitted if none)
4. **Constraints & Conflicts** — CONSTRAINT-type nodes + same-dim CONTRADICTION edges (omitted if none)
5. **System-Inferred Supplements** — nodes without `raw_quote` anchor (omitted if none)

Sections 3–5 auto-omit when empty. Output is NOT the user-visible plan; it's structured intent Claude reads, then uses to write the plan shown to the user.

### Entry points

- **`init_session.py`** — create a fresh session with optional first-turn nodes
- **`update_graph.py`** — per-turn: extract nodes from Claude's JSON, detect causal markers, score, persist
- **`compile_plan.py`** — convergence point for the plan step. Sets `awaiting_approval=True` on state BEFORE rendering, so the FSM transitions even if render fails
- **`exit_session.py`** — clear state, idempotent
- **`render_status.py`** — user-facing markdown for `/fathom:status`

### State — `session_state.py`

Always `~/.fathom-mode/active_session.json`. The plugin deliberately ignores `CLAUDE_PLUGIN_DATA` even though Claude Code populates it: that env var is exported to **hook** subprocesses but NOT to **Bash-tool** subprocesses. If we honored it, hook-spawned `init_session` would write to one path while Claude's bash-tool `update_graph` writes to another, and state would split. By forcing `~/.fathom-mode/` everywhere, all paths converge on one file — across plugin and skill too, so a session started in Cowork can be continued in Claude Code on the same machine.

State writes are atomic (temp file + `replace`). JSON uses `ensure_ascii=True` so lone UTF-16 surrogates from heredoc `\uXXXX` escapes round-trip losslessly.

## Plugin layer: `plugin/`

### Hook — `hooks/inject_fathom_context.py`

`UserPromptSubmit` hook. Four behaviors by prompt shape:

1. **Exactly `/fathom:start`** — wipe state to a pending-new-task stub, block + "Fathom Mode is ready." The next plain message becomes the task.
2. **`/fathom:start <task>`** — run `init_session.py` via subprocess, inject a session-init reminder for Claude.
3. **Other `/fathom:*` commands** — skip injection, let the slash-command body drive.
4. **Any other message** — dispatch on persisted state:
   - `pending_new_task` flag → this message IS the new task (mirror of behavior 2)
   - real session + `awaiting_approval=False` → IN_SESSION reminder (three-part rhythm + Score block + data-driven plan hint)
   - real session + `awaiting_approval=True` → AWAITING_APPROVAL reminder (judge approve / reject / revise)
   - no state → self-gate silently

The hook always exits 0 so a hook bug never blocks the user's prompt.

### Slash commands — `commands/*.md`

- **`/fathom:start <task>`** — entry point (hook has already run init; body only handles defensive fallback)
- **`/fathom:status`** — render the current graph + Score
- **`/fathom:plan`** — compile the session
- **`/fathom:exit`** — clear state

### Auto-triggered skill — `skills/fathom/SKILL.md`

Short reference covering `--nodes` JSON schema, dimension definitions, and extraction discipline. The per-turn protocol (three-part response, Score block placement, plan flow) is delivered by the hook reminder each turn — SKILL.md only carries the extraction deep-detail.

## Skill layer: `skill/`

> Note: the plugin has its own `skills/fathom/` subdirectory (auto-triggered inside Claude Code sessions). That's distinct from the top-level `skill/` folder in this repo, which is the standalone Cowork distribution. Same `SKILL.md` content, different packaging contexts.

Same `scripts/` as the plugin (physically duplicated — simpler than symlinks at this scope). `SKILL.md` absorbs what the plugin's hook would otherwise deliver per turn: three-part response format, per-turn `update_graph.py` invocation instructions, plan trigger flow, approval flow, tangential handling. Since Cowork doesn't support `UserPromptSubmit` hooks (Anthropic issues #41845, #27398), the skill body must persist the protocol in Claude's context itself.

## Division of labor

| Layer | Responsibility |
|---|---|
| Claude | Natural-language understanding, node extraction, three-part response, approve / reject judgment |
| Python scripts | State I/O, graph mutation, CFP enforcement, scoring, dimension selection, compilation |
| Hook (plugin only) | Per-turn orientation reminder, FSM state dispatch |
| SKILL.md body (skill only) | Carries the protocol instructions the hook would deliver |

Everything scored or compiled is reproducible: same Intent Graph → same plan, no LLM call in the compile loop. That's what makes the output auditable. A user can disagree with Claude's extraction of their message (catch it at the "restate understanding" step), but once the graph is stable the plan it produces is deterministic.

## State flow per turn

1. User submits a message.
2. Hook fires (plugin) or SKILL body is present in context (skill).
3. Claude reads the reminder, extracts nodes from the user's message, invokes `update_graph.py` via Bash heredoc with a JSON payload (`{user_input, nodes}`).
4. `update_graph.py` reconstructs graph from state, appends new nodes, detects causal markers, scores, persists.
5. Stdout returns `score_block_str`, `plan_hint_str`, `next_target_dimension`, graph summary.
6. Claude writes the three-part response, placing `score_block_str` at the top verbatim and appending `plan_hint_str` if non-empty.
7. When the user says "plan", Claude calls `compile_plan.py` instead of `update_graph.py`. That call sets `awaiting_approval=True` on state, then renders the structured intent. Claude reads it and writes a plan for the user, asking for approve / reject / revise.
8. Next turn, the hook (or SKILL body) dispatches to the AWAITING_APPROVAL reminder. Approve → execute via normal Claude Code tools → `exit_session.py`. Reject → `exit_session.py`. Revise → update plan inline, stay in approval state.

## Heredoc + stdin payload

Per-turn payloads (the user message plus Claude's extracted nodes) are routed through `stdin` as JSON via a Bash heredoc with a quoted delimiter:

```
python3 update_graph.py <<'FATHOM_TURN_END'
{"user_input": "...", "nodes": [...]}
FATHOM_TURN_END
```

The quoted delimiter bypasses shell escaping entirely — apostrophes, em-dashes, `$` signs, and Unicode in the user's message pass through literally, no quoting required. Scripts decode `sys.stdin.buffer` as UTF-8 explicitly rather than relying on the OS default codec, so non-ASCII content (Chinese, emoji, smart quotes) survives intact across platforms.

## Known limitations

- **`verified_causal_pairs` is a reserved field.** The current design does not implement LLM-driven causal verification — that algorithm was designed for reflective chat scenarios and intentionally not adopted for Claude Code's action-oriented context. The field is plumbed through scoring as a future extension hook but populated only if a later implementation needs it.
- **Cowork hook behavior** — `UserPromptSubmit` may not fire on Cowork. The skill is designed to work regardless: the `SKILL.md` body carries the full protocol, so the per-turn reminder is not essential.
- **claude.ai web / mobile** — no subprocess available, out of scope.
- **Single active session per machine** — state is a single file. Concurrent sessions in two project directories on the same machine would clash.

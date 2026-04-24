# Fathom Mode

A planning session protocol for AI interactions. While active, Claude pauses execution and helps you build shared understanding through structured dialogue: restate-understanding + four-style insight + dimension-targeting question, with a visible Fathom Score that climbs as understanding deepens. Compile the session into a plan; review, approve, and only then execute.

> **Status — hackathon build (April 21–27, 2026).** Plumbing is real and end-to-end; the Score, Intent Graph, Compiler, and Causal Fathom Protocol are implemented from scratch in `scripts/`. Treat this as a working preview — APIs and on-disk state shape may still change before a tagged release.

## Two distributions, one protocol

| Distribution | For | Where to install | Per-turn reinforcement |
|---|---|---|---|
| [`plugin/`](plugin/) | Claude Code (terminal / IDE) users | `/plugin install <repo>/plugin` | `UserPromptSubmit` hook fires every turn |
| [`skill/`](skill/) | Cowork (desktop app) users | Repackage as a Cowork skill bundle and install via Settings → Skills | Skill body persists in context (no hook; Cowork doesn't support hooks per Anthropic issues #41845, #27398) |

Both deliver the same deterministic Score / compile pipeline and the same protocol vocabulary (`plan` / `approve` / `reject` / `execute` + four insight styles `supplement` / `clarify` / `correct` / `reframe`). Pick by environment.

For Claude.ai web / mobile, neither distribution applies (no subprocess available in browser sandbox). Out of scope for this project.

## Quick start — Claude Code plugin

1. Clone this repo to any local path.
2. In Claude Code: `/plugin install <absolute-path-to-repo>/plugin`
3. Verify: `/help` lists `fathom:start` / `fathom:status` / `fathom:plan` / `fathom:exit`.
4. Start a session: `/fathom:start design a Lotka-Volterra visualizer` (or whatever your task).

See [`plugin/README.md`](plugin/README.md) for plugin-specific details (architecture, hook design, install variants).

## Quick start — Cowork skill

1. Clone this repo to any local path.
2. Repackage `skill/` as a Cowork skill bundle (per Cowork's skill installation flow).
3. Install in Cowork via Settings → Skills.
4. Trigger by saying "let's plan this" / "fathom mode" or by typing `/fathom` in chat.

The skill auto-discovers its bundled scripts and uses Bash to invoke them. State lives at `~/.fathom-mode/active_session.json` — shared with the plugin, so a session started in Cowork can be continued in Claude Code (and vice versa) on the same machine.

## What is Fathom Mode

A **planning session mode** for AI interactions. While active, Claude pauses execution and runs a deliberate three-part dialogue per turn:

- **Understanding restate** — Claude reflects back what it has taken from your message, including any assumptions, so you can catch misinterpretations early
- **One insight** — supplements a missing dimension, clarifies an ambiguity, corrects a technical misconception, or reframes your angle
- **One targeted follow-up question** — advancing one dimension of understanding the dialogue has not yet covered

A **Fathom Score** climbs visibly with each in-session turn — fast initial gain, exponentially diminishing returns, asymptotic to (but never reaching) 100%. When you're ready, you say `/fathom:plan` (plugin) or "plan" (skill) and the session is rendered into a plan you can review, refine, and approve before any execution begins.

The plan-drafting step is deterministic. The same Intent Graph always produces the same plan, no LLM call in between, fully auditable.

## Why it exists

Most weak LLM output comes from ambiguous user input. The conventional answer is "write better prompts," but that pushes the burden onto the user without giving them a structure to think in. Fathom Mode front-loads intent-structuring as a first-class protocol — a discrete block of work that separates "figuring out what to do" from "doing it."

Opus 4.7 already handles ambiguity better than its predecessors: Anthropic's own guidance is *"Specify the task up front, in the first turn. Ambiguous prompts conveyed progressively across many turns tend to reduce both token efficiency and, sometimes, overall quality."* Fathom Mode helps users get to that well-specified first turn — it's a **layered complement** to Opus 4.7's adaptive thinking, not a replacement for it. When you ask something tangential mid-session, Claude correctly answers it directly without forcing it through the protocol; that's the model's judgment, by design.

## Architecture (brief)

Both distributions share the same Python algorithm core in `scripts/`:
- `_models.py` — Node / Edge / Dimension / NodeType / RelationType / EdgeSource enums + dataclasses
- `_graph.py` — IntentGraph storage with Causal Fathom Protocol downgrade enforced at edge insertion
- `_dimensions.py` — 6W priority + next-target dimension selector
- `_causal.py` — User-explicit causal marker detection
- `_scoring.py` — Fathom Score formula (asymptotic, dimension-aware)
- `_compiler.py` — 5-section structured intent renderer
- `init_session.py` / `update_graph.py` / `compile_plan.py` / `exit_session.py` — entry points

The plugin layers on:
- `hooks/inject_fathom_context.py` — `UserPromptSubmit` hook that injects per-turn reminders
- `commands/*.md` — slash command bodies for explicit entry points
- `skills/fathom/SKILL.md` + `references/` — reference material for Claude

The skill layers on:
- `SKILL.md` (body absorbs what the plugin's hook delivers per turn — turn-protocol instructions live in the skill body since the hook isn't available)
- `references/` — same reference docs as the plugin
- `scripts/` — duplicated copy of the plugin's scripts for self-contained operation

Script duplication between `plugin/scripts/` and `skill/scripts/` is intentional — simpler than symlinking or clever-sharing at this scope. When updating algorithm code, update both copies.

State path is shared (`~/.fathom-mode/active_session.json`) so sessions migrate seamlessly between environments on the same machine.

## Origin & Rule 1 Compliance

This concept originates from prior publications — the SSRN paper *Fathom-then-Generate: A Reversible Intent Alignment Protocol* and the Substack series on Intent Alignment by Lawrence Ma. This repository is a **fresh implementation built entirely during the Built with Opus 4.7 hackathon**, April 21–27, 2026 (Pacific Time). The prior `ftg` Python library at `github.com/ma-ziwei/fathom-mode` served as conceptual reference only; **no code was copied** — concepts and architectural ideas are inspiration, not provenance.

## License

MIT — see [LICENSE](LICENSE).

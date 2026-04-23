# Fathom Mode (Claude Code Plugin)

> **Status — Day 1 skeleton.** Plumbing is real and end-to-end. Algorithms (Score, Intent Graph, Compiler, Causal Fathom Protocol) are stubs returning plausible placeholder data. Days 2–5 fill in the real logic. Don't install for production use yet.

## What is Fathom Mode

Fathom Mode is a **planning session mode** for AI interactions. While it is active, Claude pauses execution and helps you build shared understanding through a deliberate three-part dialogue:

- **Understanding restate** — Claude reflects back what it has taken from your message, including any assumptions, so you can catch misinterpretations early
- **One insight** — supplements a missing dimension, clarifies an ambiguity, corrects a technical misconception, or reframes your angle
- **One targeted follow-up question** — advancing one dimension of understanding the dialogue has not yet covered

A **Fathom Score** climbs visibly with each in-session turn — fast initial gain, exponentially diminishing returns, asymptotic to (but never reaching) 100%. When you're ready, you say `/fathom-plan` and the session is rendered into a plan you can review, refine, and approve before any execution begins.

The plan step is deterministic. The same Intent Graph always produces the same plan, no LLM call in between, fully auditable.

## Why it exists

Most weak LLM output comes from ambiguous user input. The conventional answer is "write better prompts," but that pushes the burden onto the user without giving them a structure to think in. Fathom Mode front-loads intent-structuring as a first-class protocol — a discrete block of work that separates "figuring out what to do" from "doing it."

Opus 4.7 already handles ambiguity better than its predecessors: Anthropic's own guidance is *"Specify the task up front, in the first turn. Ambiguous prompts conveyed progressively across many turns tend to reduce both token efficiency and, sometimes, overall quality."* Fathom Mode helps users get to that well-specified first turn — it's a **layered complement** to Opus 4.7's adaptive thinking, not a replacement for it. When you ask something tangential mid-session, Claude correctly answers it directly without forcing it through the protocol; that's the model's judgment, by design.

## Install

### Claude Code (primary, Day 1 verified surface)

1. Clone or download this repo to a local path, e.g.
   `C:\Users\Hyte\Desktop\fathom-mode-main\fathom-claude\fathom-mode-plugin`
2. In Claude Code, install via the local path. Two options:
   - **Project-scoped**: from the project where you want to use it, `/plugin install <absolute-path>`.
   - **User-scoped**: `/plugin marketplace add <absolute-path>` and then enable from `/plugin`.
3. Verify: `/help` should now list `fathom`, `fathom-status`, `fathom-plan`, `fathom-exit` under "Plugin commands."

Requires Python 3 on `PATH` (`python3` invocation). No third-party Python dependencies for the Day 1 stub.

### Cowork

Should install via the same plugin format ([Cowork plugin docs](https://support.claude.com/en/articles/13837440-use-plugins-in-claude-cowork)). The `UserPromptSubmit` hook may not fire on Cowork — under verification. If hooks don't fire on Cowork, the skill + commands still work; only the per-turn orientation reminder is missing.

### claude.ai (web)

Plugins as bundled here are not yet a supported install path on claude.ai web. The skill content can be repackaged as a Skill zip via Settings > Features (Pro / Max / Team / Enterprise plans with code execution enabled). State persistence on claude.ai is per-conversation (no cross-session state).

## Usage

```
/fathom <a complex task you want to plan>
```

Claude enters Fathom Mode. Each in-session turn produces the three-part response and a Score block. You can:

```
/fathom-status        # inspect the current Intent Graph and Score
/fathom-plan          # plan from the session; reply 'approve' to proceed
/fathom-exit          # leave Fathom Mode (clears state)
```

### Example

```
> /fathom I want to pivot into ML from a backend background

[three-part response from Claude]
---
**Fathom Score**: `███████░░░░░░░ 47%` (Δ +47%)
Dimensions active: WHO, WHAT, WHY | next: HOW

> I've got 6 years backend, mostly Python and Postgres. Targeting applied roles, not research.

[three-part response]
---
**Fathom Score**: `█████████░░░░░ 63%` (Δ +16%)
...

> /fathom-plan

[5-section plan]

**Reply 'approve' to proceed with this plan, or describe what to change.**

> approve

[execution begins]
```

If you ask something tangential mid-session ("what time is it in Tokyo?") Claude will answer it directly and append `*(outside current Fathom session; resuming planning next turn)*` — no Score change for that turn.

## How it works

Single plugin package containing four kinds of components:

- **Skill** (`skills/fathom-mode/SKILL.md`) — auto-triggered description tells Claude when to switch into Fathom Mode behaviour. References in `skills/fathom-mode/references/` cover the three-part turn examples, Score-band guidance, and plan format template.
- **Slash commands** (`commands/fathom*.md`) — explicit boundaries for entering, inspecting, planning, and exiting a session.
- **Hook** (`hooks/inject_fathom_context.py`) — `UserPromptSubmit` hook that self-gates on the session state file. When a session is active, injects a short orientation reminder via `additionalContext`. When inactive, exits silently.
- **Scripts** (`scripts/*.py`) — pure-Python deterministic logic for session state, graph updates, score, status rendering, the plan step, exit. No LLM calls; Claude itself does the per-turn extraction work and shells out to the scripts for the deterministic operations.

Session state lives at `${CLAUDE_PLUGIN_DATA}/active_session.json`, isolated per Claude Code install.

## Origin & Rule 1 Compliance

This concept originates from prior publications — the SSRN paper *Fathom-then-Generate: A Reversible Intent Alignment Protocol* and the Substack series on Intent Alignment by Lawrence Ma. This repository is a **fresh implementation built entirely during the Built with Opus 4.7 hackathon**, April 21–27, 2026 (Pacific Time). The prior `ftg` Python library at `github.com/ma-ziwei/fathom-mode` served as conceptual reference only; **no code was copied** — concepts and architectural ideas are inspiration, not provenance.

## Roadmap (Days 2–5)

- **Day 2** — real Fathom Score formula (`1 - exp(-0.10 * latent_depth)`, asymptotic 100%, dimension-aware diminishing returns)
- **Day 3** — real Intent Graph operations (NetworkX-free, dict-backed, with the CFP downgrade rule baked into edge insertion)
- **Day 4** — real Compiler module (5-section structured intent assembly from the graph) + Causal Fathom Protocol (linguistic causal-marker detection limiting causal edges to user-explicit relationships)
- **Day 5** — polish, demo recording, cross-platform fixes (Cowork hooks, claude.ai Skill repackaging), README finalization, marketplace submission prep

## License

MIT — see [LICENSE](LICENSE).

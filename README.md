# Fathom Mode for Claude

Pause execution. Clarify intent. Then let Claude act from an approved plan.

Fathom Mode is a planning session mode for Claude Code and Cowork. It helps Claude restate its understanding, surface missing details, ask one targeted follow-up at a time, and compile the conversation into a structured plan before executing complex coding or computer-use tasks.

## What Claude does in Fathom Mode

- **Restates its understanding** so you can catch wrong assumptions before execution starts.
- **Surfaces missing details and ambiguity** instead of silently guessing.
- **Asks one targeted follow-up per turn** to deepen the task along the least-covered dimension.
- **Tracks understanding with a visible Fathom Score** so the planning session feels like progress, not endless chatting.
- **Compiles the session into a structured plan** you review and approve before Claude executes.

## Quick start

### Claude Code plugin

```
/plugin marketplace add https://github.com/ma-ziwei/fathom-mode-for-claude.git
/plugin install fathom@fathom-mode
/fathom:start refactor this React component so it's easier to maintain
```

Claude enters a planning session instead of immediately editing files. Use `/fathom:status` to see current understanding, `/fathom:plan` when you want a structured plan, `/fathom:exit` to leave.

### Cowork skill

1. Clone this repo, or download `fathom-skill.zip` from the latest [release](https://github.com/ma-ziwei/fathom-mode-for-claude/releases).
2. In Claude Desktop → Cowork → **Customize → Skills → Upload**, select the zip.
3. Start a task and type `/fathom` or say "let's plan this." Claude enters the protocol.

## Example session

A real turn looks like this. Score block first, then a three-part response (understanding restate, one insight, one question):

```
You:  Build a dashboard for tracking model eval runs.

Claude:
      Fathom Score
      ██████░░░░░░░░ 43% (+43)

      I'm reading this as a tool you'd run locally alongside your
      experiments — single user, not a shared service, no auth layer.
      Say if that's off.

      One thing worth flagging: "dashboard" is doing a lot of work
      in this sentence. Live-monitoring (refresh every few seconds,
      current job status, resource usage) is a weekend afternoon;
      post-run reporting (compare N completed runs, sort by metrics,
      export tables) is a different project with different trade-offs.
      The word is the same, the code is not.

      Which matters more — watching runs in flight, or comparing them
      after they finish?

You:  Comparing after, mostly. But I'd like a small glance panel for
      what's currently running — not the focus, just a corner.

      ... (several turns later, Score ~75%)

      💡 Ready to plan? Reply plan.

You:  plan

Claude: [runs compile_plan.py — produces a 5-section structured plan
         covering task anchor, user expression + system understanding,
         explicit causal relationships, constraints + conflicts, and
         system-inferred supplements]

      Reply approve to proceed with this plan, reject to discard, or
      describe what to change.

You:  approve

Claude: [executes from the compiled plan — files, commands, grounded
         in every dimension of the session]
```

## How Fathom Mode works

While a task is in Fathom Mode, Claude does not immediately execute it. Each turn follows a three-part rhythm:

1. A short **understanding restate** with any assumptions surfaced explicitly.
2. One **insight** — supplementing a missing dimension, clarifying an ambiguity, correcting a misconception, or reframing your angle.
3. One **targeted follow-up question** advancing the dimension least covered so far.

The visible **Fathom Score** climbs with each in-session turn — fast early, exponentially diminishing, asymptotic to (but never reaching) 100%. It's a gauge of dialogue depth, not an objective measure of truth.

When you're ready, `plan` compiles the session into a structured plan. The compile is **deterministic**: the same Intent Graph always produces the same plan, with no LLM call in the middle. Review it, approve it, and only then does Claude execute. After approval, Claude acts from the compiled plan, reducing ambiguity-driven misfires and rework on complex multi-step tasks.

If you ask something tangential mid-session (a quick definition, an unrelated question), Claude answers directly — Fathom Mode is an active session, not a cage. The protocol resumes when the task resumes.

## Two distributions, one protocol

| Distribution | Use when | Install |
|---|---|---|
| **Claude Code plugin** | You use Claude Code in terminal or IDE | `/plugin install fathom@fathom-mode` |
| **Cowork skill** | You use Claude Cowork desktop | Upload skill bundle in Customize → Skills |

Both share the same session state (`~/.fathom-mode/active_session.json`) and the same deterministic plan compiler. A session you start in Cowork can be continued in Claude Code on the same machine, and vice versa.

**The skill is not a lesser version of the plugin.** It runs the full protocol — same scripts, same Intent Graph, same deterministic compile, same four-style insight palette. The only difference is how the per-turn reminder reaches Claude: the plugin uses a `UserPromptSubmit` hook; the skill relies on Claude holding the protocol in context. In practice, sessions run in Cowork feel just as coherent as sessions in Claude Code. If you live in Cowork, install the skill — you're getting Fathom Mode in full.

If you use both environments, install both. State is shared on a single machine, so you can start a session in one and finish it in the other.

## Why use it

Fathom Mode is most useful for:

- Ambiguous tasks where you're not sure what you want yet
- Multi-step coding work where misunderstanding early compounds late
- Computer-use tasks with long side-effect chains
- High-stakes refactors, migrations, or new-system design

It is not meant for simple factual questions, fully specified one-shot commands, or cases where you want Claude to answer immediately. Don't use it for "what does this function do" — use it for "I want to replace this architecture."

Most weak LLM output comes from ambiguous input, and Opus already handles ambiguity well on its own. Fathom Mode is a **layered complement** to the model's judgment, not a replacement — it gives you a structured dialogue surface for the tasks where a few minutes of intent-clarification saves hours of rework.

## Requirements

- **Claude Code** (terminal or IDE) for the plugin distribution
- **Claude Cowork** (desktop app) for the skill distribution
- **Python 3** available as `python3` on your PATH

Claude.ai web and mobile are out of scope — neither environment supports the subprocess invocations Fathom Mode relies on.

## Troubleshooting

- **Session feels stuck or you want to start over**: `/fathom:exit` (plugin) or ask Claude to end the session (skill), then start fresh.
- **Score plateaus without a plan-ready hint**: the task may warrant continuing. Just type `plan` — Claude will compile whatever depth you've reached.
- **Install fails with SSH authentication error**: the shortcut `<owner>/<repo>` form may default to SSH URL. Use the full HTTPS URL instead (as shown in Quick start above).
- **Plugin command not found after install**: run `/plugin install fathom@fathom-mode` again from inside a Claude Code session, verify with `/help`.
- **Skill not triggering in Cowork**: type `/fathom` explicitly instead of relying on natural-language trigger.

## Origin

Fathom Mode originates from Lawrence Ma's prior work on intent alignment — the SSRN paper *Fathom-then-Generate: A Reversible Intent Alignment Protocol* and the [Intent Alignment Substack series](https://intentalignment.substack.com). This repository is a Claude-native implementation that adapts the original concepts — Intent Graph, Fathom Score, deterministic compile — into a planning workflow for Claude Code and Cowork. Compared with the original reflective Python library, this version is optimized for action-oriented planning sessions: clarify the task, compile a plan, approve, then execute.

## Architecture

Fathom Mode is built around a deterministic Intent Graph and compiler. Claude supplies language understanding and natural dialogue; Python scripts maintain graph state, score progress, and render the final plan. The Claude Code plugin reinforces the protocol with a `UserPromptSubmit` hook that injects a per-turn reminder; the Cowork skill carries the same protocol instructions via skill content (Cowork doesn't support hooks).

For module-level details and design rationale, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Contributing

Issues and pull requests are welcome. Bug reports, install problems, and examples of confusing Fathom sessions are especially useful. For larger features, please open an issue first — Fathom Mode isn't a typical feature library, and many changes affect the protocol's identity.

## License

MIT — see [LICENSE](LICENSE).

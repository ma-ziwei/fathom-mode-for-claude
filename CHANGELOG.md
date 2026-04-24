# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- `init_session.py` restores a first-turn score stub (35–55% based on task length) when called without `--nodes`. Previously this path returned 0%, and if Claude called `init_session.py` but skipped `update_graph.py` on the first user message (a common interpretation of the "subsequent user message" phrasing in the per-turn protocol), users saw a `0% (+0)` score block on turn 1. `update_graph.py` overwrites the stub with the real computed score on its first call, so the stub only affects the visible first-turn baseline. Trade-off: turn-1 delta becomes `real_score − stub` instead of `real_score − 0`, i.e., smaller but still positive in practice.
- `init_session.py` and `update_graph.py` now probe `stdin` with a 0.1s `select` timeout before attempting to read a JSON payload. Previously, `sys.stdin.buffer.read()` blocked unconditionally when stdin was a non-TTY file descriptor, which caused 45-second hangs (hitting the platform RPC timeout) in Cowork's Bash tool, where the subprocess is handed an open-but-empty stdin pipe that never sends EOF. Normal heredoc invocations remain unaffected (data is available instantly; the 0.1s probe window is a no-op).
- `update_graph.py` now auto-bootstraps a session when none exists, using the current `user_input` as the task description. Previously, calling `update_graph.py` before `init_session.py` returned a `no_active_session` error, which was a common footgun in environments where no hook runs `init_session.py` first (Cowork, manual CLI invocation). The traditional flow (explicit `init_session.py` → `update_graph.py`) still works and is still the recommended path for callers that want a custom task summary or task type.
- `plugin/skills/fathom/SKILL.md` now carries the full per-turn protocol (script path resolution, session bootstrap, `update_graph.py` invocation, plan flow, approval flow) rather than deferring to the `UserPromptSubmit` hook. Previously, uploading `fathom-plugin.zip` to Cowork (which doesn't fire hooks) produced noisy path and `no_active_session` errors on the first turn while Claude reconstructed the flow. The plugin now works cleanly in both hook-supporting (Claude Code CLI, Claude Desktop Chat tab) and non-hook environments (Cowork).

## [0.1.0] — 2026-04-24

Initial public release.

### Added

- **Core algorithm** — Intent Graph with Causal Fathom Protocol (CFP) downgrade enforced at edge insertion; asymptotic dimension-weighted Fathom Score; regex-based causal marker detection; deterministic 5-section plan compiler. All pure-stdlib Python, no third-party dependencies.
- **Claude Code plugin** (`plugin/`) — 4 slash commands (`/fathom:start`, `/fathom:status`, `/fathom:plan`, `/fathom:exit`); `UserPromptSubmit` hook dispatching per-turn reminders by session state (IN_SESSION / AWAITING_APPROVAL); marketplace install via `/plugin marketplace add` or zip upload via Claude Desktop's Customize → Plugins UI.
- **Cowork skill** (`skill/`) — standalone bundle that carries the same protocol via `SKILL.md` body (Cowork doesn't expose hooks).
- **Shared state** at `~/.fathom-mode/active_session.json` lets users continue a session across Claude Code and Cowork on the same machine.

[0.1.0]: https://github.com/ma-ziwei/fathom-mode-for-claude/releases/tag/v0.1.0

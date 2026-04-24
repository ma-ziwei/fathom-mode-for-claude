# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-04-24

Initial public release.

### Added

- **Core algorithm** — Intent Graph with Causal Fathom Protocol (CFP) downgrade enforced at edge insertion; asymptotic dimension-weighted Fathom Score; regex-based causal marker detection; deterministic 5-section plan compiler. All pure-stdlib Python, no third-party dependencies.
- **Claude Code plugin** (`plugin/`) — 4 slash commands (`/fathom:start`, `/fathom:status`, `/fathom:plan`, `/fathom:exit`); `UserPromptSubmit` hook dispatching per-turn reminders by session state (IN_SESSION / AWAITING_APPROVAL); marketplace install via `/plugin marketplace add` or zip upload via Claude Desktop's Customize → Plugins UI.
- **Cowork skill** (`skill/`) — standalone bundle that carries the same protocol via `SKILL.md` body (Cowork doesn't expose hooks).
- **Shared state** at `~/.fathom-mode/active_session.json` lets users continue a session across Claude Code and Cowork on the same machine.

[0.1.0]: https://github.com/ma-ziwei/fathom-mode-for-claude/releases/tag/v0.1.0

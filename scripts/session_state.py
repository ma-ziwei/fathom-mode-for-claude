#!/usr/bin/env python3
"""
Shared session-state helper for Fathom Mode scripts.

State lives at ${CLAUDE_PLUGIN_DATA}/active_session.json — a single active session
per plugin install. Day 2+ may extend to per-Claude-session keying using
session_id from hook payloads; for Day 1 a single active session is enough.

Cross-platform: pathlib.Path everywhere, UTF-8 reads/writes, no shell-isms.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Cross-platform stdout: Windows defaults to GBK / cp1252 which can't encode
# the box-drawing characters (█░) the Score bar uses. Reconfigure once on
# import so every script that uses session_state gets UTF-8 stdout for free.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except (AttributeError, OSError):
    pass


def _state_dir() -> Path:
    """
    Resolve the plugin's persistent data directory.

    ALWAYS ~/.fathom-mode/ — we deliberately ignore CLAUDE_PLUGIN_DATA.

    Reason: CLAUDE_PLUGIN_DATA is exported to hook subprocesses but NOT
    to Bash-tool subprocesses (Anthropic platform behavior on Windows
    confirmed empirically). If we honored the env var, the hook's
    init_session subprocess would write to the PLUGIN_DATA path while
    Claude's Bash-tool calls to update_graph.py would write to
    ~/.fathom-mode/. State files would split, hook reads stale state
    from one path while Bash writes to another, and bare /fathom-mode:fathom
    appears to "wipe" but the next message resurrects the old session.

    By forcing ~/.fathom-mode/ everywhere (hook, hook subprocess, Bash
    subprocess), all access converges on a single file. Cross-platform
    OK because Path.home() resolves correctly on Win/Mac/Linux.
    """
    return Path.home() / ".fathom-mode"


STATE_PATH: Path = _state_dir() / "active_session.json"


def load_state() -> dict | None:
    """Return the current session state dict, or None if no active session."""
    if not STATE_PATH.exists():
        return None
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def save_state(state: dict) -> None:
    """Write the session state dict atomically (temp file + replace)."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_PATH)


def clear_state() -> None:
    """Delete the state file. No-op if it doesn't exist."""
    try:
        STATE_PATH.unlink()
    except FileNotFoundError:
        pass


def require_active() -> dict:
    """
    Load state or print an error JSON to stdout and exit(1).

    Used by scripts that have no meaning without an active session
    (render_status, compile_plan, update_graph).
    """
    state = load_state()
    if state is None:
        sys.stdout.write(json.dumps({
            "error": "no_active_session",
            "message": (
                "No active Fathom Mode session. "
                "Use the /fathom command to start one."
            ),
        }))
        sys.exit(1)
    return state


# ---------------------------------------------------------------------------
# CLI subcommands:
#   `session_state.py check` — exit 0 if a REAL active session exists
#                              (state file present AND has session_id AND
#                              has non-empty task), 1 otherwise. Pending-
#                              task-flag stubs from Case 2 are NOT counted
#                              as real sessions — they're transient markers
#                              awaiting init_session.py.
#   `session_state.py path`  — print the canonical state file path to stdout,
#                              exit 0. Use this before reading the state file
#                              so callers don't have to guess between
#                              ${CLAUDE_PLUGIN_DATA} and ~/.fathom-mode/.
# Used by commands/fathom.md.
# ---------------------------------------------------------------------------


def _is_real_active_session(state: dict | None) -> bool:
    """A real active session has both a session_id and a non-empty task.
    Pending-task-flag-only stubs (Case 2 markers) don't qualify."""
    if state is None:
        return False
    return bool(state.get("session_id")) and bool(state.get("task"))


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "check":
        sys.exit(0 if _is_real_active_session(load_state()) else 1)
    if len(sys.argv) == 2 and sys.argv[1] == "path":
        sys.stdout.write(str(STATE_PATH))
        sys.exit(0)
    sys.stderr.write("usage: session_state.py {check|path}\n")
    sys.exit(2)

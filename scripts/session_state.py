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

    Prefers CLAUDE_PLUGIN_DATA (set by Claude Code when the plugin is loaded).
    Falls back to ~/.fathom-mode/ for standalone script runs (testing).
    """
    plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA")
    if plugin_data:
        return Path(plugin_data)
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
# CLI: `python session_state.py check` — exits 0 if active session, 1 otherwise.
# Used by commands/fathom.md to detect prior session before init_session.py.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "check":
        sys.exit(0 if STATE_PATH.exists() else 1)
    sys.stderr.write("usage: session_state.py check\n")
    sys.exit(2)

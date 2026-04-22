#!/usr/bin/env python3
"""
UserPromptSubmit hook for the Fathom Mode plugin.

Self-gates on the session state file at ${CLAUDE_PLUGIN_DATA}/active_session.json.
If absent, exits silently — the plugin is installed but no Fathom session is active,
so we must not pollute every Claude Code session in this project.

If a session is active, injects a short system reminder via additionalContext that
re-emphasizes the three-part turn rhythm and the current Score, so the model stays
oriented even if SKILL.md drifts out of attention. The reminder does NOT decide
in-session vs tangential — that judgment is the model's per the product vision
("intelligence over enforcement"). The reminder simply names both branches and lets
the model pick.

stdin payload from Claude Code is ignored — the state file is the source of truth.
The script writes JSON to stdout per the Claude Code hook protocol and always
exits 0 to avoid blocking the user prompt on hook errors.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _emit(reminder_text: str | None) -> None:
    """Print hook output JSON if there's a reminder; otherwise nothing."""
    if reminder_text is None:
        return
    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": reminder_text,
        }
    }
    sys.stdout.write(json.dumps(output))


def _build_reminder(state: dict) -> str:
    task = state.get("task", "(unknown task)")
    score_pct = state.get("score_pct", 0)
    turn = int(state.get("turn_count", 0))
    return (
        f"[Fathom Mode active — turn {turn + 1} — score {score_pct}%]\n"
        f"Current task: {task}\n"
        "Respond in the three-part format: short answer + insight + one targeted question. "
        "Before responding, call update_graph.py via Bash. After responding, append the Score block. "
        "If this message is clearly unrelated to the current task, answer directly and mark it "
        "tangential (do not update the graph)."
    )


def main() -> None:
    plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA")
    if not plugin_data:
        # Older Claude Code or env not propagated — fail open silently.
        sys.exit(0)

    state_path = Path(plugin_data) / "active_session.json"
    if not state_path.exists():
        # No active Fathom session — self-gate.
        sys.exit(0)

    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # Corrupted state file — fail open rather than block the user.
        sys.exit(0)

    _emit(_build_reminder(state))
    sys.exit(0)


if __name__ == "__main__":
    main()

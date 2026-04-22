#!/usr/bin/env python3
"""
UserPromptSubmit hook for the Fathom Mode plugin.

Three branches based on state file content:

  1. State file absent OR corrupted
     → no injection (hook self-gates; plugin is installed but no Fathom
       activity is in progress).

  2. State has pending_task_flag = "new" or "replace" (Fix X)
     → inject a "this user message IS the task" reminder telling Claude to
       run init_session.py (and exit_session.py first if "replace") before
       responding. Includes an explicit escape valve for the case where
       the user's message is clearly NOT a task description (e.g., idle
       question, clarification request); Claude may answer directly and
       re-issue the lock phrase, leaving the flag set until consumed or
       the user explicitly exits.

  3. State has a real active session (no pending flag)
     → inject the current Fathom-session reminder (three-part rhythm,
       call update_graph.py, append Score block, in-session vs tangential
       judgment is the model's per vision §3 "intelligence over enforcement").

stdin payload from Claude Code is ignored — the state file is the source
of truth. Always exits 0 to avoid blocking the user prompt on hook errors.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Cross-platform stdout — Windows default codecs can't encode em-dashes etc.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except (AttributeError, OSError):
    pass


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


def _build_active_session_reminder(state: dict) -> str:
    """Existing in-session reminder — no pending flag, real session active."""
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


def _build_pending_new_reminder() -> str:
    """Case 2 follow-up — user just entered Fathom Mode with no prior session."""
    return (
        "[Fathom Mode: pending first task]\n"
        "The user just entered Fathom Mode via empty `/fathom-mode:fathom` invocation, "
        "and the lock phrase asked them to send their task as their next message. "
        "**This message IS the task description.**\n"
        "\n"
        "Required actions BEFORE responding:\n"
        "1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init_session.py --task \"<the user's verbatim message>\"` via Bash\n"
        "2. Perform first-turn extraction per SKILL.md and call `update_graph.py --user-input ... --nodes '...'`\n"
        "3. Begin normal three-part response (short answer + insight + one targeted question) with Score block at the end\n"
        "\n"
        "Do NOT route to tangential. Do NOT skip init_session.py.\n"
        "\n"
        "Escape valve: if the message is clearly NOT a task description (e.g., an idle question like \"what's 2+2\", "
        "a clarification request, or a request to cancel), you MAY answer it directly and re-issue the lock phrase "
        "(\"Fathom Mode is ready. Send your task as your next message — I'll start the Fathom session with whatever "
        "you write next.\"). The pending flag stays set until a real task arrives or the user explicitly cancels via "
        "`/fathom-mode:fathom-exit`."
    )


def _build_pending_replace_reminder(state: dict) -> str:
    """Case 4 follow-up — user signaled task switching while a session was active."""
    old_task = state.get("task", "(unknown task)")
    old_score = state.get("score_pct", 0)
    old_turn = int(state.get("turn_count", 0))
    return (
        "[Fathom Mode: pending task replacement]\n"
        f"The user previously invoked empty `/fathom-mode:fathom` while a session was active "
        f"(old session on \"{old_task}\" — turn {old_turn} at {old_score}%), and the lock phrase "
        "told them their next message would replace the current session. **This message IS the new task description.**\n"
        "\n"
        "Required actions BEFORE responding:\n"
        "1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/exit_session.py` via Bash to clear the old session\n"
        "2. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init_session.py --task \"<the user's verbatim message>\"` via Bash\n"
        "3. Perform first-turn extraction per SKILL.md and call `update_graph.py --user-input ... --nodes '...'`\n"
        "4. Begin a new three-part response with Score block — this is the new session, not a continuation of the old\n"
        "\n"
        "Do NOT route to tangential. Do NOT try to continue the old session by appending to its nodes.\n"
        "\n"
        "Escape valve: if the message is clearly NOT a task description (e.g., an idle question, a clarification "
        "request, or a request to cancel), you MAY answer it directly and re-issue the lock phrase. The pending "
        "flag stays set until a real task arrives or the user explicitly cancels via `/fathom-mode:fathom-exit` "
        "(which would also clear the old session)."
    )


def _candidate_state_paths() -> list[Path]:
    """
    Path resolution must match scripts/session_state.py exactly, otherwise
    the hook and the scripts disagree on where state lives and the hook
    silently no-ops while a session is active.

    Per Anthropic docs, ${CLAUDE_PLUGIN_DATA} is exported only to hook
    subprocesses and MCP/LSP server subprocesses — NOT to the Bash-tool
    subprocesses that init_session.py / update_graph.py run inside. Those
    scripts therefore fall back to ~/.fathom-mode/. The hook gets the env
    var but must check both locations (env var first for forward-compat,
    fallback second to actually find what scripts wrote).
    """
    paths: list[Path] = []
    plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA")
    if plugin_data:
        paths.append(Path(plugin_data) / "active_session.json")
    paths.append(Path.home() / ".fathom-mode" / "active_session.json")
    return paths


def main() -> None:
    state_path: Path | None = None
    for candidate in _candidate_state_paths():
        if candidate.exists():
            state_path = candidate
            break

    if state_path is None:
        # No state file in any known location — self-gate.
        sys.exit(0)

    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # Corrupted state file — fail open rather than block the user.
        sys.exit(0)

    # Branch by pending flag (Fix X) before falling back to in-session reminder.
    flag = state.get("pending_task_flag")
    if flag == "new":
        _emit(_build_pending_new_reminder())
    elif flag == "replace":
        _emit(_build_pending_replace_reminder(state))
    elif state.get("session_id") and state.get("task"):
        # Real active session, no pending flag → existing in-session reminder.
        _emit(_build_active_session_reminder(state))
    else:
        # State file exists but no real session and no pending flag (degenerate
        # state, e.g., an exit_session that didn't fully clear). Self-gate.
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()

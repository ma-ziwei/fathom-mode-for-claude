#!/usr/bin/env python3
"""
UserPromptSubmit hook for the Fathom Mode plugin.

Four prompt-shape behaviors at the top level:

  1. Prompt is exactly `/fathom-mode:fathom` (no args)
     -> Hook overwrites the state file with a pending-new-task stub
        ("clean, atomic, leave-no-residue" semantics: prior session is
        wiped immediately). Then block + "Fathom Mode is ready." No LLM.
        The next plain user message will become the new task (Behavior 4).

  2. Prompt starts with `/fathom-mode:fathom ` (args present)
     -> Hook runs init_session.py --task "<args>" via subprocess (creates
        a fresh session, overwriting any prior state including pending
        stubs from Behavior 1) AND injects a session-init reminder telling
        the LLM what to do (first-turn extraction + three-part response).

  3. Prompt starts with `/fathom-mode:` (any other plugin slash command,
     incl. /fathom-mode:fathom-status / -compile / -exit)
     -> Skip injection, let the slash command's .md body drive behavior.

  4. Any other prompt (normal user message)
     a. State has pending_new_task flag
        -> This message IS the new task. Hook runs init_session.py --task
           "<this message>" via subprocess, then injects a fresh-session
           reminder. Mirrors Behavior 2 but triggered from a user message
           instead of a slash command.
     b. State has a real active session (session_id + task)
        -> Dispatch by FSM state into one of three reminders:
            - awaiting_approval=True -> AWAITING_APPROVAL reminder
              (do not call update_graph; judge user's response to the plan)
            - score_pct >= 50         -> PLAN_READY reminder
              (in-session three-part + Score block + plan hint + compile-
              intent recognition)
            - otherwise               -> IDLE reminder
              (in-session three-part + Score block, NO plan/compile content)
     c. Neither
        -> Self-gate (no injection — plugin installed but no Fathom
           activity in progress).

The score-threshold check for PLAN_READY lives in this Python dispatch,
NOT in Claude's reasoning. compile_plan.py mutates state.awaiting_approval
on invocation, so both conversational ("plan") and slash-command entry
paths converge on the same AWAITING_APPROVAL state.

Always exits 0 to avoid blocking the user prompt on hook errors.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Cross-platform stdout — Windows default codecs can't encode em-dashes etc.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except (AttributeError, OSError):
    pass


_FATHOM_ENTRY = "/fathom-mode:fathom"


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


# ---------------------------------------------------------------------------
# State machine reminder builders
#
# Three INDEPENDENT strings — not a shared template with conditional
# sections. Per Lawrence: Claude's context for the current state should
# contain only that state's reminder, nothing else.
#
# Wording principles:
#   - Deterministic rules use direct imperatives ("At top of response,
#     place..."). NO modal language ("consider", "if appropriate").
#   - Intent classification uses direct judgment language ("If the user
#     expresses approval of the plan: ..."). NO enumerated example words
#     — Opus understands abstract semantics directly, no list needed.
#   - Boundary counter-examples are KEPT where they narrow scope (e.g.,
#     "plan a meeting" is not a compile trigger).
#   - Vocabulary alignment with Claude Code: user-facing trigger words
#     are `plan` (compile entry) and `execute` (post-plan run).
# ---------------------------------------------------------------------------


def _build_idle_reminder(state: dict) -> str:
    """In-session reminder for IDLE state (active session, score < 50)."""
    score_pct = state.get("score_pct", 0)
    update_graph_path = (_scripts_dir() / "update_graph.py").as_posix()
    return (
        f"You are in an active Fathom session. Score: {score_pct}%.\n"
        "\n"
        "Format your response in three parts: a short answer to the user's "
        "message, one insight about their underlying intent, and one question "
        "that probes a dimension they have not yet covered.\n"
        "\n"
        "Before responding, call:\n"
        f'  python3 "{update_graph_path}" --user-input "<user\'s verbatim message>" '
        "--nodes '<your extracted nodes as JSON array>'\n"
        "\n"
        "At the top of your response, place the `score_block_str` field from "
        "update_graph.py's output JSON verbatim. Do not re-render the bar, do "
        "not modify symbols, do not add embellishment.\n"
        "\n"
        "(Refer to SKILL.md for --nodes JSON schema, dimension definitions, "
        "and extraction discipline.)"
    )


def _build_plan_ready_reminder(state: dict) -> str:
    """In-session reminder for PLAN_READY state (active session, score >= 50)."""
    score_pct = state.get("score_pct", 0)
    update_graph_path = (_scripts_dir() / "update_graph.py").as_posix()
    compile_plan_path = (_scripts_dir() / "compile_plan.py").as_posix()
    return (
        f"You are in an active Fathom session. Score: {score_pct}%.\n"
        "\n"
        "Format your response in three parts: a short answer to the user's "
        "message, one insight about their underlying intent, and one question "
        "that probes a dimension they have not yet covered.\n"
        "\n"
        "Before responding, call:\n"
        f'  python3 "{update_graph_path}" --user-input "<user\'s verbatim message>" '
        "--nodes '<your extracted nodes as JSON array>'\n"
        "\n"
        "At the top of your response, place the `score_block_str` field from "
        "update_graph.py's output JSON verbatim.\n"
        "\n"
        "At the end of your response, append verbatim:\n"
        "💡 Ready to plan? Reply **plan** to compile this into an action plan.\n"
        "\n"
        "If the user's message expresses intent to compile this session into a "
        "plan, do NOT call update_graph.py this turn. Instead:\n"
        f'  1. Call: python3 "{compile_plan_path}"\n'
        "  2. Read its stdout as the compiled intent markdown — do NOT show it "
        "to the user verbatim.\n"
        "  3. Draft a concrete action plan for the user's task, grounded in "
        "every section of the compiled intent. Do not introduce concerns "
        "absent from it.\n"
        '  4. End your plan with: "Reply **execute** to run the plan, or '
        'describe what to change."\n'
        "\n"
        'Note: phrases like "plan a meeting" describe the session\'s content, '
        "not a compile trigger — judge from context.\n"
        "\n"
        "(Refer to SKILL.md for --nodes JSON schema, dimension definitions, "
        "and extraction discipline.)"
    )


def _build_awaiting_approval_reminder(state: dict) -> str:
    """Reminder for AWAITING_APPROVAL state (compile_plan.py has been called)."""
    exit_session_path = (_scripts_dir() / "exit_session.py").as_posix()
    return (
        "You presented a compiled plan to the user last turn. They are now "
        "responding to it. Do NOT call update_graph.py this turn.\n"
        "\n"
        "Judge the user's message:\n"
        "\n"
        "- If the user expresses approval of the plan: execute the plan using "
        "Claude Code's normal tools (Edit, Write, Bash, etc.). After execution "
        f'completes, call: python3 "{exit_session_path}"\n'
        "\n"
        "- If the user describes changes to the plan: revise the plan inline, "
        "grounded in the same compiled intent. Present the revised plan and "
        'end with "Reply **execute** to run the plan, or describe what to '
        'change." You remain in the approval-waiting state.\n'
        "\n"
        "- If the user expresses intent to cancel: call: "
        f'python3 "{exit_session_path}"\n'
        "\n"
        "- If the user's message is unrelated to the plan: answer the question "
        'directly, then add: "Still awaiting your response on the plan — reply '
        "**execute** to run, describe what to change, or use "
        '/fathom-mode:fathom-exit to cancel."\n'
        "\n"
        "- If the message is ambiguous: ask one clarifying question about which "
        "of the above the user intends."
    )


def _build_active_session_reminder(state: dict) -> str:
    """Dispatch in-session reminder by FSM state."""
    if state.get("awaiting_approval", False):
        return _build_awaiting_approval_reminder(state)
    if int(state.get("score_pct", 0)) >= 50:
        return _build_plan_ready_reminder(state)
    return _build_idle_reminder(state)


def _build_session_init_reminder(task: str, *, source: str) -> str:
    """
    Injected after hook successfully ran init_session.py. The `source` arg
    distinguishes whether the trigger was an args-bearing slash command or
    a pending-stub consumption — affects only the framing line.
    """
    # Compute the absolute path here. Hook-injected `additionalContext` is
    # NOT processed by Claude Code's slash-command-body expansion machinery,
    # so `${CLAUDE_PLUGIN_ROOT}` would NOT be expanded — Bash would receive
    # the literal `${CLAUDE_PLUGIN_ROOT}/scripts/...`, expand it to empty
    # (env var isn't propagated to Bash-tool subprocesses on Windows), and
    # try to open `/scripts/update_graph.py` which git-bash mistranslates
    # into `C:\Program Files\Git\scripts\...` — "no such file" error.
    # Using as_posix() so backslash separators on Windows become forward
    # slashes that bash handles cleanly. Wrapping in double quotes covers
    # any whitespace in the install path.
    update_graph_path = (_scripts_dir() / "update_graph.py").as_posix()

    if source == "args":
        framing = (
            f'[Fathom Mode: new session initialized for task "{task}"]\n'
            "The UserPromptSubmit hook ran init_session.py for you when you saw "
            f"`/fathom-mode:fathom <task>`."
        )
    else:  # source == "pending"
        framing = (
            f'[Fathom Mode: pending-new-task consumed -> fresh session for "{task}"]\n'
            "The user previously typed bare /fathom-mode:fathom (which wiped any "
            "prior session and set a pending flag). This message IS the new task. "
            "The hook ran init_session.py for you."
        )
    return (
        framing + " The state file is fresh, any prior session has been overwritten, "
        "this is the first turn.\n"
        "\n"
        "Required BEFORE responding — call update_graph.py via Bash exactly like this "
        "(replace the example nodes JSON with your real extraction; the script auto-tracks "
        "turn count internally, do not pass turn-related flags):\n"
        "\n"
        f'  python3 "{update_graph_path}" \\\n'
        f'    --user-input "{task}" \\\n'
        f'    --nodes \'[{{"id":"n1","dimension":"what","node_type":"fact",'
        f'"content":"...","raw_quote":"...","confidence":0.9,"secondary_dimensions":[]}}]\'\n'
        "\n"
        "Use the absolute script path above verbatim — do NOT substitute "
        "`${CLAUDE_PLUGIN_ROOT}/scripts/update_graph.py`, that env var is not "
        "exported to Bash-tool subprocesses and bash will mis-resolve the empty path.\n"
        "\n"
        "**Valid flags are ONLY**: --user-input (required), --nodes (optional JSON array), "
        "--task-type (optional, one of: thinking|creation|execution|learning|general). "
        "Do NOT pass --turn, --turn-count, --session-id, or any other flag — the script "
        "silently ignores them as a defensive measure but they're not part of the contract.\n"
        "\n"
        "Response format (per SKILL.md three-part rhythm):\n"
        "- **At the very TOP**: print the `score_block_str` field from update_graph.py's "
        "JSON output VERBATIM. Do NOT re-render — the script renders the 2-line "
        "`Fathom Score\\n{bar} NN% (+N)` block already. No Surface/Depth/Bedrock rows, "
        "no Turn/dims row, no symbol substitution.\n"
        "- Blank line, then acknowledge entering Fathom Mode and restate the task "
        "in the user's own framing.\n"
        "- Provide your insight (one paragraph).\n"
        "- Ask exactly one targeted orientation question.\n"
        "\n"
        "Do NOT call init_session.py — already done by the hook.\n"
        "Do NOT treat this as a continuation of any prior session — the prior state has been "
        "overwritten by the hook. This is turn 1 of a brand-new session about the task above.\n"
        "Do NOT execute the user's task — you are in planning mode."
    )


def _state_path() -> Path:
    """
    Single canonical state file path. MUST match scripts/session_state.py.
    See session_state._state_dir() docstring for why we always use
    ~/.fathom-mode/ and ignore CLAUDE_PLUGIN_DATA.
    """
    return Path.home() / ".fathom-mode" / "active_session.json"


def _read_state() -> dict | None:
    """Return parsed state dict, or None if absent / corrupted."""
    path = _state_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _wipe_to_pending_stub() -> None:
    """
    Overwrite the state file with a pending-new-task stub. Old session
    data (if any) is discarded immediately — atomic wipe, no residual
    state. Atomic via temp file + replace so a crash mid-write can't
    leave a half-rewritten file.
    """
    state_path = _state_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({
        "pending_new_task": True,
        "pending_set_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2, ensure_ascii=False)
    tmp = state_path.with_suffix(".json.tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(state_path)


def _scripts_dir() -> Path:
    """Return the plugin's scripts/ directory (sibling of hooks/)."""
    return Path(__file__).resolve().parent.parent / "scripts"


def _try_run_init_session(task: str) -> bool:
    """
    Run init_session.py --task "<task>" via subprocess. Return True on success.

    On any failure (script missing, non-zero exit, exception) return False.
    Caller falls through to skip-injection so the .md body's defensive
    fallback (or the user re-trying) can attempt the init from another path.
    """
    init_script = _scripts_dir() / "init_session.py"
    if not init_script.exists():
        return False
    try:
        # Force UTF-8 decoding of the child's stdout/stderr — without this,
        # Windows defaults to GBK / cp1252 and the reader thread crashes on
        # the em-dashes / box-drawing characters init_session.py emits.
        # errors="replace" guards against any other oddities.
        result = subprocess.run(
            [sys.executable, str(init_script), "--task", task],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def main() -> None:
    # Read stdin payload to detect plugin slash commands.
    # IMPORTANT: read raw bytes from sys.stdin.buffer and decode as UTF-8
    # explicitly. sys.stdin.read() uses the OS default codec, which on
    # Windows is GBK / cp1252 — this mangles non-ASCII prompts (Chinese,
    # em-dashes, etc.) into surrogate-escaped garbage that then propagates
    # into the subprocess args + JSON writes downstream and crashes
    # init_session.py with a UnicodeEncodeError.
    try:
        payload_raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        payload = json.loads(payload_raw) if payload_raw else {}
    except (OSError, json.JSONDecodeError):
        payload = {}
    prompt_text = (payload.get("prompt") or "").strip()

    # Behavior 1: bare `/fathom-mode:fathom` -> wipe state to pending stub
    # + instant block + "Fathom Mode is ready." Old session is discarded
    # immediately; next plain user message becomes the new task.
    if prompt_text == _FATHOM_ENTRY:
        _wipe_to_pending_stub()
        sys.stdout.write(json.dumps({
            "decision": "block",
            "reason": "Fathom Mode is ready.",
        }))
        sys.exit(0)

    # Behavior 2: `/fathom-mode:fathom <task>` (args present) ->
    # hook runs init_session.py + injects reminder. Trailing space
    # distinguishes args from sibling commands like /fathom-mode:fathom-status.
    if prompt_text.startswith(_FATHOM_ENTRY + " "):
        task = prompt_text[len(_FATHOM_ENTRY) + 1:].strip()
        if task and _try_run_init_session(task):
            _emit(_build_session_init_reminder(task, source="args"))
        # Fall through to skip injection if task empty or init failed.
        sys.exit(0)

    # Behavior 3: other /fathom-mode:* slash commands -> skip injection.
    if prompt_text.startswith("/fathom-mode:"):
        sys.exit(0)

    # Behavior 4: normal user prompt -- depends on state.
    state = _read_state()

    # 4a: pending-new-task stub set by Behavior 1 -> this message IS the new task.
    if state and state.get("pending_new_task"):
        if prompt_text and _try_run_init_session(prompt_text):
            _emit(_build_session_init_reminder(prompt_text, source="pending"))
        # If empty prompt (defensive) or init failed: keep stub, no injection.
        sys.exit(0)

    # 4b: real active session -> dispatch by FSM state.
    if state and state.get("session_id") and state.get("task"):
        _emit(_build_active_session_reminder(state))

    # 4c: no state at all -> self-gate.
    sys.exit(0)


if __name__ == "__main__":
    main()

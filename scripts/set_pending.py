#!/usr/bin/env python3
"""
set_pending.py — mark the state file with a pending-task-flag for Fix X.

Used by commands/fathom.md Cases 2 and 4 to signal to the
inject_fathom_context.py hook that the user's next message is a task
description (not a normal in-session planning turn).

Flag semantics:
  "new"     — Case 2: user invoked /fathom-mode:fathom with no args and
              no prior session. Stub state file is created/extended with
              just the flag; init_session.py runs on the next-turn hook
              path with the user's message as the task.
  "replace" — Case 4: user invoked /fathom-mode:fathom with no args
              while a session was already active. Existing state file is
              extended with the flag; on the next turn, hook directs
              Claude to exit_session.py first then init_session.py with
              the new task.

After the flag is consumed (init_session.py writes fresh state), it is
naturally cleared because init_session.py constructs a fresh state dict
without any pending_* fields.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from session_state import load_state, save_state


def main() -> None:
    parser = argparse.ArgumentParser(description="Set the pending-task-flag in state.")
    parser.add_argument("--flag", required=True, choices=["new", "replace"],
                        help="'new' for Case 2 (no prior session), 'replace' for Case 4")
    args = parser.parse_args()

    state = load_state() or {}
    state["pending_task_flag"] = args.flag
    state["pending_set_at"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    sys.stdout.write(json.dumps({"status": "set", "flag": args.flag}))


if __name__ == "__main__":
    main()

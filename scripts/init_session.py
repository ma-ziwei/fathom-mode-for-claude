#!/usr/bin/env python3
"""
Initialize a new Fathom Mode session.

Called by /fathom <task>. Writes the session state file and returns JSON
with session_id, task, and the initial Fathom Score.

Day 1 stub: initial Score is a fake function of task string length.
Day 2 replaces with real first-turn extraction + the asymptotic-score formula
documented in the investigation report (section A.4).
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone

from session_state import save_state


def _initial_score_pct(task: str) -> int:
    """
    Day 1 stub: longer initial task descriptions imply more dimensions
    are pre-filled, so initial score is higher. Capped at 55%.
    """
    base = len(task.strip())
    score = min(55, max(20, base // 4))
    return score


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize a Fathom Mode session.")
    parser.add_argument("--task", required=True, help="The user's task description.")
    args = parser.parse_args()

    task = args.task.strip()
    if not task:
        sys.stdout.write(json.dumps({
            "error": "empty_task",
            "message": "A non-empty task description is required.",
        }))
        sys.exit(1)

    session_id = uuid.uuid4().hex[:12]
    initial_score = _initial_score_pct(task)
    now_iso = datetime.now(timezone.utc).isoformat()

    state = {
        "session_id": session_id,
        "task": task,
        "started_at": now_iso,
        "turn_count": 0,
        "score_pct": initial_score,
        "nodes": [],   # list of {id, dimension, content}
        "edges": [],   # list of {source, target, type}
        "dialogue": [],  # list of {role, content}
    }
    save_state(state)

    sys.stdout.write(json.dumps({
        "session_id": session_id,
        "task": task,
        "score_pct": initial_score,
        "score_delta": initial_score,
        "dimensions_active": [],
        "next_target_dimension": "why",
        "turn_count": 0,
        "graph_summary": "New session. No nodes yet — first user message will populate.",
    }))


if __name__ == "__main__":
    main()

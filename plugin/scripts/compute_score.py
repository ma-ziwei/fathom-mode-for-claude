#!/usr/bin/env python3
"""
Standalone score-readout utility.

Reads the active session state and returns just the current score as JSON.
Useful for hooks or future agents that want a quick score check without
re-rendering the full status markdown.

Day 1: returns score_pct from state verbatim.
Day 2+: may recompute from graph state if needed.
"""

from __future__ import annotations

import json
import sys

from session_state import require_active


def main() -> None:
    state = require_active()
    sys.stdout.write(json.dumps({
        "score_pct": int(state.get("score_pct", 0)),
        "turn_count": int(state.get("turn_count", 0)),
    }))


if __name__ == "__main__":
    main()

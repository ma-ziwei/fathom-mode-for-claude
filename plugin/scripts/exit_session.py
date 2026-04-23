#!/usr/bin/env python3
"""
Clear the active Fathom session state.

Idempotent — safe to call when no session is active. Always exits 0 unless
filesystem permissions prevent deletion.
"""

from __future__ import annotations

import json
import sys

from session_state import clear_state


def main() -> None:
    try:
        clear_state()
    except OSError as exc:
        sys.stdout.write(json.dumps({
            "status": "error",
            "message": f"Could not clear state file: {exc}",
        }))
        sys.exit(1)

    sys.stdout.write(json.dumps({"status": "exited"}))


if __name__ == "__main__":
    main()

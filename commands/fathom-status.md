---
description: Show the current Intent Graph and Fathom Score for the active session
allowed-tools: Bash
---

Show the current state of the active Fathom session.

Steps:

1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/render_status.py` via Bash. It returns a markdown-formatted summary of the graph and score.

2. Present the script's output verbatim — do not rewrite, summarize, or reorder. The user is asking to inspect the white-box state.

3. After the rendered status, remind the user briefly of next-step commands:
   - `/fathom-plan` — plan from the session
   - `/fathom-exit` — leave the session

If `render_status.py` exits with a non-zero status (e.g. no active session), present its error message verbatim and stop.

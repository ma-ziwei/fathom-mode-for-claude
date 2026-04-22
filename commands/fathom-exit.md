---
description: Exit Fathom Mode without compiling
allowed-tools: Bash
---

Exit the current Fathom Mode session without compiling.

Steps:

1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/exit_session.py` via Bash.

2. Acknowledge briefly: "Exited Fathom Mode. The session state has been cleared."

Do not produce a Score block, three-part response, or any planning content. After this command runs, normal Claude Code behavior resumes.

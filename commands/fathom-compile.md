---
description: Compile the current Fathom session into a structured plan for approval
allowed-tools: Bash
---

Compile the current Fathom Mode session into a plan.

Steps:

1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/compile_plan.py` via Bash. It returns the compiled plan as markdown — five sections per `references/compile-format.md`.

2. Present the plan verbatim with this clear frame on top: "Here's what I've fathomed from our conversation. Review carefully."

3. End with this exact line: "**Reply 'approve' to proceed with this plan, or describe what to change.**"

4. Wait for the user's response.
   - If they say "approve" (or equivalent), proceed to execute the plan.
   - If they describe changes, refine the plan inline (do not re-run the compile script for tweaks; treat the compiled plan as a draft to amend) and re-present, ending with the same approval prompt.

5. After execution (or after explicit user dismissal during refinement), run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/exit_session.py` to clear the session state.

> *Day 4 will replace step 4's "execute the plan" branch with a real handoff. For Day 1 the stub plan is placeholder content — acknowledging "executing the plan now…" is enough; the user understands this is the skeleton.*

---
description: Compile the current Fathom session into a structured intent and draft an action plan grounded in it.
allowed-tools: Bash
---

Run via Bash:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/compile_plan.py
```

Read its stdout as the compiled intent markdown — do NOT show this to the user verbatim. Draft a concrete action plan for the user's task, grounded in every section of the compiled intent. Do not introduce concerns absent from the intent. Honor every constraint listed.

Present the plan and end with:

> Reply **approve** to proceed with this plan, or describe what to change.

(From here the hook's AWAITING_APPROVAL reminder takes over and manages the approve / change / cancel flow on subsequent turns. This slash command exists for users who prefer an explicit slash entry to compile; the conversational "plan" trigger from the PLAN_READY hook reminder produces the same state transition via the same `compile_plan.py` invocation, since `compile_plan.py` itself sets `state.awaiting_approval = True` regardless of entry path.)

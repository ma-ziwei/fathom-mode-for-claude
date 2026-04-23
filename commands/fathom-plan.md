---
description: Plan from the current Fathom session, grounded in a structured intent.
allowed-tools: Bash
---

Run via Bash:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/compile_plan.py
```

Read its stdout as the structured intent markdown — do NOT show this to the user verbatim. Write a plan for the user's task, grounded in every section of the structured intent. Do not introduce concerns absent from the intent. Honor every constraint listed.

Present the plan and end with:

> Reply **approve** to proceed with this plan, **reject** to discard, or describe what to change.

(From here the hook's AWAITING_APPROVAL reminder takes over and manages the approve / reject / change flow on subsequent turns. This slash command exists for users who prefer an explicit slash entry; the conversational "plan" trigger from the IN_SESSION hook reminder produces the same state transition via the same `compile_plan.py` invocation, since `compile_plan.py` itself sets `state.awaiting_approval = True` regardless of entry path.)

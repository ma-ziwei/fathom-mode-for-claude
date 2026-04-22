#!/usr/bin/env python3
"""
compile_plan.py — Print the Structured Intent Summary for the active session.

Phase 1 reality: thin wrapper around _compiler.compile_intent_graph(state).
Output is markdown that Claude reads as planning input — NOT shown to user
verbatim. The /fathom-mode:fathom-compile command body explains the contract.

Phase 3 will rewrite _compiler internals (raw_quote grouping, CFP causal
filter, contradictions section). This wrapper stays unchanged across phases.
"""

from __future__ import annotations

import sys

from session_state import require_active
from _compiler import compile_intent_graph


def main() -> None:
    state = require_active()  # exits 1 with error JSON if no active session
    sys.stdout.write(compile_intent_graph(state))


if __name__ == "__main__":
    main()

"""
6W dimensional priority + next-target selector.

Concept ported from prior research (SSRN paper + MIT OSS at
github.com/ma-ziwei/fathom-mode). Boilerplate constants
(DEFAULT_DIM_PRIORITY) ported directly from ftg/dimensions.py.

Cut from ftg/dimensions.py (intentionally not ported):
  - DIMENSION_LABELS / DIMENSION_DESCRIPTIONS (used only by ftg's questioner
    prompts; SKILL.md carries our equivalent dimension definitions)
  - CROSS_DIM_RULES + infer_edges (algorithm-inferred edges; the compiler
    only renders USER_EXPLICIT causal, so inferred edges have nowhere to land)
"""

from __future__ import annotations

from _graph import IntentGraph
from _models import Dimension


# Universal dimension priority weights — direct port from ftg.
# Ordering: HOW > WHY > WHO > WHAT > WHEN > WHERE.
# Higher = the dimension matters more / should be covered first.
DEFAULT_DIM_PRIORITY: dict[str, float] = {
    "how": 6.0,
    "why": 5.0,
    "who": 4.0,
    "what": 3.0,
    "when": 2.0,
    "where": 1.0,
}


def find_target_dimension(
    graph: IntentGraph,
    waived_dimensions: set[str] | None = None,
    task_type: str = "general",
) -> str:
    """
    Pick the dimension with highest (priority_weight / (count + 1)) ratio.

    Intuition: a dim with high priority and low coverage rises to the top.
    Adding 1 to count avoids division by zero when a dim has no nodes yet.

    The `task_type` arg is currently unused — kept for signature
    compatibility with ftg's version (where task_type can override
    priorities). Reserved for future task-aware tweaks.

    Returns the dim name as a lowercase string ("who" / "what" / etc.).
    Defaults to "how" if every candidate is waived (degenerate).
    """
    waived = waived_dimensions or set()
    counts = graph.dimension_node_counts()

    best_score = -1.0
    target = "how"  # fallback if every candidate is waived
    for dim in [d.value for d in Dimension]:
        if dim in waived:
            continue
        priority = DEFAULT_DIM_PRIORITY.get(dim, 3.0)
        count = counts.get(dim, 0)
        score = priority / (count + 1)
        if score > best_score:
            best_score = score
            target = dim

    return target


# ---------------------------------------------------------------------------
# Self-test (run with: python _dimensions.py)
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    from _models import Node

    # Test 1 — empty graph → "how" (highest priority, count=0 for all)
    g = IntentGraph()
    assert find_target_dimension(g) == "how", (
        f"empty graph should target 'how', got {find_target_dimension(g)}"
    )

    # Test 2 — 1 HOW node: HOW=6/2=3.0, WHY=5/1=5.0 → "why"
    g.add_node(Node(id="n1", content="...", raw_quote="", dimension="how", node_type="fact"))
    assert find_target_dimension(g) == "why", (
        f"after 1 HOW, should target 'why', got {find_target_dimension(g)}"
    )

    # Test 3 — HOW + WHY: HOW=6/2=3.0, WHY=5/2=2.5, WHO=4/1=4.0 → "who"
    g.add_node(Node(id="n2", content="...", raw_quote="", dimension="why", node_type="fact"))
    assert find_target_dimension(g) == "who", (
        f"after HOW+WHY, should target 'who', got {find_target_dimension(g)}"
    )

    # Test 4 — waived dimensions skipped
    # Remaining (WHO/WHAT waived): HOW=6/2=3, WHY=5/2=2.5, WHEN=2/1=2, WHERE=1/1=1 → HOW
    target = find_target_dimension(g, waived_dimensions={"who", "what"})
    assert target == "how", f"with WHO+WHAT waived, expected 'how', got {target}"

    # Test 5 — fully populated, skewed: lots of HOW, no WHERE → "where"
    g2 = IntentGraph()
    for i in range(10):
        g2.add_node(Node(id=f"h{i}", content="...", raw_quote="", dimension="how", node_type="fact"))
    # HOW=6/11≈0.55, WHY=5/1=5.0 → "why"
    assert find_target_dimension(g2) == "why"
    # Add tons of WHY too — WHO has lowest count among DEPTH dims
    for i in range(10):
        g2.add_node(Node(id=f"y{i}", content="...", raw_quote="", dimension="why", node_type="fact"))
    # HOW=6/11≈0.55, WHY=5/11≈0.45, WHO=4/1=4.0, WHAT=3/1=3.0 → "who"
    assert find_target_dimension(g2) == "who"

    # Test 6 — empty waived set is no-op
    target = find_target_dimension(g, waived_dimensions=set())
    assert target == "who", f"empty waived should equal no-waived: got {target}"

    print("_dimensions.py self-test passed")

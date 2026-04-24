"""
Intent Graph — directed graph of nodes + edges with CFP downgrade.

Concept ported from prior research (SSRN paper + MIT OSS at
github.com/ma-ziwei/fathom-mode). The plugin uses pure-stdlib dict
storage (no NetworkX) to keep install footprint minimal. Repetitive
boilerplate (relation priority dict, edge strength comparator) is
faithful to ftg/graph.py.

Key invariant — Causal Fathom Protocol enforcement point: CAUSAL edges
MUST have source_type == USER_EXPLICIT. Any violation is auto-downgraded
to SUPPORTS at add_edge(). The algorithm never fabricates causal claims;
those come only from the user's own words.

Cut from ftg/graph.py (intentionally not ported):
  - NetworkX-backed connectivity_score, get_causal_chains, dimension_coverage
  - infer_edges + CROSS_DIM_RULES (algorithm-inferred SUPPORTS/DEPENDENCY)
  - DAG cycle check (we don't render dependency chains)
"""

from __future__ import annotations

from _models import (
    Dimension,
    Edge,
    EdgeSource,
    Node,
    RelationType,
)


# Strongest-edge-wins comparator — direct port from ftg/graph.py
RELATION_PRIORITY: dict[str, int] = {
    RelationType.CAUSAL.value: 5,
    RelationType.DEPENDENCY.value: 4,
    RelationType.CONTRADICTION.value: 3,
    RelationType.CONDITIONAL.value: 2,
    RelationType.SUPPORTS.value: 1,
}

SOURCE_PRIORITY: dict[str, int] = {
    EdgeSource.USER_EXPLICIT.value: 3,
    EdgeSource.USER_IMPLIED.value: 2,
    EdgeSource.ALGORITHM_INFERRED.value: 1,
}


def _edge_strength(edge: Edge) -> tuple[int, int]:
    return (
        RELATION_PRIORITY.get(edge.relation_type, 0),
        SOURCE_PRIORITY.get(edge.source_type, 0),
    )


class IntentGraph:
    """Directed graph of nodes + edges. Pure-dict storage."""

    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        # (source_id, target_id) -> Edge. Strongest-edge-wins per pair.
        self._edges: dict[tuple[str, str], Edge] = {}

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_node(self, node: Node) -> None:
        """Insert or replace a node by id."""
        self._nodes[node.id] = node

    def add_edge(self, edge: Edge) -> bool:
        """
        Add a directed edge. Return True if accepted, False if rejected.

        Rejection cases:
          - source or target node does not exist in graph
          - source == target (self-loop)
          - an existing edge for (source, target) has equal-or-stronger strength

        CFP enforcement: if relation_type == 'causal' and source_type !=
        'user_explicit', rewrite the edge to 'supports' before storing.
        """
        if edge.source not in self._nodes or edge.target not in self._nodes:
            return False
        if edge.source == edge.target:
            return False

        # Causal Fathom Protocol — algorithm cannot fabricate causal claims
        if (edge.relation_type == RelationType.CAUSAL.value
                and edge.source_type != EdgeSource.USER_EXPLICIT.value):
            edge = Edge(
                source=edge.source,
                target=edge.target,
                relation_type=RelationType.SUPPORTS.value,
                source_type=edge.source_type,
                weight=edge.weight,
            )

        pair = (edge.source, edge.target)
        existing = self._edges.get(pair)
        if existing is not None and _edge_strength(edge) <= _edge_strength(existing):
            return False

        self._edges[pair] = edge
        return True

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return len(self._edges)

    def get_node(self, node_id: str) -> Node | None:
        return self._nodes.get(node_id)

    def get_all_nodes(self) -> list[Node]:
        return list(self._nodes.values())

    def get_all_edges(self) -> list[Edge]:
        return list(self._edges.values())

    def get_nodes_by_type(self, node_type: str) -> list[Node]:
        """Filter by node_type string (e.g., 'constraint')."""
        return [n for n in self._nodes.values() if n.node_type == node_type]

    def get_nodes_by_dimension(self, dim: str) -> list[Node]:
        """Filter by primary dimension string (e.g., 'why')."""
        return [n for n in self._nodes.values() if n.dimension == dim]

    def dimension_node_counts(self) -> dict[str, int]:
        """Count nodes per dimension (primary only). All 6 dims always present (0 if empty)."""
        counts: dict[str, int] = {d.value: 0 for d in Dimension}
        for n in self._nodes.values():
            if n.dimension in counts:
                counts[n.dimension] += 1
        return counts

    def has_contradictions(self) -> list[tuple[str, str]]:
        """Return (source_id, target_id) for every CONTRADICTION edge."""
        return [
            (e.source, e.target)
            for e in self._edges.values()
            if e.relation_type == RelationType.CONTRADICTION.value
        ]

    # ------------------------------------------------------------------
    # Serialization (round-trips through state file JSON)
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges.values()],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IntentGraph":
        graph = cls()
        for nd in data.get("nodes", []):
            graph.add_node(Node.from_dict(nd))
        for ed in data.get("edges", []):
            graph.add_edge(Edge.from_dict(ed))
        return graph


# ---------------------------------------------------------------------------
# Self-test (run with: python _graph.py)
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    g = IntentGraph()
    g.add_node(Node(id="a", content="cause", raw_quote="", dimension="why", node_type="belief"))
    g.add_node(Node(id="b", content="effect", raw_quote="", dimension="what", node_type="fact"))

    # Test 1 — CFP downgrade: algorithm-inferred CAUSAL → SUPPORTS
    accepted = g.add_edge(Edge(
        source="a", target="b",
        relation_type=RelationType.CAUSAL.value,
        source_type=EdgeSource.ALGORITHM_INFERRED.value,
    ))
    assert accepted, "edge should be accepted (then downgraded)"
    edges = g.get_all_edges()
    assert len(edges) == 1
    assert edges[0].relation_type == RelationType.SUPPORTS.value, (
        f"CFP downgrade failed: relation_type={edges[0].relation_type}"
    )

    # Test 2 — USER_EXPLICIT CAUSAL preserved (replaces weaker supports)
    accepted = g.add_edge(Edge(
        source="a", target="b",
        relation_type=RelationType.CAUSAL.value,
        source_type=EdgeSource.USER_EXPLICIT.value,
    ))
    assert accepted, "user-explicit causal should replace weaker supports"
    edges = g.get_all_edges()
    assert any(e.relation_type == RelationType.CAUSAL.value for e in edges), (
        "USER_EXPLICIT CAUSAL should be preserved (not downgraded)"
    )

    # Test 3 — USER_IMPLIED CAUSAL also gets downgraded (only USER_EXPLICIT survives)
    g.add_node(Node(id="x", content="x", raw_quote="", dimension="who", node_type="fact"))
    g.add_node(Node(id="y", content="y", raw_quote="", dimension="how", node_type="fact"))
    g.add_edge(Edge(
        source="x", target="y",
        relation_type=RelationType.CAUSAL.value,
        source_type=EdgeSource.USER_IMPLIED.value,
    ))
    xy_edge = g._edges[("x", "y")]
    assert xy_edge.relation_type == RelationType.SUPPORTS.value, (
        "USER_IMPLIED CAUSAL must also downgrade"
    )

    # Test 4 — self-loop rejected
    assert not g.add_edge(Edge(
        source="a", target="a",
        relation_type=RelationType.SUPPORTS.value,
        source_type=EdgeSource.USER_EXPLICIT.value,
    ))

    # Test 5 — missing target node rejected
    assert not g.add_edge(Edge(
        source="a", target="z",
        relation_type=RelationType.SUPPORTS.value,
        source_type=EdgeSource.USER_EXPLICIT.value,
    ))

    # Test 6 — weaker edge rejected (existing CAUSAL is already strongest)
    rejected_weaker = g.add_edge(Edge(
        source="a", target="b",
        relation_type=RelationType.SUPPORTS.value,
        source_type=EdgeSource.ALGORITHM_INFERRED.value,
    ))
    assert not rejected_weaker, "weaker edge should not replace existing CAUSAL"

    # Test 7 — dimension_node_counts includes all 6 dims
    counts = g.dimension_node_counts()
    assert counts["why"] == 1
    assert counts["what"] == 1
    assert counts["who"] == 1
    assert counts["how"] == 1
    assert counts["when"] == 0
    assert counts["where"] == 0
    assert set(counts.keys()) == {"who", "what", "why", "when", "where", "how"}

    # Test 8 — get_nodes_by_type
    beliefs = g.get_nodes_by_type("belief")
    assert len(beliefs) == 1 and beliefs[0].id == "a"
    facts = g.get_nodes_by_type("fact")
    assert len(facts) == 3  # b, x, y

    # Test 9 — get_nodes_by_dimension
    whats = g.get_nodes_by_dimension("what")
    assert len(whats) == 1 and whats[0].id == "b"

    # Test 10 — has_contradictions
    g.add_node(Node(id="c", content="claim1", raw_quote="", dimension="what", node_type="fact"))
    g.add_node(Node(id="d", content="claim2", raw_quote="", dimension="what", node_type="fact"))
    g.add_edge(Edge(
        source="c", target="d",
        relation_type=RelationType.CONTRADICTION.value,
        source_type=EdgeSource.USER_EXPLICIT.value,
    ))
    contras = g.has_contradictions()
    assert ("c", "d") in contras

    # Test 11 — to_dict / from_dict round-trip
    data = g.to_dict()
    g2 = IntentGraph.from_dict(data)
    assert g2.node_count() == g.node_count()
    assert g2.edge_count() == g.edge_count()
    # Verify the contradiction survived round-trip
    assert ("c", "d") in g2.has_contradictions()

    print("_graph.py self-test passed")
    print(f"  nodes: {g.node_count()}, edges: {g.edge_count()}")
    print(f"  dim counts: {g.dimension_node_counts()}")

"""
Causal marker detection — extracts user-stated causal relationships
from natural-language text and maps them to graph nodes as
USER_EXPLICIT CAUSAL edges (per CFP, only the user's own causal
language counts).

Concept ported from prior research (SSRN paper + MIT OSS at
github.com/ma-ziwei/fathom-mode). Marker lists, fragment cleaner,
overlap-score function, and threshold (0.3) ported directly from
ftg/causal.py — boilerplate constants where direct fidelity matters.

Cut from ftg/causal.py (intentionally not ported):
  - CausalTracker (embedding-based hypothesis verification)
  - EmbeddingCache, cosine_similarity, _compute_ambiguity
  - process_causal_feedback (multi-round verification loop)
  - deep_causal_verification (LLM-judge with quote attestation)
  - is_worth_verifying / TRIVIAL_PAIRS / HIGH_VALUE_PAIRS

The MVP ships marker detection + node matching only. Verified
hypotheses and embedding-based ambiguity detection wait for a later
phase.
"""

from __future__ import annotations

from _models import Edge, EdgeSource, Node, RelationType


# Marker lists — direct port from ftg/causal.py (boilerplate constants)
FORWARD_MARKERS: list[str] = [
    "therefore", "causes", "leads to", "results in",
    "which means", "consequently",
]
BACKWARD_MARKERS: list[str] = [
    "because", "due to", "as a result of",
    "caused by", "owing to",
]
PURPOSE_MARKERS: list[str] = [
    "in order to", "so that", "for the purpose of",
    "intended for", "to be used as", "used for",
]


def detect_causal_markers(text: str) -> list[dict]:
    """
    Scan text for causal/purpose markers; return structured detections.

    Each detection dict: {type, marker, cause, effect}
      type: 'forward' | 'backward' | 'purpose'
      Forward markers ('therefore', 'causes', ...): cause MARKER effect
      Backward markers ('because', 'due to', ...): effect MARKER cause
      Purpose markers ('in order to', 'so that', ...): action MARKER goal
        — purpose is intentionality, NEVER promoted to CAUSAL per CFP.

    Strategy (faithful to ftg):
      1. Try forward markers; if any match, skip backward (avoid double-detect)
      2. If no forward match, try backward
      3. Always scan for purpose markers separately
      4. Deduplicate forward/backward detections by (cause, effect) lower
    """
    if not text:
        return []
    lower = text.lower()
    detections: list[dict] = []
    seen_pairs: set[tuple[str, str]] = set()

    # Forward markers: cause MARKER effect
    forward_found = False
    for marker in FORWARD_MARKERS:
        if marker in lower:
            idx = lower.index(marker)
            cause = _clean_fragment(text[:idx])
            effect = _clean_fragment(text[idx + len(marker):])
            if cause and effect:
                key = (cause.lower(), effect.lower())
                if key not in seen_pairs:
                    seen_pairs.add(key)
                    detections.append({
                        "type": "forward",
                        "marker": marker.strip(),
                        "cause": cause,
                        "effect": effect,
                    })
                    forward_found = True

    # Backward markers: effect MARKER cause (skipped if forward already found)
    if not forward_found:
        for marker in BACKWARD_MARKERS:
            if marker in lower:
                idx = lower.index(marker)
                effect = _clean_fragment(text[:idx])
                cause = _clean_fragment(text[idx + len(marker):])
                if cause and effect:
                    key = (cause.lower(), effect.lower())
                    if key not in seen_pairs:
                        seen_pairs.add(key)
                        detections.append({
                            "type": "backward",
                            "marker": marker.strip(),
                            "cause": cause,
                            "effect": effect,
                        })

    # Purpose markers: action MARKER goal — collected separately, never causal
    for marker in PURPOSE_MARKERS:
        if marker in lower:
            idx = lower.index(marker)
            action = _clean_fragment(text[:idx])
            goal = _clean_fragment(text[idx + len(marker):])
            if goal:
                detections.append({
                    "type": "purpose",
                    "marker": marker.strip(),
                    "action": action if action else "(implicit action)",
                    "goal": goal,
                })

    return detections


def _clean_fragment(text: str) -> str:
    """Trim punctuation and connectors from a clause fragment (port from ftg)."""
    text = text.strip()
    for prefix in [",", ".", ";", ":", "and ", "then "]:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
    for suffix in [",", ".", ";", ":"]:
        if text.endswith(suffix):
            text = text[:-len(suffix)].strip()
    return text


def _overlap_score(query: str, content: str, raw: str) -> float:
    """
    Score how well a marker fragment overlaps with a node's text.

    Direct port from ftg's _overlap_score. Strategy:
      - substring win (query inside content/raw): 1.0
      - reverse substring (content/raw inside query): 0.8
      - else: word-set intersection / query word count
    Range [0.0, 1.0].
    """
    if not query:
        return 0.0
    q_lower = query.lower()
    c_lower = content.lower()
    r_lower = raw.lower() if raw else ""
    if q_lower in c_lower or (r_lower and q_lower in r_lower):
        return 1.0
    if c_lower in q_lower or (r_lower and r_lower in q_lower):
        return 0.8
    query_words = set(q_lower.split())
    content_words = set(c_lower.split()) | set(r_lower.split())
    if not query_words:
        return 0.0
    return len(query_words & content_words) / max(len(query_words), 1)


def match_markers_to_nodes(
    detections: list[dict],
    existing_nodes: list[Node],
    min_overlap: float = 0.3,
) -> list[Edge]:
    """
    Map causal detections to graph nodes; produce USER_EXPLICIT CAUSAL edges.

    Only forward and backward detections create edges. Purpose detections
    are filtered out here — caller is responsible for logging them
    separately (they stay out of the graph per CFP).

    For each detection, find the best-matching node for cause + effect
    via _overlap_score over (content, raw_quote). If both sides clear
    min_overlap and refer to different nodes, emit a USER_EXPLICIT
    CAUSAL edge.
    """
    edges: list[Edge] = []
    for det in detections:
        if det["type"] == "purpose":
            continue
        cause_text = det["cause"]
        effect_text = det["effect"]

        best_cause: Node | None = None
        best_effect: Node | None = None
        best_cause_score = 0.0
        best_effect_score = 0.0

        for node in existing_nodes:
            cs = _overlap_score(cause_text, node.content, node.raw_quote)
            es = _overlap_score(effect_text, node.content, node.raw_quote)
            if cs > best_cause_score:
                best_cause_score = cs
                best_cause = node
            if es > best_effect_score:
                best_effect_score = es
                best_effect = node

        if (best_cause is not None
                and best_effect is not None
                and best_cause.id != best_effect.id
                and best_cause_score >= min_overlap
                and best_effect_score >= min_overlap):
            edges.append(Edge(
                source=best_cause.id,
                target=best_effect.id,
                relation_type=RelationType.CAUSAL.value,
                source_type=EdgeSource.USER_EXPLICIT.value,
                weight=1.0,
            ))

    return edges


# ---------------------------------------------------------------------------
# Self-test (run with: python _causal.py)
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    # Test 1 — backward marker
    det = detect_causal_markers("I skipped breakfast because I overslept")
    assert len(det) == 1, f"expected 1 detection, got {len(det)}: {det}"
    assert det[0]["type"] == "backward", f"expected backward, got {det[0]['type']}"
    assert det[0]["cause"] == "I overslept", f"cause wrong: {det[0]['cause']!r}"
    assert det[0]["effect"] == "I skipped breakfast", f"effect wrong: {det[0]['effect']!r}"

    # Test 2 — forward marker
    det = detect_causal_markers("Rising rates therefore mortgage costs climb")
    assert any(d["type"] == "forward" for d in det), f"no forward in {det}"
    fwd = next(d for d in det if d["type"] == "forward")
    assert "rising rates" in fwd["cause"].lower()
    assert "mortgage" in fwd["effect"].lower()

    # Test 3 — purpose marker (NOT causal)
    det = detect_causal_markers("I'm saving money in order to buy a house")
    purposes = [d for d in det if d["type"] == "purpose"]
    assert len(purposes) == 1, f"expected 1 purpose, got {purposes}"
    assert "buy a house" in purposes[0]["goal"].lower()
    causals = [d for d in det if d["type"] in ("forward", "backward")]
    assert len(causals) == 0, f"purpose should not produce causal, got: {causals}"

    # Test 4 — forward + purpose combined (use a marker actually in the list:
    # "causes" plural matches; "cause" singular wouldn't because the marker
    # list ports ftg's exact tokens — boilerplate fidelity)
    det = detect_causal_markers(
        "Higher inflation causes mortgage costs to climb, in order to curb spending"
    )
    types = [d["type"] for d in det]
    assert "forward" in types, f"expected forward in {types}"
    assert "purpose" in types, f"expected purpose in {types}"

    # Test 5 — empty / no markers
    assert detect_causal_markers("") == []
    assert detect_causal_markers("just plain prose with nothing relevant") == []

    # Test 6 — match_markers_to_nodes excludes purpose, requires overlap
    nodes = [
        Node(id="n1", content="overslept this morning", raw_quote="I overslept",
             dimension="why", node_type="fact"),
        Node(id="n2", content="skipped breakfast today", raw_quote="I skipped breakfast",
             dimension="what", node_type="fact"),
        Node(id="n3", content="bought a house", raw_quote="buy a house",
             dimension="what", node_type="goal"),
    ]
    det = detect_causal_markers(
        "I skipped breakfast because I overslept; saving in order to buy a house"
    )
    edges = match_markers_to_nodes(det, nodes)
    assert len(edges) == 1, f"expected 1 edge (purpose excluded), got {len(edges)}: {edges}"
    e = edges[0]
    assert e.source == "n1" and e.target == "n2", (
        f"edge endpoints wrong: {e.source} -> {e.target}"
    )
    assert e.relation_type == RelationType.CAUSAL.value
    assert e.source_type == EdgeSource.USER_EXPLICIT.value

    # Test 7 — overlap below threshold produces no edge
    nodes_bad = [
        Node(id="n1", content="completely unrelated topic", raw_quote="",
             dimension="who", node_type="fact"),
        Node(id="n2", content="another disjoint matter", raw_quote="",
             dimension="who", node_type="fact"),
    ]
    edges = match_markers_to_nodes(
        detect_causal_markers("X happens because Y triggers"),
        nodes_bad,
    )
    assert edges == [], f"low overlap should produce no edges, got: {edges}"

    print("_causal.py self-test passed")

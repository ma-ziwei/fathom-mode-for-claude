"""
Data models for the Fathom Mode plugin — enums + dataclasses.

Concept inspired by prior research (SSRN paper + prior library); no code copied.
Used by _scoring.py, _graph.py, _compiler.py and the script entry points
(init_session, update_graph) for state-file round-trip.

String-valued enums (`str, Enum`) make JSON serialization trivial:
`json.dumps(asdict(node))` works directly without custom encoders.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Dimension(str, Enum):
    """The 6W dimensional coordinate system."""

    WHO = "who"
    WHAT = "what"
    WHY = "why"
    WHEN = "when"
    WHERE = "where"
    HOW = "how"


class NodeType(str, Enum):
    """Semantic sub-type of an information node."""

    FACT = "fact"
    BELIEF = "belief"
    VALUE = "value"
    INTENT = "intent"
    CONSTRAINT = "constraint"
    EMOTION = "emotion"
    ASSUMPTION = "assumption"
    GOAL = "goal"


class RelationType(str, Enum):
    """Semantic type of an edge between nodes."""

    CAUSAL = "causal"
    DEPENDENCY = "dependency"
    CONTRADICTION = "contradiction"
    CONDITIONAL = "conditional"
    SUPPORTS = "supports"


class EdgeSource(str, Enum):
    """Provenance of an edge — how the relationship was established."""

    USER_EXPLICIT = "user_explicit"      # User explicitly stated the relationship
    USER_IMPLIED = "user_implied"        # LLM inferred from user's language
    ALGORITHM_INFERRED = "algorithm_inferred"  # Pure algorithmic inference (never CAUSAL)


# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------


@dataclass
class Node:
    """A single information node in the Intent Graph."""

    id: str
    content: str
    raw_quote: str
    dimension: str            # Dimension value
    node_type: str            # NodeType value
    confidence: float = 0.8

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Node":
        return cls(
            id=d["id"],
            content=d["content"],
            raw_quote=d.get("raw_quote", ""),
            dimension=d["dimension"],
            node_type=d.get("node_type", "fact"),
            confidence=d.get("confidence", 0.8),
        )


@dataclass
class Edge:
    """A directed relationship between two nodes."""

    source: str               # Node id
    target: str               # Node id
    relation_type: str        # RelationType value
    source_type: str          # EdgeSource value
    weight: float = 1.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Edge":
        return cls(
            source=d["source"],
            target=d["target"],
            relation_type=d["relation_type"],
            source_type=d["source_type"],
            weight=d.get("weight", 1.0),
        )

"""
Fathom Score — original algorithm faithfully ported from prior research.

Concept inspired by prior research (SSRN paper + prior library); no code copied.

The displayed Fathom Score is an asymptotic saturating function of three masses:
    fathom_score = 1 - exp(-DISPLAY_SCALE * latent_depth)
    latent_depth = utility_mass + grounding_mass + entropy_regularizer

Each mass is computed deterministically from the Intent Graph state:
  - utility_mass:   per-dim sum of base weights with rank-novelty 1/sqrt(1+i),
                    weighted heavier for DEPTH dims (why/who/how) than SURFACE
                    dims (what/when/where).
  - grounding_mass: sum over verified causal pairs (PARTIAL=2.8, VERIFIED=3.4).
                    Empty Day 2 (CFP detection lands Day 4).
  - entropy_reg:    0.15 * normalized Shannon entropy across credited mass per
                    dim. Rewards spreading nodes across multiple dims.

Three diagnostic sub-scores are also exposed (Surface / Depth / Bedrock):
each is its own 1 - exp(-k*x) saturating curve over the relevant mass.

The curve shape is monotonically non-decreasing and asymptotic to 1.0 (never
reaches it) — perfect understanding is a lie.

Run this file directly to self-verify: `python _scoring.py`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Constants (faithful port — Lawrence's designed signature, do not approximate)
# ---------------------------------------------------------------------------

SURFACE_DIMENSIONS = {"what", "when", "where"}
DEPTH_DIMENSIONS = {"why", "who", "how"}

SURFACE_WEIGHT = 1.0
DEPTH_WEIGHT = 1.9

PARTIAL_CAUSAL_WEIGHT = 2.8
VERIFIED_CAUSAL_WEIGHT = 3.4

ENTROPY_REGULARIZER_WEIGHT = 0.15
DISPLAY_SCALE = 0.10
DEPTH_PENETRATION_SCALE = 0.30
BEDROCK_SCALE = 1.0


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class BreakdownResult:
    """Full Score breakdown — top fathom_score is what's displayed; others diagnostic."""

    fathom_score: float          # 0.0-1.0; displayed * 100 as percent
    surface_coverage: float      # 0.0-1.0; entropy across active dims
    depth_penetration: float     # 0.0-1.0; saturating over utility_mass
    bedrock_grounding: float     # 0.0-1.0; saturating over grounding_mass
    utility_mass: float
    grounding_mass: float
    entropy_regularizer: float


# ---------------------------------------------------------------------------
# Main computation
# ---------------------------------------------------------------------------


def compute_fathom_breakdown(nodes, verified_causal_pairs=None):
    """
    Compute the full Fathom Score breakdown for a list of nodes.

    Args:
        nodes: list of objects with a `.dimension` attribute (e.g. Node from _models).
        verified_causal_pairs: optional dict {(src_id, tgt_id): "partial"|"verified"}.
            Day 2 always passes empty {}; Day 4 wires real causal edges.

    Returns:
        BreakdownResult with fathom_score in [0.0, 1.0).
    """
    verified_causal_pairs = verified_causal_pairs or {}

    # --- utility_mass: rank-based novelty per dimension ---
    by_dim = {}
    for node in nodes:
        dim = node.dimension
        base = DEPTH_WEIGHT if dim in DEPTH_DIMENSIONS else SURFACE_WEIGHT
        by_dim.setdefault(dim, []).append(base)

    utility_mass = 0.0
    credited = {}  # dim -> total credited mass for that dim
    for dim, weights in by_dim.items():
        weights.sort(reverse=True)
        dim_total = 0.0
        for i, w in enumerate(weights):
            contrib = w * (1.0 / math.sqrt(1 + i))
            utility_mass += contrib
            dim_total += contrib
        credited[dim] = dim_total

    # --- entropy_regularizer: Shannon-normalized coverage across dims ---
    total_credited = sum(credited.values())
    if total_credited > 0 and len(credited) > 1:
        ent = -sum(
            (m / total_credited) * math.log(m / total_credited)
            for m in credited.values()
            if m > 0
        )
        ent_norm = ent / math.log(len(credited))
    else:
        ent_norm = 1.0 if total_credited > 0 else 0.0
    entropy_reg = ENTROPY_REGULARIZER_WEIGHT * ent_norm

    # --- grounding_mass: verified causal edges ---
    grounding_mass = 0.0
    for _pair, kind in verified_causal_pairs.items():
        weight = VERIFIED_CAUSAL_WEIGHT if kind == "verified" else PARTIAL_CAUSAL_WEIGHT
        grounding_mass += weight

    # --- combine to latent_depth and saturating scores ---
    latent_depth = utility_mass + grounding_mass + entropy_reg

    fathom_score = (
        1.0 - math.exp(-DISPLAY_SCALE * latent_depth) if latent_depth > 0 else 0.0
    )
    depth_penetration = (
        1.0 - math.exp(-DEPTH_PENETRATION_SCALE * utility_mass)
        if utility_mass > 0
        else 0.0
    )
    bedrock_grounding = (
        1.0 - math.exp(-BEDROCK_SCALE * grounding_mass) if grounding_mass > 0 else 0.0
    )
    surface_coverage = ent_norm  # already 0-1

    return BreakdownResult(
        fathom_score=fathom_score,
        surface_coverage=surface_coverage,
        depth_penetration=depth_penetration,
        bedrock_grounding=bedrock_grounding,
        utility_mass=utility_mass,
        grounding_mass=grounding_mass,
        entropy_regularizer=entropy_reg,
    )


# ---------------------------------------------------------------------------
# Self-test (run with: python _scoring.py)
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    class _FakeNode:
        def __init__(self, dim):
            self.dimension = dim

    # 1. Empty input → score 0.0
    r = compute_fathom_breakdown([], {})
    assert r.fathom_score == 0.0, f"empty should be 0, got {r.fathom_score}"

    # 2. 1 SURFACE-dim node → small score
    r = compute_fathom_breakdown([_FakeNode("what")], {})
    assert 0 < r.fathom_score < 0.15, (
        f"1 what node should land ~10%, got {r.fathom_score:.4f}"
    )

    # 3. 6-dim first turn → ~0.55-0.60 (Lawrence's expected: ~0.585-0.591)
    nodes_6 = [
        _FakeNode("what"),
        _FakeNode("when"),
        _FakeNode("where"),
        _FakeNode("why"),
        _FakeNode("who"),
        _FakeNode("how"),
    ]
    r6 = compute_fathom_breakdown(nodes_6, {})
    assert 0.55 < r6.fathom_score < 0.60, (
        f"6-dim first turn should be 0.55-0.60, got {r6.fathom_score:.4f}"
    )

    # 4. Monotonicity: adding a node never decreases score
    r_extra = compute_fathom_breakdown(nodes_6 + [_FakeNode("why")], {})
    assert r_extra.fathom_score >= r6.fathom_score, (
        f"score must be monotonically non-decreasing: "
        f"6-dim={r6.fathom_score:.4f} vs +1why={r_extra.fathom_score:.4f}"
    )

    # 5. Asymptotic: very large input < 1.0
    big = [_FakeNode(d) for d in ("who", "what", "why", "when", "where", "how")] * 50
    r_big = compute_fathom_breakdown(big, {})
    assert r_big.fathom_score < 1.0, (
        f"score must asymptote below 1.0, got {r_big.fathom_score}"
    )

    # 6. Verified causal pairs add grounding mass
    r_with_causal = compute_fathom_breakdown(
        nodes_6, {("a", "b"): "verified", ("c", "d"): "partial"}
    )
    assert r_with_causal.fathom_score > r6.fathom_score, (
        "verified causal should bump score"
    )
    assert r_with_causal.bedrock_grounding > 0, "bedrock should reflect grounding mass"

    print("All sanity checks passed.")
    print(f"  6-dim first turn fathom_score  = {r6.fathom_score:.4f}")
    print(f"  6-dim surface_coverage         = {r6.surface_coverage:.4f}")
    print(f"  6-dim depth_penetration        = {r6.depth_penetration:.4f}")
    print(f"  6-dim bedrock_grounding        = {r6.bedrock_grounding:.4f}")
    print(f"  asymptote (300 nodes)          = {r_big.fathom_score:.4f} < 1.0")

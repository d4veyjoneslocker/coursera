"""
Narrative classification for shown explanation-tree nodes.

Rather than enumerate every (driver_type x surfaced_by x sign x relationship x
standout) combination, classification is COMPOSITIONAL: four independent
sub-decisions, each keyed off one or two fields, that the template layer
assembles into a sentence.

    frame     - what kind of thing this is        (driver_type)
    valence   - direction, with or against tide   (sign + relationship)
    health    - the stage-specific diagnostic     (stage metric, tunable)
    emphasis  - point a finger or describe spread (is_standout + surfaced_by)

A short list of OVERRIDES then adjusts the struct for a few special stories
composition can't capture on its own.

classify_node(node) -> dict  (the struct the template layer consumes)
"""

from dataclasses import dataclass, field
from backend.insights.business_narrative.select_tree_branches import make_surface_decision


@dataclass
class NarrativeNode:
    node_type: str
    driver_type: str | None
    scope: dict
    impact: float | None

    surfaced_by: str

    classification: dict

    headline: str
    detail: str | None

    children: list["NarrativeNode"] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Health thresholds (tunable)
# ---------------------------------------------------------------------------

# mature: rate_change is a fraction, e.g. -0.20 = VPO down 20%
MATURE_WEAKENING_THRESHOLD = -0.10
MATURE_SOFTENING_THRESHOLD = -0.03
MATURE_STRENGTHENING_THRESHOLD = 0.10

# ramping: reorder_breadth is 0..1, share of launch placements that reordered
RAMPING_WEAK_REORDER_THRESHOLD = 0.30
RAMPING_STRONG_REORDER_THRESHOLD = 0.70


# ---------------------------------------------------------------------------
# Dimension 1 — frame (driver_type)
# ---------------------------------------------------------------------------

def frame_of(driver_type):
    return {
        "new": "new_distribution",
        "ramping": "recent_launch",
        "mature": "established",
    }.get(driver_type, "unknown")


# ---------------------------------------------------------------------------
# Dimension 2 — valence (sign + relationship)
# ---------------------------------------------------------------------------

def valence_of(impact, relationship):
    if impact is None:
        return "neutral"

    positive = impact >= 0

    if relationship == "counterforce":
        # counteracting the parent movement
        return "bright_spot" if positive else "drag"

    # supporting the parent movement
    return "contributing" if positive else "declining"


# ---------------------------------------------------------------------------
# Dimension 3 — health (stage-specific diagnostic)
# ---------------------------------------------------------------------------

def health_of(node):
    if node.driver_type == "mature":
        rate_change = getattr(node, "rate_change", None)

        if rate_change is None:
            return None

        if rate_change <= MATURE_WEAKENING_THRESHOLD:
            return "weakening"

        if rate_change <= MATURE_SOFTENING_THRESHOLD:
            return "softening"

        if rate_change >= MATURE_STRENGTHENING_THRESHOLD:
            return "strengthening"

        return "stable"

    if node.driver_type == "ramping":
        reorder_breadth = getattr(node, "reorder_breadth", None)

        if reorder_breadth is None:
            return None

        if reorder_breadth < RAMPING_WEAK_REORDER_THRESHOLD:
            return "weak_reorder"

        if reorder_breadth > RAMPING_STRONG_REORDER_THRESHOLD:
            return "strong_reorder"

        return "mixed_reorder"

    # new: no valid prior baseline for a health verdict
    return None


# ---------------------------------------------------------------------------
# Dimension 4 — emphasis (is_standout + surfaced_by)
# ---------------------------------------------------------------------------

def emphasis_of(node, surfaced_by):
    peer_comparison = getattr(
        node,
        "peer_comparison",
        None,
    )

    is_standout = (
        peer_comparison.get("is_standout")
        if isinstance(peer_comparison, dict)
        else None
    )

    if surfaced_by == "signal":
        return "flagged"

    if is_standout is True:
        return "concentrated"

    if is_standout is False:
        return "broad"

    return "unspecified"


# ---------------------------------------------------------------------------
# Overrides — special stories composition can't capture alone
# ---------------------------------------------------------------------------

def apply_overrides(node, classification):
    # A negative ramping contribution combined with broad reorder activity
    # is more consistent with post-launch settling / normalization than
    # broad launch failure.
    if (
        node.driver_type == "ramping"
        and node.impact is not None
        and node.impact < 0
        and classification["health"] == "strong_reorder"
    ):
        classification["health"] = "settling"
        classification["note"] = "possible_load_in_normalization"

    return classification


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def classify_node(node, surfaced_by):
    classification = {
        "frame": frame_of(node.driver_type),
        "valence": valence_of(
            getattr(node, "impact", None),
            getattr(node, "relationship", None),
        ),
        "health": health_of(node),
        "emphasis": emphasis_of(
            node=node,
            surfaced_by=surfaced_by,
        ),
        "note": None,
    }

    return apply_overrides(
        node,
        classification,
    )

"""
Narrative rendering for classified explanation-tree nodes.

The classifier produces a compositional struct:

    frame
    valence
    health
    emphasis
    note

This layer turns that struct into a deterministic user-facing narrative payload:

    {
        "headline": ...,
        "detail": ...,
        "classification": ...
    }

The goal is to explain meaning without overstating certainty or repeating
every metric already visible in the UI.
"""


FRAME_LABELS = {
    "new_distribution": "New placements",
    "recent_launch": "Recently launched placements",
    "established": "Established placements",
}


def narrate_node(node, classification) -> dict:
    frame = classification.get("frame")
    valence = classification.get("valence")
    health = classification.get("health")
    emphasis = classification.get("emphasis")
    note = classification.get("note")

    subject = _subject_for_node(
        node=node,
        frame=frame,
    )

    headline = _build_headline(
        node=node,
        subject=subject,
        frame=frame,
        valence=valence,
        health=health,
        emphasis=emphasis,
        note=note,
    )

    detail = _build_detail(
        node=node,
        frame=frame,
        valence=valence,
        health=health,
        emphasis=emphasis,
        note=note,
    )

    return {
        "headline": headline,
        "detail": detail,
        "classification": classification,
    }


# ---------------------------------------------------------------------------
# Subject
# ---------------------------------------------------------------------------

def _subject_for_node(node, frame) -> str:
    scope = getattr(node, "scope", {}) or {}

    if scope.get("sku"):
        return scope["sku"]

    if scope.get("chain"):
        return scope["chain"]

    return FRAME_LABELS.get(
        frame,
        "Business",
    )


# ---------------------------------------------------------------------------
# Headline
# ---------------------------------------------------------------------------

def _build_headline(
    node,
    subject,
    frame,
    valence,
    health,
    emphasis,
    note,
) -> str:

    # -----------------------------------------------------
    # DRIVER
    # -----------------------------------------------------

    if node.node_type == "driver":

        if frame == "new_distribution":
            return "New placements are driving incremental volume"

        if frame == "recent_launch":
            if health == "settling":
                return "Recent launches appear to be settling"

            if health == "weak_reorder":
                return "Recent launches show weak reorder activity"

            if health == "strong_reorder":
                return "Recent launches show strong reorder activity"

            if health == "mixed_reorder":
                return "Recent launches show mixed reorder activity"

            return "Recent launches are still developing"

        if frame == "established":
            if health == "strengthening":
                return "Established placements are strengthening"

            if health == "weakening":
                return "Established placements are weakening"

            if health == "softening":
                return "Established placements are softening"

            if health == "stable":
                return "Established placements are relatively stable"

            return "Established placements"


    # -----------------------------------------------------
    # NEW
    # -----------------------------------------------------

    if frame == "new_distribution":
        if valence in {"contributing", "bright_spot"}:
            return f"{subject} is contributing incremental volume"

        if valence in {"declining", "drag"}:
            return f"{subject} is offsetting new-placement growth"

        return f"{subject} is contributing through new distribution"


    # -----------------------------------------------------
    # RAMPING
    # -----------------------------------------------------

    if frame == "recent_launch":
        if health == "settling":
            return f"{subject} appears to be settling after launch"

        if health == "weak_reorder":
            return f"{subject} shows unusually weak reorder activity"

        if health == "strong_reorder":
            return f"{subject} shows broad reorder activity"

        if health == "mixed_reorder":
            return f"{subject} shows mixed reorder activity"

        if valence in {"declining", "drag"}:
            return f"{subject} is contributing negatively among recent launches"

        if valence in {"contributing", "bright_spot"}:
            return f"{subject} is contributing positively among recent launches"

        return f"{subject} is still developing after launch"


    # -----------------------------------------------------
    # MATURE
    # -----------------------------------------------------

    if frame == "established":
        if valence == "bright_spot" and health == "strengthening":
            return f"{subject} is a bright spot in the established business"

        if valence == "drag" and health == "weakening":
            return f"{subject} is a notable weak spot in the established business"

        if valence == "drag" and health == "softening":
            return f"{subject} is softening against the broader established trend"

        if health == "strengthening":
            return f"{subject} is strengthening"

        if health == "weakening":
            return f"{subject} is weakening"

        if health == "softening":
            return f"{subject} is softening"

        if health == "stable":
            return f"{subject} is relatively stable"

        return f"{subject} is contributing within the established business"

    return subject


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------

def _build_detail(
    node,
    frame,
    valence,
    health,
    emphasis,
    note,
) -> str | None:

    impact = getattr(node, "impact", None)


    # -----------------------------------------------------
    # SIGNAL-SURFACED NODES
    # -----------------------------------------------------

    if emphasis == "flagged":

        if frame == "recent_launch" and health == "weak_reorder":
            reorder_breadth = getattr(
                node,
                "reorder_breadth",
                None,
            )

            if reorder_breadth is not None:
                return (
                    f"Despite its smaller unit impact, only "
                    f"{reorder_breadth:.1%} of placements reordered."
                )

            return (
                "Despite its smaller unit impact, reorder activity "
                "is unusually weak versus comparable placements."
            )


        if (
            frame == "established"
            and health in {"weakening", "softening"}
        ):
            rate_change = getattr(
                node,
                "rate_change",
                None,
            )

            if rate_change is not None:
                base = (
                    f"Despite its smaller unit impact, VPO declined "
                    f"{abs(rate_change):.1%} versus the prior period."
                )

                return base


    # -----------------------------------------------------
    # RAMPING NORMALIZATION
    # -----------------------------------------------------

    if (
        frame == "recent_launch"
        and note == "possible_load_in_normalization"
    ):
        reorder_breadth = getattr(
            node,
            "reorder_breadth",
            None,
        )

        avg_reorders = getattr(
            node,
            "avg_reorders",
            None,
        )

        parts = []

        if reorder_breadth is not None:
            parts.append(
                f"{reorder_breadth:.1%} of placements reordered"
            )

        if avg_reorders is not None:
            parts.append(
                f"those that reordered averaged "
                f"{avg_reorders:.1f} reorders"
            )

        if parts:
            evidence = ", and ".join(parts)

            return (
                f"Volume declined, but {evidence} — more consistent "
                "with post-launch normalization than broad launch failure."
            )

        return (
            "The decline appears more consistent with post-launch "
            "normalization than broad launch failure."
        )


    # -----------------------------------------------------
    # MATURE
    # -----------------------------------------------------

    if frame == "established":
        rate_change = getattr(
            node,
            "rate_change",
            None,
        )

        if rate_change is not None and health == "strengthening":
            base = (
                f"VPO increased {rate_change:.1%} "
                "versus the prior period."
            )

            return _apply_emphasis(
                base=base,
                emphasis=emphasis,
            )


        if rate_change is not None and health == "weakening":
            base = (
                f"VPO declined {abs(rate_change):.1%} "
                "versus the prior period."
            )

            return _apply_emphasis(
                base=base,
                emphasis=emphasis,
            )


        if rate_change is not None and health == "softening":
            base = (
                f"VPO declined {abs(rate_change):.1%} versus the prior "
                "period — a mild slip worth monitoring."
            )

            return _apply_emphasis(
                base=base,
                emphasis=emphasis,
            )


        if rate_change is not None and health == "stable":
            base = "VPO was roughly flat versus the prior period."

            return _apply_emphasis(
                base=base,
                emphasis=emphasis,
            )


    # -----------------------------------------------------
    # NEW
    # -----------------------------------------------------

    if frame == "new_distribution" and impact is not None:
        base = (
            "This contribution comes from placements that did not "
            "exist in the prior comparison window."
        )

        return _apply_emphasis(
            base=base,
            emphasis=emphasis,
        )

    return None


# ---------------------------------------------------------------------------
# Emphasis modifier
# ---------------------------------------------------------------------------

def _apply_emphasis(
    base: str,
    emphasis: str | None,
) -> str:

    if emphasis == "concentrated":
        return base.rstrip(".") + ". This stands out relative to peers."

    if emphasis == "broad":
        return (
            base.rstrip(".")
            + ". This pattern appears across multiple peers."
        )

    return base

def narrate_shown_node(shown_node):
    node = shown_node.node

    classification = classify_node(
        node=node,
        surfaced_by=shown_node.surfaced_by,
    )

    narrative = narrate_node(
        node=node,
        classification=classification,
    )

    narrative_node = NarrativeNode(
        node_type=node.node_type,
        driver_type=node.driver_type,
        scope=node.scope,
        impact=node.impact,
        surfaced_by=shown_node.surfaced_by,
        classification=classification,
        headline=narrative["headline"],
        detail=narrative["detail"],
    )

    for child in shown_node.children:
        narrative_node.children.append(
            narrate_shown_node(child)
        )

    return narrative_node
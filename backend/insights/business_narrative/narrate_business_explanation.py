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
import pandas as pd
from dataclasses import dataclass, field
from backend.insights.business_narrative.select_tree_branches import make_surface_decision
from backend.insights.business_narrative.enrich_nodes import enrich_node


@dataclass
class NarrativeNode:
    node_type: str
    driver_type: str | None
    scope: dict
    impact: float | None

    surfaced_by: str
    metrics: dict
    classification: dict

    headline: str
    detail: str | None

    children: list["NarrativeNode"] = field(default_factory=list)


@dataclass
class NarrativeInputs:
    df: pd.DataFrame
    current_start: object
    current_end: object
    prior_start: object
    prior_end: object


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

def health_of(node, metrics):
    if node.driver_type == "mature":
        rate_change = metrics.get("rate_change")

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
        reorder_breadth = metrics.get("reorder_breadth")

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

def apply_overrides(node, metrics, classification):
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

def classify_node(node, metrics, surfaced_by):
    classification = {
        "frame": frame_of(node.driver_type),
        "valence": valence_of(
            getattr(node, "impact", None),
            getattr(node, "relationship", None),
        ),
        "health": health_of(
            node=node,
            metrics=metrics,
        ),
        "emphasis": emphasis_of(
            node=node,
            surfaced_by=surfaced_by,
        ),
        "note": None,
    }

    return apply_overrides(
        node=node,
        metrics=metrics,
        classification=classification,
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


def narrate_node(node, metrics, classification) -> dict:
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
        metrics=metrics,
        subject=subject,
        frame=frame,
        valence=valence,
        health=health,
        emphasis=emphasis,
        note=note,
    )

    detail = _build_detail(
        node=node,
        metrics=metrics,
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
    metrics,
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
            placements = metrics.get("placements_added")
            stores = metrics.get("stores_with_new_placements")

            if placements is not None and stores is not None:
                return (
                    f"New distribution added {placements:,} placements "
                    f"across {stores:,} stores"
                )

            if placements is not None:
                return f"New distribution added {placements:,} placements"

            return "New distribution expanded the business"

        if frame == "recent_launch":
            reorder_breadth = metrics.get("reorder_breadth")

            if reorder_breadth is not None:
                if health == "settling":
                    return (
                        f"{reorder_breadth:.1%} of recent-launch placements "
                        "reordered despite lower volume"
                    )

                if health == "weak_reorder":
                    return (
                        f"Only {reorder_breadth:.1%} of recent-launch "
                        "placements reordered"
                    )

                if health == "strong_reorder":
                    return (
                        f"{reorder_breadth:.1%} of recent-launch placements "
                        "reordered"
                    )

                if health == "mixed_reorder":
                    return (
                        f"{reorder_breadth:.1%} of recent-launch placements "
                        "reordered"
                    )

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
            rate_change = metrics.get("rate_change")

            if rate_change is not None:
                if health == "strengthening":
                    return f"Established velocity increased {rate_change:.1%}"

                if health in {"weakening", "softening"}:
                    return f"Established velocity declined {abs(rate_change):.1%}"

                if health == "stable":
                    return "Established velocity was relatively stable"

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
        distribution_type = metrics.get("distribution_type")
        stores = metrics.get("stores_with_new_placements")
        placements = metrics.get("placements_added")

        if distribution_type == "new_chain":
            if stores is not None:
                return f"{subject} launched across {stores:,} stores"
            return f"{subject} launched as a new chain"

        if distribution_type == "new_stores_in_chain":
            if stores is not None:
                return f"{subject} expanded into {stores:,} new stores"
            return f"{subject} expanded into new stores"

        if distribution_type == "new_placements_in_existing_stores":
            if placements is not None:
                return f"{subject} added {placements:,} placements in existing stores"
            return f"{subject} expanded within existing stores"

        if distribution_type == "mixed_expansion":
            return f"{subject} expanded through new stores and deeper assortment"

        if valence in {"contributing", "bright_spot"}:
            return f"{subject} is adding new distribution"

        if valence in {"declining", "drag"}:
            return f"{subject} is offsetting new-placement growth"

        return f"{subject} is expanding distribution"


    # -----------------------------------------------------
    # RAMPING
    # -----------------------------------------------------

    if frame == "recent_launch":
        reorder_breadth = metrics.get("reorder_breadth")

        if reorder_breadth is not None:
            if health == "settling":
                return (
                    f"{reorder_breadth:.1%} of {subject} placements "
                    "reordered despite lower volume"
                )

            if health == "weak_reorder":
                return f"Only {reorder_breadth:.1%} of {subject} placements reordered"

            if health == "strong_reorder":
                return f"{reorder_breadth:.1%} of {subject} placements reordered"

            if health == "mixed_reorder":
                return f"{reorder_breadth:.1%} of {subject} placements reordered"

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
        rate_change = metrics.get("rate_change")

        if rate_change is not None:
            if health == "strengthening":
                return f"{subject} velocity increased {rate_change:.1%}"

            if health in {"weakening", "softening"}:
                return f"{subject} velocity declined {abs(rate_change):.1%}"

            if health == "stable":
                return f"{subject} velocity was relatively stable"

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


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------

def _build_detail(
    node,
    metrics,
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
            placements_in_cohort = metrics.get("placements_in_cohort")
            placements_reordered = metrics.get("placements_reordered")
            stores_in_cohort = metrics.get("stores_in_cohort")
            reorder_breadth = metrics.get("reorder_breadth")

            if (
                placements_in_cohort is not None
                and placements_reordered is not None
                and stores_in_cohort is not None
            ):
                placement_word = "placement" if placements_in_cohort == 1 else "placements"
                return (
                    f"Just {placements_reordered:,} of {placements_in_cohort:,} "
                    f"{placement_word} reordered across {stores_in_cohort:,} stores."
                )

            if reorder_breadth is not None:
                return f"Only {reorder_breadth:.1%} of placements reordered."

            return (
                "Reorder activity is unusually weak versus comparable "
                "placements."
            )

        if (
            frame == "established"
            and health in {"weakening", "softening"}
        ):
            return _mature_detail(
                metrics=metrics,
                health=health,
                emphasis=None,
                signal_flag=True,
            )


    # -----------------------------------------------------
    # RAMPING NORMALIZATION
    # -----------------------------------------------------

    if (
        frame == "recent_launch"
        and note == "possible_load_in_normalization"
    ):
        placements_in_cohort = metrics.get("placements_in_cohort")
        placements_reordered = metrics.get("placements_reordered")
        stores_in_cohort = metrics.get("stores_in_cohort")
        avg_reorders = metrics.get("avg_reorders")
        reorder_breadth = metrics.get("reorder_breadth")

        if (
            placements_in_cohort is not None
            and placements_reordered is not None
        ):
            first_sentence = (
                f"{placements_reordered:,} of {placements_in_cohort:,} "
                "placements reordered"
            )

            if stores_in_cohort is not None:
                first_sentence += f" across {stores_in_cohort:,} stores"

            if avg_reorders is not None:
                first_sentence += (
                    f", averaging {avg_reorders:.1f} reorders among "
                    "those that reordered"
                )

            return (
                first_sentence
                + ". That pattern is more consistent with post-launch "
                "normalization than broad launch weakness."
            )

        if reorder_breadth is not None:
            first_sentence = f"{reorder_breadth:.1%} of placements reordered"

            if stores_in_cohort is not None:
                first_sentence += f" across {stores_in_cohort:,} stores"

            if avg_reorders is not None:
                first_sentence += (
                    f", averaging {avg_reorders:.1f} reorders among "
                    "those that reordered"
                )

            return (
                first_sentence
                + ". That pattern is more consistent with post-launch "
                "normalization than broad launch weakness."
            )

        return (
            "The decline appears more consistent with post-launch "
            "normalization than broad launch failure."
        )


    # -----------------------------------------------------
    # RAMPING
    # -----------------------------------------------------

    if frame == "recent_launch":
        placements_in_cohort = metrics.get("placements_in_cohort")
        placements_reordered = metrics.get("placements_reordered")
        stores_in_cohort = metrics.get("stores_in_cohort")
        avg_reorders = metrics.get("avg_reorders")

        if (
            placements_in_cohort is not None
            and placements_reordered is not None
        ):
            base = (
                f"{placements_reordered:,} of {placements_in_cohort:,} "
                "placements reordered"
            )

            if stores_in_cohort is not None:
                base += f" across {stores_in_cohort:,} stores"

            if avg_reorders is not None:
                base += (
                    f", averaging {avg_reorders:.1f} reorders among "
                    "those that reordered"
                )

            return _apply_emphasis(base=base + ".", emphasis=emphasis)


    # -----------------------------------------------------
    # MATURE
    # -----------------------------------------------------

    if frame == "established":
        return _mature_detail(
            metrics=metrics,
            health=health,
            emphasis=emphasis,
        )


    # -----------------------------------------------------
    # NEW
    # -----------------------------------------------------

    if frame == "new_distribution" and impact is not None:
        stores = metrics.get("stores_with_new_placements")
        placements = metrics.get("placements_added")
        skus = metrics.get("skus_added")
        avg_skus_per_store = metrics.get("avg_skus_per_store")
        distribution_type = metrics.get("distribution_type")

        # Root NEW driver: headline carries scale; detail adds assortment context.
        if node.node_type == "driver":
            if skus is not None and avg_skus_per_store is not None:
                sku_word = "SKU" if skus == 1 else "SKUs"
                return (
                    f"Expansion spanned {skus:,} {sku_word}, averaging "
                    f"{avg_skus_per_store:.1f} new SKUs per store."
                )

            if skus is not None:
                sku_word = "SKU" if skus == 1 else "SKUs"
                return f"Expansion spanned {skus:,} {sku_word}."

            if placements is not None and stores is not None:
                return (
                    f"{placements:,} placements were added across "
                    f"{stores:,} stores."
                )

            return (
                "This contribution comes from placements that did not "
                "exist in the prior comparison window."
            )

        if distribution_type == "new_chain":
            if placements is not None and skus is not None:
                base = (
                    f"The launch added {placements:,} placements "
                    f"across {skus:,} SKUs."
                )
            elif placements is not None:
                base = f"The launch added {placements:,} placements."
            else:
                base = "This is new chain distribution."

        elif distribution_type == "new_stores_in_chain":
            if placements is not None:
                base = (
                    f"Those new stores added {placements:,} placements "
                    "to the business."
                )
            else:
                base = "Growth came from distribution into new stores."

        elif distribution_type == "new_placements_in_existing_stores":
            if stores is not None:
                base = (
                    f"The expansion deepened distribution across "
                    f"{stores:,} existing stores."
                )
            else:
                base = "Growth came from deeper distribution in existing stores."

        elif distribution_type == "mixed_expansion":
            if placements is not None and stores is not None:
                base = (
                    f"{placements:,} placements were added across {stores:,} stores "
                    "through a mix of new stores and expansion within existing stores."
                )
            else:
                base = (
                    "Growth came from a mix of new stores and expansion "
                    "within existing stores."
                )

        elif placements is not None and stores is not None:
            base = (
                f"{placements:,} placements were added across "
                f"{stores:,} stores."
            )

        else:
            base = (
                "This contribution comes from placements that did not "
                "exist in the prior comparison window."
            )

        return _apply_emphasis(
            base=base,
            emphasis=emphasis,
        )

    return None


def _mature_detail(
    metrics,
    health,
    emphasis,
    signal_flag=False,
) -> str | None:
    rate_current = metrics.get("rate_current")
    rate_prior = metrics.get("rate_prior")
    rate_change = metrics.get("rate_change")
    business_rate_current = metrics.get("business_rate_current")
    vs_business_rate = metrics.get("vs_business_rate")

    stores_in_cohort = metrics.get("stores_in_cohort")
    placements_in_cohort = metrics.get("placements_in_cohort")

    # -----------------------------------------------------
    # Period-over-period movement
    # -----------------------------------------------------

    if rate_prior is not None and rate_current is not None:
        if rate_current > rate_prior:
            base = (
                f"Velocity increased from {rate_prior:.2f} "
                f"to {rate_current:.2f}"
            )

        elif rate_current < rate_prior:
            base = (
                f"Velocity declined from {rate_prior:.2f} "
                f"to {rate_current:.2f}"
            )

        else:
            base = f"Velocity was flat at {rate_current:.2f}"

    elif rate_change is not None:
        if rate_change > 0:
            base = f"Velocity increased {rate_change:.1%}"

        elif rate_change < 0:
            base = f"Velocity declined {abs(rate_change):.1%}"

        else:
            base = "Velocity was roughly flat versus the prior period"

    else:
        if health == "stable":
            return "Velocity was roughly flat versus the prior period."

        return None

    # -----------------------------------------------------
    # Cohort scale
    # -----------------------------------------------------

    if (
        placements_in_cohort is not None
        and stores_in_cohort is not None
    ):
        base += (
            f" across {placements_in_cohort:,} placements "
            f"in {stores_in_cohort:,} stores"
        )

    elif placements_in_cohort is not None:
        base += f" across {placements_in_cohort:,} placements"

    elif stores_in_cohort is not None:
        base += f" across {stores_in_cohort:,} stores"

    base += "."

    # -----------------------------------------------------
    # Velocity vs. overall Mature business
    # -----------------------------------------------------
    # Skip the Mature root itself, where the node's velocity
    # is the benchmark and vs_business_rate == 0.

    if (
        rate_current is not None
        and business_rate_current is not None
        and vs_business_rate is not None
        and abs(vs_business_rate) > 1e-6
    ):
        if vs_business_rate < 0:
            base += (
                f" At {rate_current:.2f}, it remains "
                f"{abs(vs_business_rate):.1%} below the overall "
                f"Mature velocity of {business_rate_current:.2f}."
            )

        else:
            velocity_multiple = (
                rate_current / business_rate_current
            )

            base += (
                f" At {rate_current:.2f}, it is "
                f"{velocity_multiple:.1f}× the overall "
                f"Mature velocity of {business_rate_current:.2f}."
            )

    # -----------------------------------------------------
    # Signal / emphasis
    # -----------------------------------------------------

    if signal_flag:
        return (
            base.rstrip(".")
            + ". Despite its smaller unit impact, this stands out "
            "as an unusual signal."
        )

    return _apply_emphasis(
        base=base,
        emphasis=emphasis,
    )


# ---------------------------------------------------------------------------
# Emphasis modifier
# ---------------------------------------------------------------------------

def _apply_emphasis(
    base: str,
    emphasis: str | None,
) -> str:

    if emphasis == "concentrated":
        return base.rstrip(".") + ". This stands out relative to peers."

    # "broad" is useful as structured classification metadata, but does not
    # add enough user-facing information to warrant repetitive narration.
    return base

def narrate_shown_node(
    shown_node,
    inputs,
    business_rate_current=None,
):
    node = shown_node.node

    # The top-level Mature driver is the overall Mature business.
    # Use its VPO as the benchmark for this entire Mature branch.
    if (
        node.driver_type == "mature"
        and not node.scope
        and business_rate_current is None
    ):
        business_rate_current = getattr(
            node,
            "rate_current",
            None,
        )

    metrics = enrich_node(
        node=node,
        inputs=inputs,
        business_rate_current=business_rate_current,
    )

    classification = classify_node(
        node=node,
        metrics=metrics,
        surfaced_by=shown_node.surfaced_by,
    )

    narrative = narrate_node(
        node=node,
        metrics=metrics,
        classification=classification,
    )

    narrative_node = NarrativeNode(
        node_type=node.node_type,
        driver_type=node.driver_type,
        scope=node.scope,
        impact=node.impact,
        surfaced_by=shown_node.surfaced_by,
        metrics=metrics,
        classification=classification,
        headline=narrative["headline"],
        detail=narrative["detail"],
    )

    for child in shown_node.children:
        narrative_node.children.append(
            narrate_shown_node(
                shown_node=child,
                inputs=inputs,
                business_rate_current=business_rate_current,
            )
        )

    return narrative_node
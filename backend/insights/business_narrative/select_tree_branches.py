from statistics import mean, stdev
from dataclasses import dataclass, field
from backend.insights.business_narrative.business_narrative_helpers import get_comparable_nodes, compute_peer_comparison, SIGNAL_METRICS


MIN_SHARE = 0.10        # <- your old SIGNIFICANT_CONTRIBUTION_THRESHOLD
MAX_SHARE = 0.40        # small nodes must explain this much of their parent
BUSINESS_REF = 0.10 


"""
Surfacing layer for the business explanation tree.

Takes a built ExplanationNode tree and decides which nodes become
"shown" (i.e. become narrative nodes), why they surfaced, and how they
compare to their siblings.

Two surfacing gates:
  - contribution: is this node a meaningful share of its parent (scaled so
    smaller-business-share nodes must explain more of their parent)?
  - signal: is this node anomalous vs its peers on a bucket-specific metric?

Two expansion controls (whether to drill into a node's children):
  - contribution nodes: only drill if the split is concentrated (a child
    stands out) — uniform splits add nothing.
  - signal nodes: children are judged against each other (siblings mode),
    so uniform anomalies don't repeat down the tree.
"""


# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

MIN_COMPARISON_GROUP = 3
STANDOUT_MULTIPLIER = 1.2

# "is the split concentrated enough to bother drilling" — gentler than
# STANDOUT_MULTIPLIER on purpose: mild real concentration should still expand.
EXPAND_STANDOUT_MULTIPLIER = 1.10


@dataclass
class ShownNode:
    node: object
    surfaced_by: str
    children: list["ShownNode"] = field(default_factory=list)

# ---------------------------------------------------------------------------
# Surface decision (per node)
# ---------------------------------------------------------------------------

def make_surface_decision(node, parent, all_nodes, comparison_mode="global") -> str | None:
    total_business_change = sum(
        n.impact for n in all_nodes if n.node_type == "driver"
    ) or None

    if node.node_type == "root":
        return "contribution"
    if node.node_type == "driver":
        return "contribution"
    if node.node_type == "residual":
        return None

    if is_significant_contribution(node, parent, total_business_change):
        return "contribution"

    if comparison_mode == "siblings" and parent is not None:
        comparable_nodes = [
            sibling
            for sibling in parent.children
            if sibling is not node
            and sibling.node_type == "entity"
        ]
    else:
        comparable_nodes = get_comparable_nodes(
            node,
            all_nodes,
            mode="global",
        )

    signal_metrics = SIGNAL_METRICS.get(node.driver_type, {})

    for metric_name, direction in signal_metrics.items():
        if is_strong_signal(
            node=node,
            metric_name=metric_name,
            comparable_nodes=comparable_nodes,
            direction=direction,
        ):
            return "signal"

    return None


def is_significant_contribution(node, parent, total_business_change) -> bool:
    if parent is None or node.impact is None or parent.impact in (None, 0):
        return False
    if total_business_change in (None, 0):
        return False

    share_of_parent = abs(node.impact) / abs(parent.impact)
    share_of_business = abs(node.impact) / abs(total_business_change)

    # The less of the business a node represents, the more of its parent it
    # must explain. Big nodes can be diffuse; small nodes must be concentrated.
    required_share = MIN_SHARE + (MAX_SHARE - MIN_SHARE) * (
        1 - min(share_of_business / BUSINESS_REF, 1)
    )
    return share_of_parent >= required_share


def is_strong_signal(node, metric_name, comparable_nodes, direction, threshold=2.0) -> bool:
    value = getattr(node, metric_name, None)
    if value is None:
        return False

    comparison_values = [
        getattr(other, metric_name)
        for other in comparable_nodes
        if getattr(other, metric_name, None) is not None
    ]
    if len(comparison_values) < MIN_COMPARISON_GROUP:
        return False

    comparison_mean = mean(comparison_values)
    comparison_std = stdev(comparison_values)
    if comparison_std == 0:
        return False

    z_score = (value - comparison_mean) / comparison_std
    if direction == "low":
        return z_score <= -threshold
    if direction == "high":
        return z_score >= threshold
    return False



# ---------------------------------------------------------------------------
# Expansion gate (whether to drill into a contribution node's children)
# ---------------------------------------------------------------------------

def should_expand_contribution(node) -> bool:
    """
    Only drill into a contribution node if the split is concentrated — one
    child meaningfully exceeds the sibling average. Uniform splits (e.g. three
    SKUs each ~33%) add nothing, so we stop.
    """
    entity_children = [c for c in node.children if c.node_type == "entity"]
    if len(entity_children) < 2:
        return False

    values = [
        abs(c.impact)
        for c in entity_children
        if c.impact is not None
    ]
    if len(values) < 2:
        return False

    peer_mean = sum(values) / len(values)
    top = max(values)
    if peer_mean == 0:
        return False

    return top >= peer_mean * EXPAND_STANDOUT_MULTIPLIER


# ---------------------------------------------------------------------------
# Traversal — build the flat list of shown nodes
# ---------------------------------------------------------------------------

def build_shown_nodes(tree):
    all_nodes = []

    def collect_all(node):
        all_nodes.append(node)

        for child in node.children:
            collect_all(child)

    collect_all(tree)


    def walk(
        node,
        parent=None,
        comparison_mode="global",
    ):
        decision = make_surface_decision(
            node=node,
            parent=parent,
            all_nodes=all_nodes,
            comparison_mode=comparison_mode,
        )

        if decision is None:
            return None

        shown_node = ShownNode(
            node=node,
            surfaced_by=decision,
        )

        if (
            decision == "contribution"
            and not should_expand_contribution(node)
        ):
            return shown_node

        child_mode = (
            "siblings"
            if decision == "signal"
            else "global"
        )

        for child in node.children:
            shown_child = walk(
                node=child,
                parent=node,
                comparison_mode=child_mode,
            )

            if shown_child is not None:
                shown_node.children.append(shown_child)

        return shown_node


    shown_nodes = []

    for driver in tree.children:
        shown_node = walk(
            node=driver,
            parent=tree,
        )

        if shown_node is not None:
            shown_nodes.append(shown_node)

    return shown_nodes

SIGNAL_METRICS = {
    "new": {},
    "ramping": {
        "reorder_breadth": "low",
        "avg_reorders": "low",
    },
    "mature": {
        "rate_change": "low",
    },
}

MIN_COMPARISON_GROUP = 3
STANDOUT_MULTIPLIER = 1.2

PEER_METRIC = {
    "mature": "rate_change",
    "ramping": "reorder_breadth",
}


def get_comparable_nodes(node, all_nodes, mode="global"):
    if mode == "siblings":
        parent = getattr(node, "parent", None)
        if parent is None:
            return []
        return [
            c for c in parent.children
            if c is not node and c.node_type == "entity"   # exclude residual
        ]

    # default global: same driver_type across the tree
    return [
        other for other in all_nodes
        if other is not node
        and other.node_type == "entity"
        and other.driver_type == node.driver_type
    ]



def compute_peer_comparison(
    node,
    sibling_nodes,
) -> dict | None:
    """
    Compare a node against all of its candidate siblings at the
    current split, before top-N selection and residual collapse.

    Peer metric depends on lifecycle:
        Mature  -> rate_change
        Ramping -> reorder_breadth
        New     -> impact

    Direction comes from SIGNAL_METRICS where applicable.
    The node itself is excluded from the peer baseline.
    """

    metric = PEER_METRIC.get(
        node.driver_type,
        "impact",
    )

    direction = SIGNAL_METRICS.get(
        node.driver_type,
        {},
    ).get(metric)

    peers = [
        sibling
        for sibling in sibling_nodes
        if sibling is not node
        and sibling.node_type == "entity"
    ]

    values = [
        getattr(peer, metric)
        for peer in peers
        if getattr(peer, metric, None) is not None
    ]

    val = getattr(node, metric, None)

    if val is None or not values:
        return None

    peer_mean = sum(values) / len(values)

    # -----------------------------------------------------
    # Rank + standout logic depends on metric direction
    # -----------------------------------------------------

    if direction == "low":
        # Lower values are more notable / concerning
        ranked = sorted(values + [val])
        rank = ranked.index(val) + 1

        is_standout = (
            val <= peer_mean / STANDOUT_MULTIPLIER
            if peer_mean
            else None
        )

    elif direction == "high":
        # Higher values are more notable
        ranked = sorted(values + [val], reverse=True)
        rank = ranked.index(val) + 1

        is_standout = (
            val >= peer_mean * STANDOUT_MULTIPLIER
            if peer_mean
            else None
        )

    else:
        # Directionless metric (e.g. New impact):
        # rank by absolute magnitude
        ranked = sorted(
            values + [val],
            key=abs,
            reverse=True,
        )
        rank = ranked.index(val) + 1

        is_standout = (
            abs(val) >= abs(peer_mean) * STANDOUT_MULTIPLIER
            if peer_mean
            else None
        )

    return {
        "metric": metric,
        "value": float(val),
        "peer_mean": float(peer_mean),
        "peer_count": int(len(values)),
        "rank": int(rank),
        "is_standout": (
            bool(is_standout)
            if is_standout is not None
            else None
        ),
    }
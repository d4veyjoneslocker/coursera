from dataclasses import dataclass, field

import pandas as pd
import numpy as np

from backend.insights.contribution_diagnostics import (
    build_units_contribution_table,
    aggregate_units_contributions,
)

from backend.insights.business_narrative.business_narrative_helpers import compute_peer_comparison

from backend.metrics.metric_growth_rates import calculate_vpo_3m



DEFAULT_DIMENSIONS = ["chain", "sku", "dc", "state"]


# ---------------------------------------------------------
# Explanation node
# ---------------------------------------------------------

@dataclass
class ExplanationNode:
    node_type: str
    scope: dict
    driver_type: str | None
    impact: float

    relationship: str | None = None
    split_dimension: str | None = None
    split_score: float | None = None
    depth: int = 0

    context: list[dict] = field(default_factory=list)

    peer_comparison: dict | None = None

    stores_current: int | None = None
    stores_prior: int | None = None

    pods_current: int | None = None
    pods_prior: int | None = None

    rate_current: float | None = None
    rate_prior: float | None = None
    rate_change: float | None = None 

    reorder_breadth: float | None = None       # % of ramping placements that reordered
    avg_reorders: float | None = None          # avg reorders per reordering placement
    months_since_launch: float | None = None   # median across ramping placements

    children: list["ExplanationNode"] = field(default_factory=list)


    def to_dict(self) -> dict:
        return {
                "node_type": self.node_type,
                "scope": self.scope,
                "driver_type": self.driver_type,
                "impact": self.impact,

                "relationship": self.relationship,
                "split_dimension": self.split_dimension,
                "split_score": self.split_score,
                "depth": self.depth,

                "context": self.context,
                "peer_comparison": self.peer_comparison,

                "stores_current": self.stores_current,
                "stores_prior": self.stores_prior,
                "pods_current": self.pods_current,
                "pods_prior": self.pods_prior,

                "rate_current": self.rate_current,
                "rate_prior": self.rate_prior,
                "rate_change": self.rate_change,

                "reorder_breadth": self.reorder_breadth,
                "avg_reorders": self.avg_reorders,
                "months_since_launch": self.months_since_launch,

                "children": [
                    child.to_dict()
                    for child in self.children
                ],
        }


# ---------------------------------------------------------
# Scope helpers
# ---------------------------------------------------------

def filter_contributions_to_scope(
    contributions: pd.DataFrame,
    scope: dict,
) -> pd.DataFrame:

    result = contributions

    for column, value in scope.items():
        if column in result.columns and value is not None:
            result = result[result[column] == value]

    return result.copy()


def filter_raw_to_scope(
    df: pd.DataFrame,
    scope: dict,
) -> pd.DataFrame:

    result = df

    for column, value in scope.items():
        if column in result.columns and value is not None:
            result = result[result[column] == value]

    return result.copy()

def compute_node_velocity(
    df: pd.DataFrame,
    scope: dict,
    current_end,
    prior_end,
):
    scoped_df = filter_raw_to_scope(
        df,
        scope,
    )

    mature_df = scoped_df[
        scoped_df["sku_lifecycle"] == "Mature"
    ].copy()

    if mature_df.empty:
        return None, None, None

    mature_pods = mature_df[
        "pod_helper"
    ].dropna().unique()

    mature_history_df = df[
        df["pod_helper"].isin(mature_pods)
    ].copy()

    if mature_history_df.empty:
        return None, None, None

    velocity = calculate_vpo_3m(
        mature_df,
        mature_history_df,
        [],
    )

    current_row = velocity[
        velocity["month_year"] == current_end
    ]

    prior_row = velocity[
        velocity["month_year"] == prior_end
    ]

    rate_current = (
        None
        if current_row.empty
        else current_row.iloc[0]["vpo_3m"]
    )

    rate_prior = (
        None
        if prior_row.empty
        else prior_row.iloc[0]["vpo_3m"]
    )

    if (
        rate_current is None
        or rate_prior is None
        or pd.isna(rate_current)
        or pd.isna(rate_prior)
        or rate_prior == 0
    ):
        rate_change = None
    else:
        rate_change = (
            rate_current - rate_prior
        ) / rate_prior

    return (
        rate_current,
        rate_prior,
        rate_change,
    )

def _apply_ramping_metrics(node: ExplanationNode, df: pd.DataFrame, current_end) -> None:
    """
    Reorder health for a ramping node, measured over ONLY the Ramping
    placements in this scope so mature stores in the same scope don't
    dilute the signal.
    """
    scoped = filter_raw_to_scope(df, node.scope)
    if scoped.empty:
        return

    ramping_rows = scoped[scoped["sku_lifecycle"] == "Ramping"]
    if ramping_rows.empty:
        return

    atom = ["pod_helper", "coded_customer", "sku"]

    per_placement = (
        ramping_rows.groupby(atom, dropna=False)["reorder_flag_pod"]
        .sum()
        .reset_index(name="reorders")
    )

    if len(per_placement) > 0:
        reordered = per_placement["reorders"] > 0
        node.reorder_breadth = float(reordered.mean())
        if reordered.any():
            node.avg_reorders = float(per_placement.loc[reordered, "reorders"].mean())

    firsts = (
        ramping_rows.groupby(atom, dropna=False)["sku_first_month_purchased"]
        .first()
    )
    months = (current_end - firsts).apply(lambda x: getattr(x, "n", x))
    if len(months) > 0:
        node.months_since_launch = float(np.median(months.values))


def compute_node_metrics(node: ExplanationNode, df: pd.DataFrame, current_end, prior_end) -> None:
    """
    Stage-aware dispatch. Each driver_type gets ONLY its valid metric:
        new      -> nothing (units only)
        ramping  -> reorder breadth / avg reorders / months-since-launch
        mature   -> per-store velocity (current/prior/change)
    Mutates node in place.
    """

    if node.driver_type == "mature":
        rc, rp, rch = compute_node_velocity(
            df,
            node.scope,
            current_end,
            prior_end,
        )
        node.rate_current, node.rate_prior, node.rate_change = rc, rp, rch

    elif node.driver_type == "ramping":
        _apply_ramping_metrics(node, df, current_end)

    # new: intentionally nothing


def get_remaining_dimensions(
    contributions: pd.DataFrame,
    node: ExplanationNode,
    dimensions: list[str],
) -> list[str]:

    used_dimensions = set(node.scope.keys())

    return [
        dimension
        for dimension in dimensions
        if dimension not in used_dimensions and dimension in contributions.columns
    ]


# ---------------------------------------------------------
# Context
# ---------------------------------------------------------

def get_relevant_context(
    scope: dict,
    context_records: list[dict],
) -> list[dict]:
    """
    Simple V1 scope matcher.

    A context record matches when every populated scope field
    in that context record matches the node scope.

    Example:

        context:
            {"chain": "SPROUTS"}

        node:
            {"chain": "SPROUTS", "sku": "VANILLA"}

        -> match
    """

    matches = []

    for context in context_records:
        context_scope = context.get("scope", {})

        if not context_scope:
            continue

        matched = True

        for key, value in context_scope.items():
            if value is None:
                continue

            if scope.get(key) != value:
                matched = False
                break

        if matched:
            matches.append(context)

    return matches


# ---------------------------------------------------------
# Relationship
# ---------------------------------------------------------

def get_relationship(
    child_impact: float,
    parent_impact: float,
) -> str:

    if child_impact == 0 or parent_impact == 0:
        return "neutral"

    if child_impact * parent_impact > 0:
        return "support"

    return "counterforce"


# ---------------------------------------------------------
# Dimension decomposition
# ---------------------------------------------------------

def get_dimension_children(
    contributions: pd.DataFrame,
    node: ExplanationNode,
    dimension: str,
) -> list[dict]:
    """
    Groups the current node's contribution rows by one candidate
    dimension.

    No lifecycle attribution is recalculated here.
    We only sum the existing additive contribution ledger.
    """

    scoped = filter_contributions_to_scope(
        contributions=contributions,
        scope=node.scope,
    )

    if scoped.empty:
        return []

    impact_cols = {
        "new": "new_impact",
        "ramping": "ramping_impact",
        "mature": "mature_impact",
    }

    impact_col = impact_cols[node.driver_type]

    grouped = (
        scoped
        .groupby(dimension, dropna=False)[impact_col]
        .sum()
        .reset_index(name="impact")
    )

    children = []

    for _, row in grouped.iterrows():
        value = row[dimension]
        impact = row["impact"]

        # Null-valued dimensions do not become recursive children.
        # Their impact naturally falls into residual.
        if pd.isna(value):
            continue

        if pd.isna(impact) or impact == 0:
            continue

        children.append({
            "dimension": dimension,
            "value": value,
            "impact": impact,
            "relationship": get_relationship(
                child_impact=impact,
                parent_impact=node.impact,
            ),
        })

    return children


# ---------------------------------------------------------
# Concentration
# ---------------------------------------------------------

def calculate_support_concentration(children, top_n_support=3):
    support = [c for c in children if c["relationship"] == "support"]
    if not support:
        return 0.0, 0.0

    impacts = sorted([abs(c["impact"]) for c in support], reverse=True)
    gross = sum(impacts)
    if gross == 0:
        return 0.0, 0.0

    top1_share = impacts[0] / gross                    # for RANKING (fair across cardinality)
    topn_share = sum(impacts[:top_n_support]) / gross  # for the GATE (is it concentrated at all)
    return top1_share, topn_share


def choose_child_dimension(
    contributions: pd.DataFrame,
    node: ExplanationNode,
    dimensions: list[str],
    top_n_support: int = 3,
    concentration_gate: float = 0.60,
) -> tuple[str | None, list[dict], float]:
    """
    Tests unused dimensions in predetermined order and chooses
    the first dimension whose supporting movement is sufficiently
    concentrated in a few children.

    Dimension priority is determined by the order of `dimensions`.
    """

    best_score = 0.0

    for dimension in dimensions:
        children = get_dimension_children(
            contributions=contributions,
            node=node,
            dimension=dimension,
        )

        if not children:
            continue

        top1_share, topn_share = calculate_support_concentration(
            children=children,
            top_n_support=top_n_support,
        )

        # Keep the strongest attempted score for debugging / metadata
        best_score = max(best_score, top1_share)

        # Take the FIRST dimension in priority order that clears the gate
        if topn_share >= concentration_gate:
            return dimension, children, top1_share

    return None, [], best_score


# ---------------------------------------------------------
# Child selection
# ---------------------------------------------------------

def select_children(
    candidates: list[dict],
    top_n_support: int = 3,
    top_n_counterforce: int = 2,
    min_child_impact: float = 100,
) -> list[dict]:
    """
    Selects supporting and counterforcing children independently.

    Both remain eligible for recursive expansion.
    """

    support = [
        child
        for child in candidates
        if child["relationship"] == "support"
        and abs(child["impact"]) >= min_child_impact
    ]

    counterforces = [
        child
        for child in candidates
        if child["relationship"] == "counterforce"
        and abs(child["impact"]) >= min_child_impact
    ]

    support = sorted(
        support,
        key=lambda child: abs(child["impact"]),
        reverse=True,
    )[:top_n_support]

    counterforces = sorted(
        counterforces,
        key=lambda child: abs(child["impact"]),
        reverse=True,
    )[:top_n_counterforce]

    return support + counterforces


# ---------------------------------------------------------
# Build children
# ---------------------------------------------------------

def build_children(
    parent: ExplanationNode,
    dimension: str,
    candidates: list[dict],
    context_records: list[dict],
    df: pd.DataFrame,
    current_end,
    prior_end,
    top_n_support: int = 3,
    top_n_counterforce: int = 2,
    min_child_impact: float = 100,
) -> list[ExplanationNode]:

    # Fixed 3-month comparison windows
    current_start = current_end - 2
    prior_start = prior_end - 2

    lifecycle_map = {
        "new": "New",
        "ramping": "Ramping",
        "mature": "Mature",
    }

    lifecycle = lifecycle_map.get(parent.driver_type)

    # -----------------------------------------------------
    # Build ALL candidate nodes first.
    #
    # Peer comparisons must use the full sibling universe,
    # before top-N selection collapses the remainder.
    # -----------------------------------------------------

    sibling_nodes = []

    for child in candidates:
        child_scope = {
            **parent.scope,
            dimension: child["value"],
        }

        # Rows belonging to this specific node.
        scoped = filter_raw_to_scope(
            df,
            child_scope,
        )

        # Keep counts lifecycle-specific to this branch.
        if lifecycle is not None:
            scoped = scoped[
                scoped["sku_lifecycle"] == lifecycle
            ]

        current_rows = scoped[
            (scoped["month_year"] >= current_start)
            & (scoped["month_year"] <= current_end)
        ]

        prior_rows = scoped[
            (scoped["month_year"] >= prior_start)
            & (scoped["month_year"] <= prior_end)
        ]

        node = ExplanationNode(
            node_type="entity",
            scope=child_scope,
            driver_type=parent.driver_type,
            impact=child["impact"],
            relationship=child["relationship"],
            context=get_relevant_context(
                child_scope,
                context_records,
            ),
            depth=parent.depth + 1,

            stores_current=int(
                current_rows["coded_customer"].nunique()
            ),
            stores_prior=int(
                prior_rows["coded_customer"].nunique()
            ),
            pods_current=int(
                current_rows["pod_helper"].nunique()
            ),
            pods_prior=int(
                prior_rows["pod_helper"].nunique()
            ),
        )

        compute_node_metrics(
            node,
            df,
            current_end,
            prior_end,
        )

        sibling_nodes.append(node)

    # -----------------------------------------------------
    # Peer comparison
    #
    # IMPORTANT: this happens BEFORE selection/residual.
    # sibling_nodes contains the full candidate sibling set.
    # -----------------------------------------------------

    for node in sibling_nodes:
        node.peer_comparison = compute_peer_comparison(
            node,
            sibling_nodes,
        )

    # -----------------------------------------------------
    # Select the children that actually survive into tree.
    # -----------------------------------------------------

    selected = select_children(
        candidates=candidates,
        top_n_support=top_n_support,
        top_n_counterforce=top_n_counterforce,
        min_child_impact=min_child_impact,
    )

    selected_values = {
        child["value"]
        for child in selected
    }

    children = [
        node
        for node in sibling_nodes
        if node.scope.get(dimension) in selected_values
    ]

    # -----------------------------------------------------
    # Residual
    #
    # Always reconcile mathematically.
    #
    # Includes:
    # - unselected small children
    # - children beyond top-N
    # - null-dimension groups
    #
    # Residual is NOT part of peer comparison.
    # -----------------------------------------------------

    selected_impact = sum(
        child.impact
        for child in children
    )

    residual_impact = (
        parent.impact
        - selected_impact
    )

    if abs(residual_impact) > 1e-6:
        children.append(
            ExplanationNode(
                node_type="residual",
                scope=parent.scope.copy(),
                driver_type=parent.driver_type,
                impact=residual_impact,
                relationship="residual",
                depth=parent.depth + 1,
            )
        )

    # -----------------------------------------------------
    # Reconciliation seatbelt
    # -----------------------------------------------------

    total = sum(
        child.impact
        for child in children
    )

    if abs(total - parent.impact) >= 1e-6:
        raise ValueError(
            f"Children don't sum to parent at scope={parent.scope}, "
            f"driver={parent.driver_type}: "
            f"{total} vs {parent.impact}"
        )

    return children

# ---------------------------------------------------------
# Expansion gates
# ---------------------------------------------------------

def should_expand(
    node: ExplanationNode,
    parent_impact: float,
    remaining_dimensions: list[str],
    magnitude_floor: float = 250,
    min_share_of_parent: float = 0.03,
    max_depth: int = 4,
) -> bool:

    if node.node_type == "residual":
        return False

    if node.driver_type is None:
        return False

    if node.depth >= max_depth:
        return False

    if not remaining_dimensions:
        return False

    impact = abs(node.impact)

    if impact < magnitude_floor:
        return False

    if parent_impact and impact / abs(parent_impact) < min_share_of_parent:
        return False

    return True


# ---------------------------------------------------------
# Recursive node expansion
# ---------------------------------------------------------

def expand_node(
    contributions: pd.DataFrame,
    node: ExplanationNode,
    parent_impact: float,
    dimensions: list[str],
    context_records: list[dict],
    df: pd.DataFrame,
    current_end,
    prior_end,
    top_n_support: int = 3,
    top_n_counterforce: int = 2,
    concentration_gate: float = 0.60,
    magnitude_floor: float = 250,
    min_child_impact: float = 100,
    min_share_of_parent: float = 0.03,
    max_depth: int = 4,
) -> ExplanationNode:

    remaining_dimensions = get_remaining_dimensions(
        contributions=contributions,
        node=node,
        dimensions=dimensions,
    )

    if not should_expand(
        node=node,
        parent_impact=parent_impact,
        remaining_dimensions=remaining_dimensions,
        magnitude_floor=magnitude_floor,
        min_share_of_parent=min_share_of_parent,
        max_depth=max_depth,
    ):
        return node

    dimension, candidates, score = choose_child_dimension(
        contributions=contributions,
        node=node,
        dimensions=remaining_dimensions,
        top_n_support=top_n_support,
        concentration_gate=concentration_gate,
    )

    if dimension is None:
        return node

    node.split_dimension = dimension
    node.split_score = score

    node.children = build_children(
        parent=node,
        dimension=dimension,
        candidates=candidates,
        context_records=context_records,
        df=df,
        current_end=current_end,
        prior_end=prior_end,
        top_n_support=top_n_support,
        top_n_counterforce=top_n_counterforce,
        min_child_impact=min_child_impact,
    )

    # -----------------------------------------------------
    # Recurse into BOTH support and counterforce.
    #
    # Residual is the only automatic dead end.
    #
    # Each child is evaluated relative to its immediate parent.
    # -----------------------------------------------------

    for child in node.children:
        if child.relationship == "residual":
            continue

        expand_node(
            contributions=contributions,
            node=child,
            parent_impact=node.impact,
            dimensions=dimensions,
            context_records=context_records,
            df=df,
            current_end=current_end,
            prior_end=prior_end,
            top_n_support=top_n_support,
            top_n_counterforce=top_n_counterforce,
            concentration_gate=concentration_gate,
            magnitude_floor=magnitude_floor,
            min_child_impact=min_child_impact,
            min_share_of_parent=min_share_of_parent,
            max_depth=max_depth,
        )

    return node


# ---------------------------------------------------------
# Root
# ---------------------------------------------------------

def build_root_node(
    contributions: pd.DataFrame,
    context_records: list[dict],
    df: pd.DataFrame,
    current_end,
    prior_end,
    magnitude_gate: float = 500,
) -> ExplanationNode | None:

    if contributions is None or contributions.empty:
        return None

    overall = aggregate_units_contributions(
        contributions=contributions,
        group_cols=None,
    )

    if overall.empty:
        return None

    row = overall.iloc[0]

    total_change = row["total_change"]
    new_impact = row["new_impact"]
    ramping_impact = row["ramping_impact"]
    mature_impact = row["mature_impact"]

    if abs(total_change) < magnitude_gate:
        return None

    root = ExplanationNode(
        node_type="business",
        scope={},
        driver_type=None,
        impact=total_change,
        relationship=None,
        context=[
            context
            for context in context_records
            if not any(
                value is not None
                for value in context.get("scope", {}).values()
            )
        ],
        depth=0,
    )

    driver_specs = [
        ("new", new_impact),
        ("ramping", ramping_impact),
        ("mature", mature_impact),
    ]

    for driver_type, impact in driver_specs:
        if impact == 0:
            continue
        driver = ExplanationNode(
            node_type="driver",
            scope={},
            driver_type=driver_type,
            impact=impact,
            relationship=get_relationship(impact, total_change),
            depth=1,
        )
        compute_node_metrics(driver, df, current_end, prior_end)
        root.children.append(driver)

    # -----------------------------------------------------
    # Root reconciliation
    # -----------------------------------------------------

    root_total = sum(child.impact for child in root.children)

    if abs(root_total - total_change) >= 1e-6:
        raise ValueError(
            f"Root drivers don't sum to total change: "
            f"{root_total} vs {total_change}"
        )

    return root


# ---------------------------------------------------------
# Master builder
# ---------------------------------------------------------

def build_business_explanation_tree(
    df: pd.DataFrame,
    current_start,
    current_end,
    prior_start,
    prior_end,
    context_records: list[dict] | None = None,
    dimensions: list[str] | None = None,
    magnitude_gate: float = 500,
    magnitude_floor: float = 250,
    min_child_impact: float = 100,
    min_share_of_parent: float = 0.03,
    concentration_gate: float = 0.60,
    top_n_support: int = 3,
    top_n_counterforce: int = 2,
    max_depth: int = 4,
) -> ExplanationNode | None:
    """
    Builds a recursive additive explanation tree.

    Flow:

        raw data
            ↓
        contribution ledger
            ↓
        total unit change
            ↓
        new / ramping / mature
            ↓
        choose best unused dimension
            ↓
        support + counterforce + residual
            ↓
        attach relevant context
            ↓
        recurse into support AND counterforce

    Key guarantees:

        - contribution attribution happens once
        - null dimension values cannot become recursive children
        - every expanded node's children reconcile to the parent
        - recursion gating is relative to the immediate parent
        - reconciliation checks remain active in production
    """

    if df is None or df.empty:
        return {}

    context_records = context_records or []
    dimensions = dimensions or DEFAULT_DIMENSIONS

    # -----------------------------------------------------
    # Build the additive contribution ledger ONCE.
    #
    # Everything after this point only filters / groups
    # already-assigned contribution values.
    # -----------------------------------------------------

    contributions = build_units_contribution_table(
        df=df,
        current_start=current_start,
        current_end=current_end,
        prior_start=prior_start,
        prior_end=prior_end,
    )

    if contributions.empty:
        return {}


    # -----------------------------------------------------
    # Build root
    # -----------------------------------------------------

    root = build_root_node(
        contributions=contributions,
        context_records=context_records,
        df=df,
        current_end=current_end,
        prior_end=prior_end,
        magnitude_gate=magnitude_gate,
    )

    if root is None:
        return {}

    # -----------------------------------------------------
    # Expand new + ramping + mature branches.
    #
    # Their immediate parent is the business total change.
    # -----------------------------------------------------

    for child in root.children:
        expand_node(
            contributions=contributions,
            node=child,
            parent_impact=root.impact,
            dimensions=dimensions,
            context_records=context_records,
            df=df,
            current_end=current_end,
            prior_end=prior_end,
            top_n_support=top_n_support,
            top_n_counterforce=top_n_counterforce,
            concentration_gate=concentration_gate,
            magnitude_floor=magnitude_floor,
            min_child_impact=min_child_impact,
            min_share_of_parent=min_share_of_parent,
            max_depth=max_depth,
        )

    return root
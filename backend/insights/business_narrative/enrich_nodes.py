from __future__ import annotations

import pandas as pd

from backend.metrics.metric_calculators import calculate_vpo
from backend.metrics.metric_growth_rates import calculate_vpo_3m


def enrich_node(
    node,
    inputs,
    business_rate_current=None,
):
    """
    Build a structured metrics payload for a surfaced explanation-tree node.

    Enrichment should only compute factual metrics.
    It should not decide what the metrics mean or generate narrative language.
    """

    if node.driver_type == "new":
        return _enrich_new(
            node=node,
            df=inputs.df,
            current_start=inputs.current_start,
            current_end=inputs.current_end,
        )

    if node.driver_type == "ramping":
        return _enrich_ramping(
            node,
            df=inputs.df,
        )

    if node.driver_type == "mature":
        return _enrich_mature(
            node=node,
            df=inputs.df,
            current_start=inputs.current_start,
            current_end=inputs.current_end,
            business_rate_current=business_rate_current,
        )

    return {}


# ---------------------------------------------------------------------------
# NEW
# ---------------------------------------------------------------------------

def _enrich_new(
    node,
    df: pd.DataFrame,
    current_start,
    current_end,
) -> dict:
    scoped_df = _filter_to_scope(
        df=df,
        scope=getattr(node, "scope", {}) or {},
    )

    current_df = scoped_df[
        scoped_df["month_year"].between(
            current_start,
            current_end,
        )
    ].copy()

    # Restrict to NEW placements only.
    if "sku_lifecycle" in current_df.columns:
        current_df = current_df[
            current_df["sku_lifecycle"]
            .astype("string")
            .str.lower()
            .eq("new")
        ].copy()

    stores_with_new_placements = _safe_nunique(
        current_df,
        "coded_customer",
    )

    placements_added = _safe_nunique(
        current_df,
        "pod_helper",
    )

    skus_added = _safe_nunique(
        current_df,
        "sku",
    )

    avg_skus_per_store = _avg_unique_per_group(
        df=current_df,
        group_col="coded_customer",
        value_col="sku",
    )

    distribution_type = _new_distribution_type(
        node=node,
        df=df,
        current_start=current_start,
    )

    return {
        "stores_with_new_placements": stores_with_new_placements,
        "placements_added": placements_added,
        "skus_added": skus_added,
        "avg_skus_per_store": avg_skus_per_store,
        "distribution_type": distribution_type,
    }


def _new_distribution_type(
    node,
    df: pd.DataFrame,
    current_start,
) -> str | None:
    """
    Classify how NEW distribution was created for a chain-scoped node.

    Returns:
        - "new_chain"
        - "new_stores_in_chain"
        - "new_placements_in_existing_stores"
        - "mixed_expansion"
    """

    scope = getattr(node, "scope", {}) or {}
    chain = scope.get("chain")

    if (
        not chain
        or "chain" not in df.columns
        or "coded_customer" not in df.columns
    ):
        return None

    chain_df = df[
        df["chain"] == chain
    ].copy()

    # Historical chain activity before the current comparison window.
    prior_chain_df = chain_df[
        chain_df["month_year"] < current_start
    ].copy()

    # If the brand had no activity in this chain before the window,
    # this is a new chain.
    if prior_chain_df.empty:
        return "new_chain"

    # NEW placements created during the current window.
    current_new_df = chain_df[
        chain_df["month_year"] >= current_start
    ].copy()

    if "sku_lifecycle" in current_new_df.columns:
        current_new_df = current_new_df[
            current_new_df["sku_lifecycle"]
            .astype("string")
            .str.lower()
            .eq("new")
        ].copy()

    if current_new_df.empty:
        return None

    current_new_stores = set(
        current_new_df["coded_customer"]
        .dropna()
        .unique()
    )

    prior_stores = set(
        prior_chain_df["coded_customer"]
        .dropna()
        .unique()
    )

    new_store_count = len(
        current_new_stores - prior_stores
    )

    existing_store_count = len(
        current_new_stores & prior_stores
    )

    # All NEW placements are in stores that were new to the brand.
    if (
        new_store_count > 0
        and existing_store_count == 0
    ):
        return "new_stores_in_chain"

    # All NEW placements are inside stores where the brand
    # already had some historical presence.
    if (
        existing_store_count > 0
        and new_store_count == 0
    ):
        return "new_placements_in_existing_stores"

    # Both happened.
    if (
        new_store_count > 0
        and existing_store_count > 0
    ):
        return "mixed_expansion"

    return None


def _sum_units(
    df: pd.DataFrame,
) -> float | None:
    """
    Total units from the NEW placements during the current period.
    """

    if (
        df.empty
        or "units" not in df.columns
    ):
        return None

    units = pd.to_numeric(
        df["units"],
        errors="coerce",
    )

    if units.notna().sum() == 0:
        return None

    return float(
        units.sum()
    )


def _calculate_current_vpo(
    df: pd.DataFrame,
    current_end,
) -> float | None:
    """
    Current L3M VPO for the NEW placements in this node.

    Reuses the existing calculate_vpo_3m() metric rather than
    defining a second velocity calculation here.
    """

    if df.empty:
        return None

    velocity = calculate_vpo_3m(
        df,
        df,
        [],
    )

    if (
        velocity is None
        or velocity.empty
        or "month_year" not in velocity.columns
        or "vpo_3m" not in velocity.columns
    ):
        return None

    current_row = velocity[
        velocity["month_year"] == current_end
    ]

    if current_row.empty:
        return None

    value = current_row.iloc[0]["vpo_3m"]

    if pd.isna(value):
        return None

    return float(value)


# ---------------------------------------------------------------------------
# RAMPING
# ---------------------------------------------------------------------------

def _enrich_ramping(
    node,
    df: pd.DataFrame,
) -> dict:
    scoped_df = _filter_to_scope(
        df=df,
        scope=getattr(node, "scope", {}) or {},
    )

    ramping_df = scoped_df[
        scoped_df["sku_lifecycle"]
        .astype("string")
        .str.lower()
        .eq("ramping")
    ].copy()

    placements_in_cohort = None
    placements_reordered = None

    if not ramping_df.empty:
        atom = [
            "pod_helper",
            "coded_customer",
            "sku",
        ]

        stores_in_cohort = _safe_nunique(ramping_df,"coded_customer")

        per_placement = (
            ramping_df
            .groupby(
                atom,
                dropna=False,
            )["reorder_flag_pod"]
            .sum()
            .reset_index(name="reorders")
        )

        placements_in_cohort = int(len(per_placement))

        placements_reordered = int((per_placement["reorders"] > 0).sum())

    return {
        "reorder_breadth": getattr(
            node,
            "reorder_breadth",
            None,
        ),
        "avg_reorders": getattr(
            node,
            "avg_reorders",
            None,
        ),
        "months_since_launch": getattr(
            node,
            "months_since_launch",
            None,
        ),
        "placements_in_cohort": placements_in_cohort,
        "placements_reordered": placements_reordered,
        "stores_in_cohort": stores_in_cohort,
    }


# ---------------------------------------------------------------------------
# MATURE
# ---------------------------------------------------------------------------

def _enrich_mature(
    node,
    df: pd.DataFrame,
    current_start,
    current_end,
    business_rate_current=None,
) -> dict:
    scoped_df = _filter_to_scope(
        df=df,
        scope=getattr(node, "scope", {}) or {},
    )

    current_df = scoped_df[
        scoped_df["month_year"].between(
            current_start,
            current_end,
        )
    ].copy()

    if "sku_lifecycle" in current_df.columns:
        current_df = current_df[
            current_df["sku_lifecycle"]
            .astype("string")
            .str.lower()
            .eq("mature")
        ].copy()

    stores_in_cohort = _safe_nunique(
        current_df,
        "coded_customer",
    )

    placements_in_cohort = _safe_nunique(
        current_df,
        "pod_helper",
    )

    rate_current = getattr(
        node,
        "rate_current",
        None,
    )

    vs_business_rate = (
        (rate_current / business_rate_current) - 1
        if rate_current is not None
        and business_rate_current not in (None, 0)
        else None
    )

    return {
        "rate_current": rate_current,
        "rate_prior": getattr(
            node,
            "rate_prior",
            None,
        ),
        "rate_change": getattr(
            node,
            "rate_change",
            None,
        ),
        "business_rate_current": business_rate_current,
        "vs_business_rate": vs_business_rate,
        "stores_in_cohort": stores_in_cohort,
        "placements_in_cohort": placements_in_cohort,
    }

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _filter_to_scope(
    df: pd.DataFrame,
    scope: dict,
) -> pd.DataFrame:
    scoped_df = df

    for field, value in scope.items():
        if value is None:
            continue

        if field not in scoped_df.columns:
            continue

        scoped_df = scoped_df[
            scoped_df[field] == value
        ]

    return scoped_df.copy()


def _safe_nunique(
    df: pd.DataFrame,
    column: str,
) -> int | None:
    if column not in df.columns:
        return None

    return int(
        df[column]
        .dropna()
        .nunique()
    )


def _avg_unique_per_group(
    df: pd.DataFrame,
    group_col: str,
    value_col: str,
) -> float | None:
    if (
        group_col not in df.columns
        or value_col not in df.columns
        or df.empty
    ):
        return None

    values = (
        df.dropna(
            subset=[
                group_col,
                value_col,
            ]
        )
        .groupby(group_col)[value_col]
        .nunique()
    )

    if values.empty:
        return None

    return float(
        values.mean()
    )
import pandas as pd


def get_top_concentration(
    df: pd.DataFrame,
    group_col: str,
    entity_col: str = "coded_customer",
    min_pct: float = 0.40,
    min_count: int = 2,
):
    """
    Finds whether one dimension explains a meaningful share of affected stores.
    Example: 6 of 10 struggling stores are tied to one SKU.
    """

    if df.empty or group_col not in df.columns or entity_col not in df.columns:
        return None

    counts = (
        df.dropna(subset=[group_col])
        .groupby(group_col)[entity_col]
        .nunique()
        .sort_values(ascending=False)
    )

    if counts.empty:
        return None

    top_value = counts.index[0]
    top_count = int(counts.iloc[0])
    total_count = int(counts.sum())
    top_pct = top_count / total_count if total_count else 0

    if top_count < min_count or top_pct < min_pct:
        return None

    return {
        "dimension": group_col,
        "value": top_value,
        "count": top_count,
        "total": total_count,
        "pct": top_pct,
        "signal_type": "raw_concentration",
    }


def get_overindexed_concentration(
    affected_df: pd.DataFrame,
    universe_df: pd.DataFrame,
    group_col: str,
    entity_col: str = "coded_customer",
    min_affected_pct: float = 0.40,
    min_overindex_pts: float = 0.15,
    min_index: float = 1.5,
    min_count: int = 2,
    min_outside_universe_count: int = 5,  # 👈 NEW
):
    """
    Finds whether affected stores are overrepresented in one segment
    relative to that segment's share of the relevant universe.

    Example:
    Utah = 60% of struggling stores but only 30% of all chain stores.

    Also avoids false positives when almost all stores are already in that segment.
    """

    if (
        affected_df.empty
        or universe_df.empty
        or group_col not in affected_df.columns
        or group_col not in universe_df.columns
        or entity_col not in affected_df.columns
        or entity_col not in universe_df.columns
    ):
        return None

    affected_counts = (
        affected_df.dropna(subset=[group_col])
        .groupby(group_col)[entity_col]
        .nunique()
    )

    universe_counts = (
        universe_df.dropna(subset=[group_col])
        .groupby(group_col)[entity_col]
        .nunique()
    )

    affected_total = affected_df[entity_col].nunique()
    universe_total = universe_df[entity_col].nunique()

    if affected_total == 0 or universe_total == 0:
        return None

    signals = []

    for value, affected_count in affected_counts.items():
        universe_count = universe_counts.get(value, 0)

        if universe_count == 0:
            continue

        # 👇 NEW: ensure enough stores outside this segment
        outside_universe_count = universe_total - universe_count
        if outside_universe_count < min_outside_universe_count:
            continue

        affected_pct = affected_count / affected_total
        universe_pct = universe_count / universe_total
        overindex_pts = affected_pct - universe_pct
        index = affected_pct / universe_pct if universe_pct else None

        if (
            affected_count >= min_count
            and affected_pct >= min_affected_pct
            and overindex_pts >= min_overindex_pts
            and index is not None
            and index >= min_index
        ):
            signals.append({
                "dimension": group_col,
                "value": value,
                "count": int(affected_count),
                "total": int(affected_total),
                "pct": affected_pct,
                "universe_count": int(universe_count),
                "universe_total": int(universe_total),
                "universe_pct": universe_pct,
                "overindex_pts": overindex_pts,
                "index": index,
                "signal_type": "overindexed_concentration",
            })

    if not signals:
        return None

    return sorted(signals, key=lambda x: x["overindex_pts"], reverse=True)[0]


def get_root_cause_concentration(
    affected_df: pd.DataFrame,
    universe_df: pd.DataFrame | None = None,
    dimensions=None,
    entity_col: str = "coded_customer",
    min_pct: float = 0.40,
    min_count: int = 2,
):
    """
    Checks root-cause-style concentration.

    For now:
    - SKU uses raw concentration among affected stores
    - State uses over-index vs the relevant store universe
    """

    if dimensions is None:
        dimensions = ["sku", "state"]

    signals = []

    for dim in dimensions:
        if dim == "state" and universe_df is not None:
            signal = get_overindexed_concentration(
                affected_df=affected_df,
                universe_df=universe_df,
                group_col=dim,
                entity_col=entity_col,
                min_count=min_count,
            )
        else:
            signal = get_top_concentration(
                df=affected_df,
                group_col=dim,
                entity_col=entity_col,
                min_pct=min_pct,
                min_count=min_count,
            )

        if signal:
            signals.append(signal)

    if not signals:
        return None

    return max(signals, key=lambda x: x.get("overindex_pts", x["pct"]))


def describe_root_cause_signal(signal):
    """
    Turns a concentration signal into plain-English explanation.
    """

    if not signal:
        return (
            "The issue appears spread across the affected stores rather than clearly concentrated "
            "in one SKU or geography."
        )

    dim = signal["dimension"]
    value = signal["value"]
    pct = signal["pct"]
    count = signal["count"]
    total = signal["total"]

    if dim == "sku":
        return (
            f"{value} accounts for {pct:.0%} of the affected stores "
            f"({count} of {total}), suggesting the issue may be SKU-specific."
        )

    if dim == "state":
        if signal.get("signal_type") == "overindexed_concentration":
            universe_pct = signal["universe_pct"]
            universe_count = signal["universe_count"]
            universe_total = signal["universe_total"]

            return (
                f"{value} looks overrepresented: it accounts for {pct:.0%} of affected stores "
                f"({count} of {total}), compared with {universe_pct:.0%} of this chain's total store base "
                f"({universe_count} of {universe_total})."
            )

        return None

    return (
        f"The issue is concentrated in {value} for {dim}, accounting for "
        f"{pct:.0%} of affected stores ({count} of {total})."
    )


def decompose_units_growth(
    units_current: float,
    units_prior: float,
    stores_current: float,
    stores_prior: float,
    vpo_current: float,
    vpo_prior: float,
):
    values = [
        units_current,
        units_prior,
        stores_current,
        stores_prior,
        vpo_current,
        vpo_prior,
    ]

    if any(pd.isna(v) for v in values):
        return None

    total_change = units_current - units_prior

    if total_change == 0:
        return None

    distribution_impact = (stores_current - stores_prior) * vpo_prior
    velocity_impact = (vpo_current - vpo_prior) * stores_prior
    interaction_impact = total_change - distribution_impact - velocity_impact

    distribution_share = distribution_impact / total_change
    velocity_share = velocity_impact / total_change
    interaction_share = interaction_impact / total_change

    primary_driver = (
        "distribution"
        if abs(distribution_share) >= abs(velocity_share)
        else "velocity"
    )

    return {
        "total_change": total_change,
        "distribution_impact": distribution_impact,
        "velocity_impact": velocity_impact,
        "interaction_impact": interaction_impact,
        "distribution_share": distribution_share,
        "velocity_share": velocity_share,
        "interaction_share": interaction_share,
        "primary_driver": primary_driver,
    }


def describe_growth_decomposition(decomp):
    if not decomp:
        return None

    dist_share = decomp["distribution_share"]
    vel_share = decomp["velocity_share"]
    primary = decomp["primary_driver"]

    if primary == "distribution" and abs(dist_share) >= 0.60:
        return (
            f"The change was primarily driven by distribution, which accounted for "
            f"about {dist_share:.0%} of the unit change."
        )

    if primary == "velocity" and abs(vel_share) >= 0.60:
        return (
            f"The change was primarily driven by velocity, which accounted for "
            f"about {vel_share:.0%} of the unit change."
        )

    return (
        "The change was driven by a mix of distribution and velocity rather than "
        "one clear driver."
    )
import pandas as pd
from backend.metrics.metric_calculators import calculate_units
from backend.metrics.metric_growth_rates import add_additive_metric_3m, calculate_active_pods_3m_opportunities, calculate_vpo_3m
from backend.metrics.metric_helpers import clean_group_cols
from backend.insights.insights_helper import get_last_full_month


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
    min_overindex_pts: float = 0.1,
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
    Finds the strongest root-cause signal.

    If universe_df is provided:
        → use over-index logic for all dimensions (sku, state)

    If not:
        → fallback to raw concentration
    """

    if dimensions is None:
        dimensions = ["sku", "state"]

    signals = []

    for dim in dimensions:
        # ✅ Use over-index logic when possible
        if universe_df is not None:
            signal = get_overindexed_concentration(
                affected_df=affected_df,
                universe_df=universe_df,
                group_col=dim,
                entity_col=entity_col,
                min_count=min_count,
            )
        else:
            # fallback (shouldn't really happen in your case)
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

    # pick strongest signal
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

def calculate_units_growth_decomposition_3m(
    df_filtered,
    df_full,
    group_cols=None,
    selected_years=None,
    selected_months=None,
    include_current_month=False,
):
    group_cols = clean_group_cols(group_cols)

    units = calculate_units(
        df_filtered,
        group_cols=group_cols,
    )

    units_3m = add_additive_metric_3m(
        units,
        group_cols,
        "units",
    )

    active_pods_3m = calculate_active_pods_3m_opportunities(
        df_filtered=df_filtered,
        df_full=df_full,
        group_cols=group_cols,
        selected_years=selected_years,
        selected_months=selected_months,
        include_current_month=include_current_month,
    )

    vpo_3m = calculate_vpo_3m(
        df_filtered=df_filtered,
        df_full=df_full,
        group_cols=group_cols,
        selected_years=selected_years,
        selected_months=selected_months,
        #include_current_month=include_current_month,
    )

    result = (
        units_3m
        .merge(
            active_pods_3m,
            on=group_cols,
            how="left",
        )
        .merge(
            vpo_3m,
            on=group_cols,
            how="left",
        )
    )

    if result.empty:
        return result
    
    if include_current_month:
        latest_month = pd.Period(pd.Timestamp.today(), freq="M")
    else:
        latest_month = get_last_full_month()

    current = (
        result[result["month_year"] == latest_month]
        .copy()
        .rename(columns={
            "units_3m": "units_current",
            "active_pods_3m_opportunities": "active_pods_current",
            "vpo_3m": "vpo_current",
        })
    )

    prior_month = latest_month - 3

    prior = (
        result[result["month_year"] == prior_month]
        .copy()
        .rename(columns={
            "units_3m": "units_prior",
            "active_pods_3m_opportunities": "active_pods_prior",
            "vpo_3m": "vpo_prior",
        })
    )

    non_time_cols = [c for c in group_cols if c != "month_year"]

    current = current.drop(columns=["month_year"], errors="ignore")
    prior = prior.drop(columns=["month_year"], errors="ignore")

    prior_cols = non_time_cols + [
        "units_prior",
        "active_pods_prior",
        "vpo_prior",
    ]

    if non_time_cols:
        result = current.merge(
            prior[prior_cols],
            on=non_time_cols,
            how="left",
        )
    else:
        current["_merge_key"] = 1
        prior["_merge_key"] = 1

        result = current.merge(
            prior[["_merge_key"] + prior_cols],
            on="_merge_key",
            how="left",
        ).drop(columns=["_merge_key"])
        
    decomps = result.apply(
        lambda row: decompose_units_growth(
            units_current=row["units_current"],
            units_prior=row["units_prior"],
            active_pods_current=row["active_pods_current"],
            active_pods_prior=row["active_pods_prior"],
            vpo_current=row["vpo_current"],
            vpo_prior=row["vpo_prior"],
            weeks_per_month=4,
        ) or {},
        axis=1,
    )

    decomp_df = pd.json_normalize(decomps)

    result = pd.concat(
        [
            result.reset_index(drop=True),
            decomp_df.reset_index(drop=True),
        ],
        axis=1,
    )

    return result

def decompose_units_growth(
    units_current: float,
    units_prior: float,
    active_pods_current: float,
    active_pods_prior: float,
    vpo_current: float,
    vpo_prior: float,
    weeks_per_month: int = 4,
):
    values = [
        units_current,
        units_prior,
        active_pods_current,
        active_pods_prior,
        vpo_current,
        vpo_prior,
    ]

    if any(pd.isna(v) for v in values):
        return None

    total_change = units_current - units_prior

    if total_change == 0:
        return None

    # Interaction is intentionally folded into distribution.
    # This says: how many units changed because we had more/fewer
    # active POD opportunities, valued at current velocity.
    distribution_impact = (
        (active_pods_current - active_pods_prior)
        * vpo_current
        * weeks_per_month
    )

    # This says: how many units changed because existing POD opportunities
    # became more/less productive.
    velocity_impact = (
        (vpo_current - vpo_prior)
        * active_pods_prior
        * weeks_per_month
    )

    distribution_share = distribution_impact / total_change
    velocity_share = velocity_impact / total_change

    primary_driver = (
        "distribution"
        if abs(distribution_share) >= abs(velocity_share)
        else "velocity"
    )

    return {
        "total_change": total_change,
        "distribution_impact": distribution_impact,
        "velocity_impact": velocity_impact,
        "distribution_share": distribution_share,
        "velocity_share": velocity_share,
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
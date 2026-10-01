import pandas as pd
import numpy as np
from backend.metrics.metric_callers import compare_metric, calculate_metric, calculate_monthly_metric
from backend.metrics.metric_helpers import resolve_period_comparison, filter_to_period, get_period_months


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
def calculate_units_growth_decomposition(
    df,
    df_full,
    active_pods_df,
    group_cols=None,
    end_month=None,
):
    if group_cols is None:
        group_cols = []
    elif isinstance(group_cols, str):
        group_cols = [group_cols]
    units = compare_metric(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_df,
        metric_name="units",
        period="L3M",
        comparison="PP",
        group_cols=group_cols,
        end_month=end_month,
    )
    opportunities = compare_metric(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_df,
        metric_name="active_pod_opportunities",
        period="L3M",
        comparison="PP",
        group_cols=group_cols,
        end_month=end_month,
    )
    velocity = compare_metric(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_df,
        metric_name="velocity",
        period="L3M",
        comparison="PP",
        group_cols=group_cols,
        end_month=end_month,
    )
    def prepare_metric(result, prefix):
        keep_cols = group_cols + [
            "value_current",
            "value_comparison",
            "abs_change",
            "pct_change",
            "comparison_eligible",
        ]

        return result[keep_cols].copy().rename(
            columns={
                "value_current": f"{prefix}_current",
                "value_comparison": f"{prefix}_comparison",
                "abs_change": f"{prefix}_abs_change",
                "pct_change": f"{prefix}_pct_change",
                "comparison_eligible": f"{prefix}_comparison_eligible",
            }
        )
    units = prepare_metric(units, "units")
    opportunities = prepare_metric(
        opportunities,
        "active_pod_opportunities",
    )
    velocity = prepare_metric(velocity, "vpo")
    frames = [
        units,
        opportunities,
        velocity,
    ]
    if group_cols:
        result = frames[0]
        for frame in frames[1:]:
            result = result.merge(
                frame,
                on=group_cols,
                how="left",
            )
    else:
        result = pd.concat(
            [
                frame.reset_index(drop=True)
                for frame in frames
            ],
            axis=1,
        )
    if result.empty:
        return result
    decomps = result.apply(
        lambda row: decompose_units_growth(
            units_current=row["units_current"],
            units_prior=row["units_comparison"],
            active_pod_opportunities_current=row[
                "active_pod_opportunities_current"
            ],
            active_pod_opportunities_prior=row[
                "active_pod_opportunities_comparison"
            ],
            vpo_current=row["vpo_current"],
            vpo_prior=row["vpo_comparison"],
            weeks_per_month=4,
        ) or {},
        axis=1,
    )
    decomp_df = pd.json_normalize(decomps)
    return pd.concat(
        [
            result.reset_index(drop=True),
            decomp_df.reset_index(drop=True),
        ],
        axis=1,
    )

def decompose_units_growth(
    units_current: float,
    units_prior: float,
    active_pod_opportunities_current: float,
    active_pod_opportunities_prior: float,
    vpo_current: float,
    vpo_prior: float,
    weeks_per_month: int = 4,
):
    values = [
        units_current,
        units_prior,
        active_pod_opportunities_current,
        active_pod_opportunities_prior,
        vpo_current,
        vpo_prior,
    ]
    if any(pd.isna(v) for v in values):
        return None
    total_change = units_current - units_prior
    if total_change == 0:
        return None
    # Interaction is intentionally folded into distribution.
    # active_pod_opportunities represents POD-months, so VPO * 4
    # converts each opportunity back into unit impact.
    distribution_impact = (
        (
            active_pod_opportunities_current
            - active_pod_opportunities_prior
        )
        * vpo_current
        * weeks_per_month
    )
    velocity_impact = (
        (vpo_current - vpo_prior)
        * active_pod_opportunities_prior
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
def analyze_fill_rate_impact(
    sales_df,
    fill_rate_df,
    active_pods_df,
    period="L3M",
    comparison="PP",
    group_cols=None,
    end_month=None,
):
    """
    Analyze how ordering and fill rate contributed to a change in sales velocity.

    Period-level output compares:
        - sales velocity
        - order velocity
        - fill rate
        - fill-rate coverage
        - covered sales velocity

    Monthly output provides a timeline of:
        - sales velocity
        - order velocity
        - fill rate

    The monthly timeline is intended to support sequencing analysis
    (for example, whether fill rate weakened before ordering weakened)
    without making a causal determination itself.

    Returns
    -------
    period_result : pd.DataFrame
        One row per group with current vs comparison metrics.

    monthly_timeline : pd.DataFrame
        One row per group x month with monthly sales velocity,
        order velocity, and fill rate.
    """

    if group_cols is None:
        group_cols = []
    elif isinstance(group_cols, str):
        group_cols = [group_cols]

    sales_df = sales_df.copy()
    fill_rate_df = fill_rate_df.copy()
    active_pods_df = active_pods_df.copy()

    sales_df["month_year"] = pd.PeriodIndex(
        sales_df["month_year"],
        freq="M",
    )

    fill_rate_df["month_year"] = pd.PeriodIndex(
        fill_rate_df["month_year"],
        freq="M",
    )

    active_pods_df["month_year"] = pd.PeriodIndex(
        active_pods_df["month_year"],
        freq="M",
    )

    # =================================================
    # RESOLVE ANALYSIS PERIOD
    # =================================================

    current_period, comparison_period = resolve_period_comparison(
        period=period,
        comparison=comparison,
        year=None,
        end_month=end_month,
    )

    current_start = current_period["start"]
    current_end = current_period["end"]

    comparison_start = comparison_period["start"]
    comparison_end = comparison_period["end"]

    # Active PODs intentionally extend into future months for
    # forecasting. Historical diagnostics should only use the
    # POD universe through the analysis endpoint.
    active_pods_df = active_pods_df[
        active_pods_df["month_year"] <= current_end
    ].copy()

    current_months = get_period_months(
        current_start,
        current_end,
    )

    comparison_months = get_period_months(
        comparison_start,
        comparison_end,
    )

    # =================================================
    # PERIOD-LEVEL CANONICAL METRICS
    # =================================================

    velocity = compare_metric(
        df=sales_df,
        df_full=sales_df,
        active_pods_df=active_pods_df,
        metric_name="velocity",
        period=period,
        comparison=comparison,
        group_cols=group_cols,
        end_month=end_month,
    )

    order_velocity = compare_metric(
        df=fill_rate_df,
        df_full=fill_rate_df,
        active_pods_df=active_pods_df,
        metric_name="order_velocity",
        period=period,
        comparison=comparison,
        group_cols=group_cols,
        end_month=end_month,
    )

    fill_rate = compare_metric(
        df=fill_rate_df,
        df_full=fill_rate_df,
        active_pods_df=active_pods_df,
        metric_name="fill_rate",
        period=period,
        comparison=comparison,
        group_cols=group_cols,
        end_month=end_month,
    )

    def prepare_metric(result, prefix):
        keep_cols = group_cols + [
            "value_current",
            "value_comparison",
            "abs_change",
            "pct_change",
            "comparison_eligible",
        ]

        return result[keep_cols].copy().rename(
            columns={
                "value_current": f"{prefix}_current",
                "value_comparison": f"{prefix}_comparison",
                "abs_change": f"{prefix}_abs_change",
                "pct_change": f"{prefix}_pct_change",
                "comparison_eligible": f"{prefix}_comparison_eligible",
            }
        )

    velocity = prepare_metric(
        velocity,
        "velocity",
    )

    order_velocity = prepare_metric(
        order_velocity,
        "order_velocity",
    )

    fill_rate = prepare_metric(
        fill_rate,
        "fill_rate",
    )

    # =================================================
    # RAW PERIOD DATA
    # =================================================

    sales_current = filter_to_period(
        sales_df,
        current_start,
        current_end,
    )

    sales_comparison = filter_to_period(
        sales_df,
        comparison_start,
        comparison_end,
    )

    fill_current = filter_to_period(
        fill_rate_df,
        current_start,
        current_end,
    )

    fill_comparison = filter_to_period(
        fill_rate_df,
        comparison_start,
        comparison_end,
    )

    # =================================================
    # ACTIVE / COVERED POD OPPORTUNITIES
    # =================================================

    def pod_math(months, suffix):
        active = active_pods_df[
            active_pods_df["month_year"].isin(months)
        ].copy()

        covered = active[
            active["has_fill_rate_data"]
        ].copy()

        if group_cols:
            total = (
                active
                .groupby(
                    group_cols,
                    dropna=False,
                )
                .size()
                .reset_index(
                    name=f"pod_months_{suffix}"
                )
            )

            covered_counts = (
                covered
                .groupby(
                    group_cols,
                    dropna=False,
                )
                .size()
                .reset_index(
                    name=f"covered_pod_months_{suffix}"
                )
            )

            result = total.merge(
                covered_counts,
                on=group_cols,
                how="left",
            )

        else:
            result = pd.DataFrame(
                {
                    f"pod_months_{suffix}": [
                        len(active)
                    ],
                    f"covered_pod_months_{suffix}": [
                        len(covered)
                    ],
                }
            )

        result[f"covered_pod_months_{suffix}"] = (
            result[f"covered_pod_months_{suffix}"]
            .fillna(0)
        )

        result[f"coverage_{suffix}"] = (
            result[f"covered_pod_months_{suffix}"]
            / result[f"pod_months_{suffix}"].replace(
                0,
                pd.NA,
            )
        )

        return result

    pods_current = pod_math(
        current_months,
        "current",
    )

    pods_comparison = pod_math(
        comparison_months,
        "comparison",
    )

    # =================================================
    # SALES UNITS
    # =================================================

    def sales_units_math(df, suffix):
        if group_cols:
            return (
                df
                .groupby(
                    group_cols,
                    dropna=False,
                    as_index=False,
                )
                .agg(
                    **{
                        f"units_{suffix}": (
                            "units",
                            "sum",
                        )
                    }
                )
            )

        return pd.DataFrame(
            {
                f"units_{suffix}": [
                    df["units"].sum()
                ]
            }
        )

    units_current = sales_units_math(
        sales_current,
        "current",
    )

    units_comparison = sales_units_math(
        sales_comparison,
        "comparison",
    )

    # =================================================
    # COVERED SALES UNITS
    # =================================================

    def covered_sales_math(
        sales_period_df,
        months,
        suffix,
    ):
        covered_keys = (
            active_pods_df[
                active_pods_df["month_year"].isin(months)
                & active_pods_df["has_fill_rate_data"]
            ][
                [
                    "month_year",
                    "pod_helper",
                ]
            ]
            .drop_duplicates()
        )

        covered_sales = sales_period_df.merge(
            covered_keys,
            on=[
                "month_year",
                "pod_helper",
            ],
            how="inner",
        )

        if group_cols:
            return (
                covered_sales
                .groupby(
                    group_cols,
                    dropna=False,
                    as_index=False,
                )
                .agg(
                    **{
                        f"covered_units_{suffix}": (
                            "units",
                            "sum",
                        )
                    }
                )
            )

        return pd.DataFrame(
            {
                f"covered_units_{suffix}": [
                    covered_sales["units"].sum()
                ]
            }
        )

    covered_units_current = covered_sales_math(
        sales_current,
        current_months,
        "current",
    )

    covered_units_comparison = covered_sales_math(
        sales_comparison,
        comparison_months,
        "comparison",
    )

    # =================================================
    # ORDER / FILL NUMERATORS
    # =================================================

    def fill_math(df, suffix):
        if group_cols:
            return (
                df
                .groupby(
                    group_cols,
                    dropna=False,
                    as_index=False,
                )
                .agg(
                    **{
                        f"ordered_units_{suffix}": (
                            "ordered_units",
                            "sum",
                        ),
                        f"ordered_cases_{suffix}": (
                            "ordered_cases",
                            "sum",
                        ),
                        f"shipped_cases_{suffix}": (
                            "shipped_cases",
                            "sum",
                        ),
                    }
                )
            )

        return pd.DataFrame(
            {
                f"ordered_units_{suffix}": [
                    df["ordered_units"].sum()
                ],
                f"ordered_cases_{suffix}": [
                    df["ordered_cases"].sum()
                ],
                f"shipped_cases_{suffix}": [
                    df["shipped_cases"].sum()
                ],
            }
        )

    fill_raw_current = fill_math(
        fill_current,
        "current",
    )

    fill_raw_comparison = fill_math(
        fill_comparison,
        "comparison",
    )

    # =================================================
    # MERGE PERIOD RESULTS
    # =================================================

    frames = [
        velocity,
        order_velocity,
        fill_rate,
        pods_current,
        pods_comparison,
        units_current,
        units_comparison,
        covered_units_current,
        covered_units_comparison,
        fill_raw_current,
        fill_raw_comparison,
    ]

    if group_cols:
        period_result = frames[0]

        for frame in frames[1:]:
            period_result = period_result.merge(
                frame,
                on=group_cols,
                how="left",
            )

    else:
        period_result = pd.concat(
            [
                frame.reset_index(drop=True)
                for frame in frames
            ],
            axis=1,
        )

    # =================================================
    # COVERED VELOCITY
    # =================================================

    period_result["covered_velocity_current"] = (
        period_result["covered_units_current"]
        / period_result[
            "covered_pod_months_current"
        ].replace(0, pd.NA)
        / 4
    )

    period_result["covered_velocity_comparison"] = (
        period_result["covered_units_comparison"]
        / period_result[
            "covered_pod_months_comparison"
        ].replace(0, pd.NA)
        / 4
    )

    period_result["covered_velocity_abs_change"] = (
        period_result["covered_velocity_current"]
        - period_result["covered_velocity_comparison"]
    )

    period_result["covered_velocity_pct_change"] = (
        period_result["covered_velocity_abs_change"]
        / period_result[
            "covered_velocity_comparison"
        ].replace(0, pd.NA)
    )

    # =================================================
    # ORDER VS ACTUAL VELOCITY
    # =================================================

    period_result["order_vs_covered_velocity_gap"] = (
        period_result["order_velocity_pct_change"]
        - period_result["covered_velocity_pct_change"]
    )

    # =================================================
    # MONTHLY TIMELINE
    # =================================================

    monthly_velocity = calculate_monthly_metric(
        metric_name="velocity",
        df_filtered=sales_df,
        active_pods_df=active_pods_df,
        group_cols=group_cols,
    ).rename(
        columns={
            "value": "velocity",
        }
    )

    monthly_order_velocity = calculate_monthly_metric(
        metric_name="order_velocity",
        df_filtered=fill_rate_df,
        active_pods_df=active_pods_df,
        group_cols=group_cols,
    ).rename(
        columns={
            "value": "order_velocity",
        }
    )

    monthly_fill_rate = calculate_monthly_metric(
        metric_name="fill_rate",
        df_filtered=fill_rate_df,
        active_pods_df=active_pods_df,
        group_cols=group_cols,
    ).rename(
        columns={
            "value": "fill_rate",
        }
    )

    monthly_keys = group_cols + [
        "month_year",
    ]

    monthly_timeline = monthly_velocity.merge(
        monthly_order_velocity,
        on=monthly_keys,
        how="outer",
    )

    monthly_timeline = monthly_timeline.merge(
        monthly_fill_rate,
        on=monthly_keys,
        how="outer",
    )

    # Extra safeguard: the timeline itself should never
    # extend beyond the requested analysis endpoint.
    monthly_timeline = monthly_timeline[
        monthly_timeline["month_year"] <= current_end
    ].copy()

    monthly_timeline = (
        monthly_timeline
        .sort_values(monthly_keys)
        .reset_index(drop=True)
    )

    # =================================================
    # MONTH-OVER-MONTH CHANGES
    # =================================================

    metric_cols = [
        "velocity",
        "order_velocity",
        "fill_rate",
    ]

    if group_cols:
        for col in metric_cols:
            monthly_timeline[
                f"{col}_mom_abs_change"
            ] = (
                monthly_timeline
                .groupby(
                    group_cols,
                    dropna=False,
                )[col]
                .diff()
            )

            monthly_timeline[
                f"{col}_mom_pct_change"
            ] = (
                monthly_timeline
                .groupby(
                    group_cols,
                    dropna=False,
                )[col]
                .pct_change(
                    fill_method=None
                )
            )

    else:
        for col in metric_cols:
            monthly_timeline[
                f"{col}_mom_abs_change"
            ] = (
                monthly_timeline[col]
                .diff()
            )

            monthly_timeline[
                f"{col}_mom_pct_change"
            ] = (
                monthly_timeline[col]
                .pct_change(
                    fill_method=None
                )
            )

    return period_result, monthly_timeline

def diagnose_velocity_change(
    velocity_current,
    velocity_prior,
    order_velocity_current,
    order_velocity_prior,
    fill_rate_current,
    fill_rate_prior,
):
    """
    Diagnose whether a sales velocity change is meaningfully supported by:

    - a change in retailer ordering
    - a change in distributor fulfillment
    - both
    - neither

    A signal must:
    1. Move in the same direction as sales velocity.
    2. Have a relative magnitude of at least 20% of the
       sales velocity movement.

    Relative magnitude is NOT causal attribution. It simply measures
    how large the signal's percentage movement is relative to the
    observed sales velocity percentage movement.
    """

    MIN_RELATIVE_MAGNITUDE = 0.20

    # -----------------------------------------------------
    # Validate inputs
    # -----------------------------------------------------

    values = [
        velocity_current,
        velocity_prior,
        order_velocity_current,
        order_velocity_prior,
        fill_rate_current,
        fill_rate_prior,
    ]

    if any(pd.isna(v) for v in values):
        return None

    # -----------------------------------------------------
    # Calculate changes
    # -----------------------------------------------------

    velocity_change = velocity_current - velocity_prior
    order_velocity_change = (
        order_velocity_current - order_velocity_prior
    )
    fill_rate_change = fill_rate_current - fill_rate_prior

    velocity_pct_change = (
        velocity_change / velocity_prior
        if velocity_prior != 0
        else np.nan
    )

    order_velocity_pct_change = (
        order_velocity_change / order_velocity_prior
        if order_velocity_prior != 0
        else np.nan
    )

    fill_rate_pct_change = (
        fill_rate_change / fill_rate_prior
        if fill_rate_prior != 0
        else np.nan
    )

    # -----------------------------------------------------
    # Directional relationship to sales velocity
    # -----------------------------------------------------

    def get_relationship(signal_change, sales_change):
        if signal_change == 0 or sales_change == 0:
            return "neutral"

        if signal_change * sales_change > 0:
            return "support"

        return "counterforce"

    ordering_relationship = get_relationship(
        order_velocity_change,
        velocity_change,
    )

    fulfillment_relationship = get_relationship(
        fill_rate_change,
        velocity_change,
    )

    # -----------------------------------------------------
    # Relative magnitude vs sales velocity change
    #
    # Example:
    # sales -40%, orders -30% -> 0.75
    # sales -40%, fill   -4%  -> 0.10
    #
    # This is NOT causal attribution.
    # -----------------------------------------------------

    if (
        pd.notna(velocity_pct_change)
        and velocity_pct_change != 0
    ):
        ordering_relative_magnitude = (
            abs(order_velocity_pct_change)
            / abs(velocity_pct_change)
            if pd.notna(order_velocity_pct_change)
            else np.nan
        )

        fulfillment_relative_magnitude = (
            abs(fill_rate_pct_change)
            / abs(velocity_pct_change)
            if pd.notna(fill_rate_pct_change)
            else np.nan
        )

    else:
        ordering_relative_magnitude = np.nan
        fulfillment_relative_magnitude = np.nan

    # -----------------------------------------------------
    # Meaningful supporting signals
    #
    # A signal only counts as a driver if:
    #   1. it supports the direction of the sales movement
    #   2. its movement is >= 20% of the sales movement
    # -----------------------------------------------------

    ordering_meaningful = (
        ordering_relationship == "support"
        and pd.notna(ordering_relative_magnitude)
        and ordering_relative_magnitude >= MIN_RELATIVE_MAGNITUDE
    )

    fulfillment_meaningful = (
        fulfillment_relationship == "support"
        and pd.notna(fulfillment_relative_magnitude)
        and fulfillment_relative_magnitude >= MIN_RELATIVE_MAGNITUDE
    )

    # -----------------------------------------------------
    # Primary driver
    # -----------------------------------------------------

    if velocity_change == 0:
        primary_driver = "no_change"

    elif ordering_meaningful and fulfillment_meaningful:
        primary_driver = "ordering_and_fulfillment"

    elif ordering_meaningful:
        primary_driver = "ordering"

    elif fulfillment_meaningful:
        primary_driver = "fulfillment"

    else:
        primary_driver = "unexplained"

    # -----------------------------------------------------
    # Return structured diagnostic
    # -----------------------------------------------------

    return {
        "velocity_change": velocity_change,
        "velocity_pct_change": velocity_pct_change,

        "order_velocity_change": order_velocity_change,
        "order_velocity_pct_change": order_velocity_pct_change,
        "ordering_relationship": ordering_relationship,
        "ordering_relative_magnitude": ordering_relative_magnitude,
        "ordering_meaningful": ordering_meaningful,

        "fill_rate_change": fill_rate_change,
        "fill_rate_pct_change": fill_rate_pct_change,
        "fulfillment_relationship": fulfillment_relationship,
        "fulfillment_relative_magnitude": fulfillment_relative_magnitude,
        "fulfillment_meaningful": fulfillment_meaningful,

        "primary_driver": primary_driver,
    }


def build_fill_rate_diagnostics(
    features_df: pd.DataFrame,
    active_pods_df: pd.DataFrame,
    fill_rate_df: pd.DataFrame,
    period: str = "L3M",
    comparison: str = "PP",
    end_month: str | None = None,
):
    """
    Build fill-rate diagnostics independently at:

    1. Chain × SKU
    2. Distributor × Chain × DC × SKU

    No data loading and no inventory assessment happen here.
    This function is purely data-in / data-out.

    Returns:
        {
            "chain_sku": DataFrame,
            "chain_sku_monthly": DataFrame,
            "dc_sku": DataFrame,
            "dc_sku_monthly": DataFrame,
        }
    """

    # =====================================================
    # HELPER: APPLY VELOCITY DIAGNOSTIC
    # =====================================================

    def add_diagnostics(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df.copy()

        diagnostics = df.apply(
            lambda row: (
                diagnose_velocity_change(
                    velocity_current=row.get("velocity_current"),
                    velocity_prior=row.get("velocity_comparison"),
                    order_velocity_current=row.get(
                        "order_velocity_current"
                    ),
                    order_velocity_prior=row.get(
                        "order_velocity_comparison"
                    ),
                    fill_rate_current=row.get("fill_rate_current"),
                    fill_rate_prior=row.get("fill_rate_comparison"),
                )
                if (
                    row.get("velocity_comparison_eligible", False)
                    and row.get("order_velocity_comparison_eligible", False)
                    and row.get("fill_rate_comparison_eligible", False)
                )
                else None
            ),
            axis=1,
        )

        diagnostic_df = pd.json_normalize(
            [
                result if result is not None else {}
                for result in diagnostics
            ]
        )

        expected_diagnostic_cols = [
            "velocity_change",
            "velocity_pct_change",
            "order_velocity_change",
            "order_velocity_pct_change",
            "ordering_relationship",
            "ordering_relative_magnitude",
            "fill_rate_change",
            "fill_rate_pct_change",
            "fulfillment_relationship",
            "fulfillment_relative_magnitude",
            "primary_driver",
        ]

        for col in expected_diagnostic_cols:
            if col not in diagnostic_df.columns:
                diagnostic_df[col] = pd.NA

        # Prevent collisions with columns already produced by
        # analyze_fill_rate_impact.
        diagnostic_df = diagnostic_df.rename(
            columns={
                "velocity_change":
                    "diagnostic_velocity_change",
                "velocity_pct_change":
                    "diagnostic_velocity_pct_change",
                "order_velocity_change":
                    "diagnostic_order_velocity_change",
                "order_velocity_pct_change":
                    "diagnostic_order_velocity_pct_change",
                "fill_rate_change":
                    "diagnostic_fill_rate_change",
                "fill_rate_pct_change":
                    "diagnostic_fill_rate_pct_change",
            }
        )

        return pd.concat(
            [
                df.reset_index(drop=True),
                diagnostic_df.reset_index(drop=True),
            ],
            axis=1,
        )

        # =====================================================
    # CHAIN × SKU
    # =====================================================

    chain_keys = ["chain", "sku"]

    # Preferred comparison: L3M vs prior 3M
    chain_l3m, chain_monthly_timeline = analyze_fill_rate_impact(
        sales_df=features_df,
        fill_rate_df=fill_rate_df,
        active_pods_df=active_pods_df,
        period="L3M",
        comparison="PP",
        group_cols=chain_keys,
        end_month=end_month,
    )

    chain_l3m = chain_l3m.copy()
    chain_l3m["diagnostic_period"] = "L3M"
    chain_l3m["diagnostic_comparison"] = "PP"

    chain_l3m_eligible = (
        chain_l3m["velocity_comparison_eligible"].fillna(False)
        & chain_l3m["order_velocity_comparison_eligible"].fillna(False)
        & chain_l3m["fill_rate_comparison_eligible"].fillna(False)
    )

    # Fallback comparison: L2M vs prior 2M
    chain_l2m, _ = analyze_fill_rate_impact(
        sales_df=features_df,
        fill_rate_df=fill_rate_df,
        active_pods_df=active_pods_df,
        period="L2M",
        comparison="PP",
        group_cols=chain_keys,
        end_month=end_month,
    )

    chain_l2m = chain_l2m.copy()
    chain_l2m["diagnostic_period"] = "L2M"
    chain_l2m["diagnostic_comparison"] = "PP"

    chain_l2m_eligible = (
        chain_l2m["velocity_comparison_eligible"].fillna(False)
        & chain_l2m["order_velocity_comparison_eligible"].fillna(False)
        & chain_l2m["fill_rate_comparison_eligible"].fillna(False)
    )

   # Keep valid L3M rows as the preferred comparison.
    chain_l3m_valid = chain_l3m[chain_l3m_eligible].copy()
    chain_l3m_invalid = chain_l3m[~chain_l3m_eligible].copy()

    # L2M is only allowed as a fallback for rows where L3M failed.
    chain_l2m_valid = chain_l2m[chain_l2m_eligible].copy()

    chain_l2m_fallback = chain_l2m_valid.merge(
        chain_l3m_invalid[chain_keys].drop_duplicates(),
        on=chain_keys,
        how="inner",
    )

    # Keep failed L3M rows that also have no valid L2M comparison.
    # They remain in diagnostics, but add_diagnostics() will not assign a driver.
    chain_no_fallback = chain_l3m_invalid.merge(
        chain_l2m_fallback[chain_keys].assign(_has_fallback=True),
        on=chain_keys,
        how="left",
    )

    chain_no_fallback = chain_no_fallback[
        chain_no_fallback["_has_fallback"].isna()
    ].drop(columns="_has_fallback")

    chain_no_fallback["diagnostic_period"] = pd.NA
    chain_no_fallback["diagnostic_comparison"] = pd.NA

    chain_result = pd.concat(
        [
            chain_l3m_valid,
            chain_l2m_fallback,
            chain_no_fallback,
        ],
        ignore_index=True,
    )

    chain_sku_diagnostics = add_diagnostics(chain_result)


    # =====================================================
    # DISTRIBUTOR × CHAIN × DC × SKU
    # =====================================================

    dc_keys = ["distributor", "chain", "dc", "sku"]

    # Preferred comparison: L3M vs prior 3M
    dc_l3m, dc_monthly_timeline = analyze_fill_rate_impact(
        sales_df=features_df,
        fill_rate_df=fill_rate_df,
        active_pods_df=active_pods_df,
        period="L3M",
        comparison="PP",
        group_cols=dc_keys,
        end_month=end_month,
    )

    dc_l3m = dc_l3m.copy()
    dc_l3m["diagnostic_period"] = "L3M"
    dc_l3m["diagnostic_comparison"] = "PP"

    dc_l3m_eligible = (
        dc_l3m["velocity_comparison_eligible"].fillna(False)
        & dc_l3m["order_velocity_comparison_eligible"].fillna(False)
        & dc_l3m["fill_rate_comparison_eligible"].fillna(False)
    )

    # Fallback comparison: L2M vs prior 2M
    dc_l2m, _ = analyze_fill_rate_impact(
        sales_df=features_df,
        fill_rate_df=fill_rate_df,
        active_pods_df=active_pods_df,
        period="L2M",
        comparison="PP",
        group_cols=dc_keys,
        end_month=end_month,
    )

    dc_l2m = dc_l2m.copy()
    dc_l2m["diagnostic_period"] = "L2M"
    dc_l2m["diagnostic_comparison"] = "PP"

    dc_l2m_eligible = (
        dc_l2m["velocity_comparison_eligible"].fillna(False)
        & dc_l2m["order_velocity_comparison_eligible"].fillna(False)
        & dc_l2m["fill_rate_comparison_eligible"].fillna(False)
    )

    # Only valid L2M rows are allowed to replace failed L3M rows.
    dc_l2m_valid = dc_l2m[dc_l2m_eligible].copy()

    dc_result = dc_l3m.merge(
        dc_l2m_valid[dc_keys].assign(_use_l2m=True),
        on=dc_keys,
        how="left",
    )

    dc_result = dc_result[
        dc_result["_use_l2m"].isna()
    ].drop(columns="_use_l2m")

    dc_result = pd.concat(
        [
            dc_result,
            dc_l2m_valid,
        ],
        ignore_index=True,
    )

    # Keep only rows where we actually have fill-rate data
    dc_result = dc_result[
        dc_result["fill_rate_current"].notna()
        | dc_result["fill_rate_comparison"].notna()
    ].copy()

    dc_sku_diagnostics = add_diagnostics(dc_result)

    dc_sku_monthly = dc_monthly_timeline[
        dc_monthly_timeline["fill_rate"].notna()
    ].copy()


    # =====================================================
    # RETURN
    # =====================================================

    return {
        "chain_sku": chain_sku_diagnostics,
        "chain_sku_monthly": chain_monthly_timeline,
        "dc_sku": dc_sku_diagnostics,
        "dc_sku_monthly": dc_sku_monthly,
    }


from backend.data_pipeline.table_loader import (
    load_org_tables,
    load_active_pods,
    load_fill_rate_df,
)

def attach_fill_rate_inventory_assessments(
    dc_sku_diagnostics: pd.DataFrame,
    inventory_assessments,
) -> pd.DataFrame:
    """
    Attach canonical current inventory assessments to
    DC × SKU fill-rate diagnostics.

    Join grain:
        distributor × dc × sku

    This function does NOT calculate inventory status or
    recommendations. It only attaches the output of the
    canonical inventory assessment engine.
    """

    if dc_sku_diagnostics.empty:
        return dc_sku_diagnostics.copy()

    # -----------------------------------------------------
    # Normalize canonical inventory assessment output
    # -----------------------------------------------------

    # _load_cached_inventory_assessments() returns:
    #
    # {
    #     "rows": [...],
    #     "by_sku": {...},
    # }
    #
    # But allowing a DataFrame here makes this helper easier
    # to reuse/test independently.
    if isinstance(inventory_assessments, dict):
        inventory_rows = inventory_assessments.get("rows", [])
        inventory_df = pd.DataFrame(inventory_rows)

    elif isinstance(inventory_assessments, pd.DataFrame):
        inventory_df = inventory_assessments.copy()

    else:
        raise TypeError(
            "inventory_assessments must be either a dict "
            "containing 'rows' or a pandas DataFrame."
        )

    if inventory_df.empty:
        result = dc_sku_diagnostics.copy()
        result["inventory_assessment_available"] = False
        return result

    # -----------------------------------------------------
    # Validate join keys
    # -----------------------------------------------------

    join_cols = [
        "distributor",
        "dc",
        "sku",
    ]

    missing_diagnostic_cols = [
        col
        for col in join_cols
        if col not in dc_sku_diagnostics.columns
    ]

    missing_inventory_cols = [
        col
        for col in join_cols
        if col not in inventory_df.columns
    ]

    if missing_diagnostic_cols:
        raise ValueError(
            "DC diagnostics missing inventory join columns: "
            f"{missing_diagnostic_cols}"
        )

    if missing_inventory_cols:
        raise ValueError(
            "Inventory assessments missing join columns: "
            f"{missing_inventory_cols}"
        )

    # -----------------------------------------------------
    # Select inventory fields to attach
    # -----------------------------------------------------

    inventory_cols = [
        "distributor",
        "dc",
        "sku",

        "assessment_status",
        "inventory_status",
        "inventory_urgency",
        "po_status",

        "has_active_po",
        "has_overdue_po",
        "has_stale_po",
        "has_projected_order",
        "has_resolving_projected_order",

        "days_until_oos",
        "days_of_cushion",

        "projection_available",

        "as_of_date",
        "report_date",

        "observed_quantity_on_hand_cases",
        "estimated_quantity_on_hand_cases",
        "estimated_weeks_on_hand",

        "quantity_on_po_cases",

        "units_per_case",
        "units_per_week",
        "cases_per_week",

        "planning_lead_time_days",
        "planning_lead_time_source",

        "summary",
        "narrative",
    ]

    inventory_cols = [
        col
        for col in inventory_cols
        if col in inventory_df.columns
    ]

    inventory_df = inventory_df[
        inventory_cols
    ].copy()

    # -----------------------------------------------------
    # Attach current inventory assessment
    # -----------------------------------------------------

    result = dc_sku_diagnostics.merge(
        inventory_df,
        on=join_cols,
        how="left",
        validate="many_to_one",
        indicator="_inventory_merge",
    )

    result["inventory_assessment_available"] = (
        result["_inventory_merge"] == "both"
    )

    result = result.drop(
        columns=["_inventory_merge"]
    )

    return result

from pathlib import Path

import pandas as pd

from backend.data_pipeline.table_loader import (
    load_org_tables,
    load_active_pods,
    load_fill_rate_df,
)

from backend.serving.routes.inventory.inventory import (
    _load_cached_inventory_assessments,
)

from pathlib import Path

import pandas as pd

from backend.data_pipeline.table_loader import (
    load_org_tables,
    load_active_pods,
    load_fill_rate_df,
)

from backend.serving.routes.inventory.inventory import (
    _load_cached_inventory_assessments,
)


from pathlib import Path

import pandas as pd

from backend.data_pipeline.table_loader import (
    load_org_tables,
    load_active_pods,
    load_fill_rate_df,
)

from backend.serving.routes.inventory.inventory import (
    _load_cached_inventory_assessments,
)


def main():
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 300)

    org_id = "default_org"
    org_dir = Path("backend/data") / org_id

    # =====================================================
    # LOAD INPUT DATA
    # =====================================================

    features_df = load_org_tables(org_id)
    active_pods_df = load_active_pods(org_id)
    fill_rate_df = load_fill_rate_df(org_id)

    # =====================================================
    # BUILD FILL-RATE DIAGNOSTICS
    # =====================================================

    fill_rate_diagnostics = build_fill_rate_diagnostics(
        features_df=features_df,
        active_pods_df=active_pods_df,
        fill_rate_df=fill_rate_df,
        period="L3M",
        comparison="PP",
        end_month="2026-07",
    )

    # =====================================================
    # LOAD CURRENT CANONICAL INVENTORY ASSESSMENTS
    # =====================================================

    inventory_assessments = _load_cached_inventory_assessments(
        org_dir=org_dir,
        org_id=org_id,
    )

    # =====================================================
    # ATTACH INVENTORY TO DC FILL-RATE DIAGNOSTICS
    # =====================================================

    dc_with_inventory = attach_fill_rate_inventory_assessments(
        dc_sku_diagnostics=fill_rate_diagnostics["dc_sku"],
        inventory_assessments=inventory_assessments,
    )

    # =====================================================
    # INVENTORY JOIN SUMMARY
    # =====================================================

    print("\n=== INVENTORY JOIN SUMMARY ===")

    print(
        dc_with_inventory[
            "inventory_assessment_available"
        ].value_counts(dropna=False)
    )


    # =====================================================
    # PERIOD-LEVEL DC DIAGNOSTIC + CURRENT INVENTORY
    # =====================================================

    print("\n=== DC FILL-RATE DIAGNOSTIC + CURRENT INVENTORY ===")

    check_cols = [
        "distributor",
        "chain",
        "dc",
        "sku",

        # Historical diagnostic
        "primary_driver",
        "velocity_current",
        "velocity_comparison",
        "velocity_pct_change",
        "order_velocity_current",
        "order_velocity_comparison",
        "order_velocity_pct_change",
        "fill_rate_current",
        "fill_rate_comparison",
        "fill_rate_pct_change",
        "coverage_current",
        "coverage_comparison",

        # Current inventory
        "inventory_assessment_available",
        "inventory_status",
        "inventory_urgency",
        "estimated_quantity_on_hand_cases",
        "estimated_weeks_on_hand",
        "quantity_on_po_cases",
        "po_status",
        "days_until_oos",
        "days_of_cushion",
        "has_active_po",
        "has_projected_order",
    ]

    check_cols = [
        col
        for col in check_cols
        if col in dc_with_inventory.columns
    ]

    sort_cols = [
        col
        for col in [
            "chain",
            "sku",
            "distributor",
            "dc",
        ]
        if col in dc_with_inventory.columns
    ]

    print(
        dc_with_inventory[
            check_cols
        ]
        .sort_values(sort_cols)
        .round(3)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
import pandas as pd
import numpy as np
import backend.metrics as metric
from backend.metrics.metric_helpers import abs_change, pct_change, get_period_completeness
from backend.metrics.metric_calculators import calculate_active_pods
from backend.metrics.metric_helpers import resolve_period_comparison, filter_to_period, get_period_months, resolve_period

METRIC_CALCULATORS = {

    "units": (
        lambda df_filtered, df_full, group_cols, selected_months:
            metric.calculate_units(
                df=df_filtered,
                group_cols=group_cols,
            ),
        "units",
    ),

    "buying_stores": (
        lambda df_filtered, df_full, group_cols, selected_months:
            metric.calculate_buying_stores(
                df=df_filtered,
                group_cols=group_cols,
            ),
        "buying_stores",
    ),

    "active_pods": (
        lambda df_filtered, df_full, group_cols, selected_months:
            metric.calculate_active_pods(
                df_filtered=df_filtered,
                df_full=df_full,
                group_cols=group_cols,
                selected_months=selected_months,
            ),
        "active_pods",
    ),

    "velocity": (
        lambda df_filtered, df_full, group_cols, selected_months:
            metric.calculate_vpo(
                df_filtered=df_filtered,
                df_full=df_full,
                group_cols=group_cols,
                selected_months=selected_months,
            ),
        "vpo",
    ),

    "reorder_rate": (
        lambda df_filtered, df_full, group_cols, selected_months:
            metric.calculate_reorder_rate(
                df_filtered=df_filtered,
                df_full=df_full,
                group_cols=group_cols,
                selected_months=selected_months,
            ),
        "reorder_rate",
    ),
}

ZERO_IF_MISSING_METRICS = {
    "units",
    "buying_stores",
}

def calculate_metric(
    metric,
    df_filtered,
    df_full=None,
    group_cols=None,
    selected_months=None,
):
    config = METRIC_CALCULATORS.get(metric)

    if config is None:
        raise ValueError(f"Unsupported metric: {metric}")

    calculator, metric_column = config

    result = calculator(
        df_filtered=df_filtered,
        df_full=df_full,
        group_cols=group_cols,
        selected_months=selected_months,
    )

    # Ungrouped metrics may return a scalar
    if not isinstance(result, pd.DataFrame):
        return pd.DataFrame({
            "value": [result]
        })

    return result.rename(
        columns={metric_column: "value"}
    )

def get_comparison_eligibility(
    df_filtered,
    df_full,
    group_cols,
    comparison_start,
    metric,
):
    """
    Determines whether each group has enough history for a valid comparison.

    Most metrics:
        Requires active PODs in the first month of the comparison period.

    Reorder rate:
        Requires active PODs in the month before the comparison period.
    """

    eligibility_month = (
        comparison_start - 1
        if metric == "reorder_rate"
        else comparison_start
    )

    active_pods = calculate_active_pods(
        df_filtered=df_filtered,
        df_full=df_full,
        group_cols=group_cols,
        selected_months=[eligibility_month],
    )

    active_pods = active_pods.rename(
        columns={"active_pods": "eligibility_active_pods"}
    )

    active_pods["comparison_eligible"] = (
        active_pods["eligibility_active_pods"] > 0
    )

    return active_pods[
        group_cols
        + [
            "eligibility_active_pods",
            "comparison_eligible",
        ]
    ]

def compare_metric(
    df,
    df_full,
    metric,
    period,
    year,
    comparison,
    group_cols=None,
):
    group_cols = group_cols or []

    current_period, comparison_period = resolve_period_comparison(
        period=period,
        year=year,
        comparison=comparison,
    )

    current_df = filter_to_period(
        df,
        current_period["start"],
        current_period["end"],
    )

    comparison_df = filter_to_period(
        df,
        comparison_period["start"],
        comparison_period["end"],
    )

    current = calculate_metric(
        metric=metric,
        df_filtered=current_df,
        df_full=df_full,
        group_cols=group_cols,
        selected_months=get_period_months(
            current_period["start"],
            current_period["end"],
        ),
    )

    prior = calculate_metric(
        metric=metric,
        df_filtered=comparison_df,
        df_full=df_full,
        group_cols=group_cols,
        selected_months=get_period_months(
            comparison_period["start"],
            comparison_period["end"],
        ),
    )

    if group_cols:
        result = current.merge(
            prior,
            on=group_cols,
            how="outer",
            suffixes=("_current", "_comparison"),
        )

        eligibility = get_comparison_eligibility(
            df_filtered=df,
            df_full=df_full,
            group_cols=group_cols,
            comparison_start=comparison_period["start"],
            metric=metric,
        )

        result = result.merge(
            eligibility,
            on=group_cols,
            how="left",
        )

        result["comparison_eligible"] = (
            result["comparison_eligible"]
            .fillna(False)
            .astype(bool)
        )

    else:
        result = current.rename(
            columns={"value": "value_current"}
        ).copy()

        result["value_comparison"] = (
            prior["value"].iloc[0]
            if not prior.empty
            else None
        )

        eligibility = get_comparison_eligibility(
            df_filtered=df,
            df_full=df_full,
            group_cols=group_cols,
            comparison_start=comparison_period["start"],
            metric=metric,
        )

        result["comparison_eligible"] = bool(
            eligibility["comparison_eligible"].iloc[0]
            if not eligibility.empty
            else False
        )

    if metric in ZERO_IF_MISSING_METRICS:
        result["value_current"] = result["value_current"].fillna(0)
        result["value_comparison"] = result["value_comparison"].fillna(0)

    result["abs_change"] = abs_change(
        result["value_current"],
        result["value_comparison"],
    )

    result["pct_change"] = pct_change(
        result["value_current"],
        result["value_comparison"],
    )

    result.loc[
        ~result["comparison_eligible"],
        ["abs_change", "pct_change"],
    ] = np.nan

    return result

def get_comparison_eligibility_new(
    active_pods_df,
    group_cols,
    comparison_start,
    metric,
):
    """
    Determine whether each group is eligible for comparison using
    precomputed active-POD membership.

    Normal metrics:
        Must have at least one active POD in the first month of the
        comparison period.

    Reorder rate:
        Must have at least one active POD in the month immediately
        before the first month of the comparison period.
    """

    if group_cols is None:
        group_cols = []

    if isinstance(group_cols, str):
        group_cols = [group_cols]

    eligibility_month = (
        comparison_start - 1
        if metric == "reorder_rate"
        else comparison_start
    )

    eligibility_df = active_pods_df[
        active_pods_df["month_year"]
        == eligibility_month
    ]

    # Overall / ungrouped metric
    if not group_cols:
        active_pods = (
            eligibility_df["pod_helper"]
            .nunique()
        )

        return pd.DataFrame(
            {
                "eligibility_active_pods": [
                    active_pods
                ],
                "comparison_eligible": [
                    active_pods > 0
                ],
            }
        )

    # Grouped metric
    result = (
        eligibility_df
        .groupby(
            group_cols,
            as_index=False,
        )["pod_helper"]
        .nunique()
        .rename(
            columns={
                "pod_helper":
                    "eligibility_active_pods",
            }
        )
    )

    result["comparison_eligible"] = (
        result["eligibility_active_pods"] > 0
    )

    return result


def compare_metric_new(
    df,
    df_full,
    active_pods_df,
    metric,
    period,
    year=None,
    comparison="PP",
    group_cols=None,
):
    """
    Compare a metric between the selected period and comparison
    period using precomputed active-POD membership for comparison
    eligibility.

    Metric calculation remains unchanged. Only active-POD
    eligibility uses active_pods_df.
    """

    if group_cols is None:
        group_cols = []

    if isinstance(group_cols, str):
        group_cols = [group_cols]


    # -------------------------------------------------
    # RESOLVE CURRENT PERIOD
    # -------------------------------------------------

    current_period, comparison_period = resolve_period_comparison(
        period=period,
        year=year,
        comparison=comparison,
    )

    current_start = current_period["start"]
    current_end = current_period["end"]

    comparison_start = comparison_period["start"]
    comparison_end = comparison_period["end"]


    # -------------------------------------------------
    # FILTER PERIODS
    # -------------------------------------------------

    current_df = filter_to_period(
        df,
        current_start,
        current_end,
    )

    comparison_df = filter_to_period(
        df_full,
        comparison_start,
        comparison_end,
    )


    # -------------------------------------------------
    # CALCULATE CURRENT
    # -------------------------------------------------

    current_result = calculate_metric(
        metric=metric,
        df_filtered=current_df,
        df_full=df_full,
        group_cols=group_cols,
        selected_months=None,
    )

    current_result = current_result.rename(
        columns={
            "value": "value_current",
        }
    )


    # -------------------------------------------------
    # CALCULATE COMPARISON
    # -------------------------------------------------

    comparison_result = calculate_metric(
        metric=metric,
        df_filtered=comparison_df,
        df_full=df_full,
        group_cols=group_cols,
        selected_months=None,
    )

    comparison_result = comparison_result.rename(
        columns={
            "value": "value_comparison",
        }
    )


    # -------------------------------------------------
    # MERGE CURRENT + COMPARISON
    # -------------------------------------------------

    if group_cols:

        result = current_result.merge(
            comparison_result,
            on=group_cols,
            how="outer",
        )

    else:

        result = pd.DataFrame(
            {
                "value_current": [
                    current_result["value"].iloc[0]
                    if "value" in current_result.columns
                    else current_result[
                        "value_current"
                    ].iloc[0]
                ],
                "value_comparison": [
                    comparison_result["value"].iloc[0]
                    if "value" in comparison_result.columns
                    else comparison_result[
                        "value_comparison"
                    ].iloc[0]
                ],
            }
        )


    # -------------------------------------------------
    # ADDITIVE METRICS
    #
    # A missing row for an otherwise valid group means
    # zero activity for units / buying stores.
    # -------------------------------------------------

    if metric in ZERO_IF_MISSING_METRICS:

        result["value_current"] = (
            result["value_current"]
            .fillna(0)
        )

        result["value_comparison"] = (
            result["value_comparison"]
            .fillna(0)
        )


    # -------------------------------------------------
    # COMPARISON ELIGIBILITY
    #
    # This is the optimized portion.
    # No active-POD reconstruction occurs here.
    # -------------------------------------------------

    eligibility = (
        get_comparison_eligibility_new(
            active_pods_df=active_pods_df,
            group_cols=group_cols,
            comparison_start=comparison_start,
            metric=metric,
        )
    )

    if group_cols:

        result = result.merge(
            eligibility,
            on=group_cols,
            how="left",
        )

    else:

        result[
            "eligibility_active_pods"
        ] = eligibility[
            "eligibility_active_pods"
        ].iloc[0]

        result[
            "comparison_eligible"
        ] = eligibility[
            "comparison_eligible"
        ].iloc[0]


    result["comparison_eligible"] = (
        result["comparison_eligible"]
        .fillna(False)
        .astype(bool)
    )


    # -------------------------------------------------
    # CHANGES
    # -------------------------------------------------

    result["abs_change"] = (
        result["value_current"]
        - result["value_comparison"]
    )

    result["pct_change"] = pct_change(
        result["value_current"],
        result["value_comparison"],
    )


    # -------------------------------------------------
    # SUPPRESS INVALID COMPARISONS
    # -------------------------------------------------

    result.loc[
        ~result["comparison_eligible"],
        [
            "abs_change",
            "pct_change",
        ],
    ] = np.nan


    return result
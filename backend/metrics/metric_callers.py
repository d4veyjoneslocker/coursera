import pandas as pd
import numpy as np
import backend.metrics as metric
from backend.metrics.fill_rate.metrics import calculate_order_velocity, calculate_fill_rate
from backend.metrics.metric_helpers import resolve_period_comparison, filter_to_period, pct_change

#ADD CLACULATE_ORDER_VPO

METRIC_CALCULATORS = {
    "units": {
        "calculator": lambda df_filtered, active_pods_df, group_cols:
            metric.calculate_units(
                df=df_filtered,
                group_cols=group_cols,
            ),
        "column": "units",
        "zero_if_missing": True,
        "eligibility": "standard",
    },

    "buying_stores": {
        "calculator": lambda df_filtered, active_pods_df, group_cols:
            metric.calculate_buying_stores(
                df=df_filtered,
                group_cols=group_cols,
            ),
        "column": "buying_stores",
        "zero_if_missing": True,
        "eligibility": "standard",
    },

    "active_pods": {
        "calculator": lambda df_filtered, active_pods_df, group_cols:
            metric.calculate_active_pods(
                active_pods_df=active_pods_df,
                group_cols=group_cols,
            ),
        "column": "active_pods",
        "zero_if_missing": False,
        "eligibility": "standard",
    },

    "active_pod_opportunities": {
        "calculator": lambda df_filtered, active_pods_df, group_cols: metric.calculate_active_pod_opportunities(
            active_pods_df,
            group_cols=group_cols,
        ),
        "column": "active_pod_opportunities",
        "zero_if_missing": False,
        "eligibility": "standard",
    },

    "velocity": {
        "calculator": lambda df_filtered, active_pods_df, group_cols:
            metric.calculate_velocity(
                df_filtered=df_filtered,
                active_pods_df=active_pods_df,
                group_cols=group_cols,
            ),
        "column": "vpo",
        "zero_if_missing": False,
        "eligibility": "standard",
    },

    "reorder_rate": {
        "calculator": lambda df_filtered, active_pods_df, group_cols:
            metric.calculate_store_reorder_rate(
                active_pods_df=active_pods_df,
                group_cols=group_cols,
            ),
        "column": "reorder_rate",
        "zero_if_missing": False,
        "eligibility": "reorder",
    },

    "pod_reorder_rate": {
        "calculator": lambda df_filtered, active_pods_df, group_cols:
            metric.calculate_pod_reorder_rate(
                active_pods_df=active_pods_df,
                group_cols=group_cols,
            ),
        "column": "reorder_rate",
        "zero_if_missing": False,
        "eligibility": "reorder",
    },

    "fill_rate": {
        "calculator": lambda df_filtered, active_pods_df, group_cols:
            calculate_fill_rate(
                df=df_filtered,
                group_cols=group_cols,
            ),
        "column": "fill_rate",
        "zero_if_missing": False,
        "eligibility": "fill_rate_coverage",
    },
    "average_skus_per_store": {
        "calculator": lambda df_filtered, active_pods_df, group_cols:
            metric.calculate_average_skus_per_store(
                df=df_filtered,
                group_cols=group_cols,
            ),
        "column": "average_skus_per_store",
        "zero_if_missing": False,
        "eligibility": "standard",
    },
    "average_skus_per_store": {
        "calculator": lambda df_filtered, active_pods_df, group_cols:
            metric.calculate_average_skus_per_store(
                df=df_filtered,
                group_cols=group_cols,
            ),
        "column": "average_skus_per_store",
        "zero_if_missing": False,
        "eligibility": "standard",
    },
    "new_pods": {
        "calculator": lambda df_filtered, active_pods_df, group_cols:
            metric.calculate_new_pods(
                active_pods_df=active_pods_df,
                group_cols=group_cols,
            ),
        "column": "new_pods",
        "zero_if_missing": True,
        "eligibility": "standard",
    },
    "active_skus": {
        "calculator": lambda df_filtered, active_pods_df, group_cols: metric.calculate_active_skus(
            active_pods_df,
            group_cols=group_cols,
        ),
        "column": "active_skus",
        "zero_if_missing": False,
        "eligibility": "standard",
    },
    "skus_selling": {
        "calculator": lambda df_filtered, active_pods_df, group_cols:
            metric.calculate_skus_selling(
                df=df_filtered,
                group_cols=group_cols,
            ),
        "column": "skus_selling",
        "zero_if_missing": True,
        "eligibility": None,
    },
    "order_velocity": {
        "calculator": lambda df_filtered, active_pods_df, group_cols: calculate_order_velocity(
            fill_rate_df=df_filtered,
            active_pods_df=active_pods_df,
            group_cols=group_cols,
        ),
        "column": "order_vpo",
        "zero_if_missing": False,
        "eligibility": "fill_rate_coverage",
    },
}

def calculate_metric(
    metric_name,
    df_filtered,
    active_pods_df,
    group_cols=None,
):
    metric_definition = METRIC_CALCULATORS.get(metric_name)

    if metric_definition is None:
        raise ValueError(f"Unsupported metric: {metric_name}")

    result = metric_definition["calculator"](
        df_filtered=df_filtered,
        active_pods_df=active_pods_df,
        group_cols=group_cols,
    )

    if not isinstance(result, pd.DataFrame):
        return pd.DataFrame({
            "value": [result]
        })

    return result.rename(
        columns={
            metric_definition["column"]: "value"
        }
    )

def get_comparison_eligibility(
    active_pods_df,
    group_cols,
    comparison_start,
    metric_name,
):
    """
    Determine whether each group is eligible for comparison using
    precomputed active-POD membership.

    Standard metrics:
        Must have at least one active POD in the first month of the
        comparison period.

    Reorder metrics:
        Must have at least one active POD in the month immediately
        before the first month of the comparison period. This ensures
        there was an existing active-POD universe with an opportunity
        to reorder when the comparison period began.

    Fill-rate coverage metrics:
        Must have at least one active POD with fill-rate coverage in
        the first month of the comparison period.
    """

    if group_cols is None:
        group_cols = []

    if isinstance(group_cols, str):
        group_cols = [group_cols]

    metric_definition = METRIC_CALCULATORS.get(metric_name)

    if metric_definition is None:
        raise ValueError(f"Unsupported metric: {metric_name}")

    eligibility_type = metric_definition["eligibility"]

    df = active_pods_df.copy()

    if eligibility_type == "fill_rate_coverage":
        df = df[
            df["has_fill_rate_data"]
        ].copy()

    eligibility_month = (
        comparison_start - 1
        if eligibility_type == "reorder"
        else comparison_start
    )

    eligibility_df = df[
        df["month_year"] == eligibility_month
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


def compare_metric(
    df,
    df_full,
    active_pods_df,
    metric_name,
    period,
    year=None,
    comparison="PP",
    group_cols=None,
    end_month=None,
):
    """
    Compare a metric between the selected period and comparison period.
    """

    if group_cols is None:
        group_cols = []

    if isinstance(group_cols, str):
        group_cols = [group_cols]

    metric_definition = METRIC_CALCULATORS.get(metric_name)

    if metric_definition is None:
        raise ValueError(f"Unsupported metric: {metric_name}")

    # -------------------------------------------------
    # RESOLVE PERIODS
    # -------------------------------------------------

    current_period, comparison_period = resolve_period_comparison(
        period=period,
        year=year,
        comparison=comparison,
        end_month=end_month,
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

    current_active_pods_df = filter_to_period(
        active_pods_df,
        current_start,
        current_end,
    )

    comparison_df = filter_to_period(
        df_full,
        comparison_start,
        comparison_end,
    )

    comparison_active_pods_df = filter_to_period(
        active_pods_df,
        comparison_start,
        comparison_end,
    )

    # -------------------------------------------------
    # CALCULATE CURRENT
    # -------------------------------------------------

    current_result = calculate_metric(
        metric_name=metric_name,
        df_filtered=current_df,
        active_pods_df=current_active_pods_df,
        group_cols=group_cols,
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
        metric_name=metric_name,
        df_filtered=comparison_df,
        active_pods_df=comparison_active_pods_df,
        group_cols=group_cols,
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
                    current_result["value_current"].iloc[0]
                ],
                "value_comparison": [
                    comparison_result["value_comparison"].iloc[0]
                ],
            }
        )

    # -------------------------------------------------
    # ZERO IF MISSING
    # -------------------------------------------------

    if metric_definition["zero_if_missing"]:
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
    # -------------------------------------------------

    eligibility = get_comparison_eligibility(
        active_pods_df=active_pods_df,
        group_cols=group_cols,
        comparison_start=comparison_start,
        metric_name=metric_name,
    )

    if group_cols:
        result = result.merge(
            eligibility,
            on=group_cols,
            how="left",
        )

    else:
        result["eligibility_active_pods"] = (
            eligibility["eligibility_active_pods"].iloc[0]
        )

        result["comparison_eligible"] = (
            eligibility["comparison_eligible"].iloc[0]
        )

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


def calculate_monthly_metric(
    metric_name,
    df_filtered,
    active_pods_df,
    group_cols=None,
):
    if group_cols is None:
        group_cols = []

    if isinstance(group_cols, str):
        group_cols = [group_cols]

    group_cols = [col for col in group_cols if col != "month_year"]
    monthly_group_cols = group_cols + ["month_year"]

    return calculate_metric(
        metric_name=metric_name,
        df_filtered=df_filtered,
        active_pods_df=active_pods_df,
        group_cols=monthly_group_cols,
    )
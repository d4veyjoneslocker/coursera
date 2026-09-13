import pandas as pd
import backend.metrics as metric
from backend.metrics.metric_helpers import abs_change, pct_change

from backend.metrics.metric_helpers import resolve_period_comparison, filter_to_period, get_period_months

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
    else:
        result = current.rename(
            columns={"value": "value_current"}
        ).copy()

        result["value_comparison"] = (
            prior["value"].iloc[0]
            if not prior.empty
            else None
        )

    result["abs_change"] = abs_change(
        result["value_current"],
        result["value_comparison"],
    )

    result["pct_change"] = pct_change(
        result["value_current"],
        result["value_comparison"],
    )

    return result
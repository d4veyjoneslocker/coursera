import pandas as pd
import numpy as np
from typing import Literal

from backend.filters.filter_table import filter_table
from backend.metrics.features import add_features

from backend.metrics.metric_callers import calculate_monthly_metric

def clean_for_json(df: pd.DataFrame) -> pd.DataFrame:
    # convert periods/dates first
    for col in df.columns:
        if pd.api.types.is_period_dtype(df[col]) or pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].astype(str)

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.astype(object).where(pd.notnull(df), None)

    return df

def clean_object_for_json(value):
    if isinstance(value, dict):
        return {
            key: clean_object_for_json(val)
            for key, val in value.items()
        }

    if isinstance(value, list):
        return [
            clean_object_for_json(val)
            for val in value
        ]

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        if pd.isna(value) or np.isinf(value):
            return None
        return float(value)

    if isinstance(value, float):
        if pd.isna(value) or np.isinf(value):
            return None

    return value

def prep_monthly_graph(df, metric):
    df = df[["month_year", metric]]
    df = df.rename(columns={metric: "value"})

    return df

def remove_time_filters(filters):
    non_time_filters = filters.copy()
    non_time_filters.pop("year", None)
    non_time_filters.pop("month_year", None)

    return non_time_filters

def filter_and_recompute_features(df, filters, feature_filter_keys={"status"}):
    base_filters = {k: v for k, v in filters.items() if k not in feature_filter_keys}
    feature_filters = {k: v for k, v in filters.items() if k in feature_filter_keys}

    df = filter_table(df, **base_filters)
    df = add_features(df)
    df = filter_table(df, **feature_filters)

    return df

def convert_selected_months(selected_months):
    if not selected_months:
        return None

    return [pd.Period(m, freq="M") for m in selected_months]

def convert_selected_years(selected_years):
    if not selected_years:
        return None

    return [int(y) for y in selected_years]

ChartMetric = Literal[
    "units",
    "buyers",
    "velocity",
    "pods",
    "reorders",
    "fill_rate"
]
ChartView = Literal["default", "all_time", "yoy"]


def _get_monthly_metric_table(
    metric: ChartMetric,
    df: pd.DataFrame,
    active_pods_df: pd.DataFrame,
):
    metric_map = {
        "units": ("units", "units"),
        "buyers": ("buying_stores", "buying_stores"),
        "velocity": ("velocity", "vpo"),
        "pods": ("active_pods", "active_pods"),
        "reorders": ("reorder_rate", "reorder_rate"),
        "fill_rate": ("fill_rate", "fill_rate"),
    }

    if metric not in metric_map:
        raise ValueError(f"Unsupported metric: {metric}")

    metric_name, value_col = metric_map[metric]

    result = calculate_monthly_metric(
        metric_name=metric_name,
        df_filtered=df,
        active_pods_df=active_pods_df,
    )

    result = calculate_monthly_metric(
    metric_name=metric_name,
    df_filtered=df,
    active_pods_df=active_pods_df,
)

    if metric == "reorders":
        print("\n=== REORDER CHART DEBUG ===")
        print("features months:", sorted(df["month_year"].unique()))
        print("active pod months:", sorted(active_pods_df["month_year"].unique()))
        print("result:")
        print(result.to_string(index=False))
        print("===========================\n")

    result = result.rename(
        columns={"value": value_col}
    )

    return result, value_col


def _prep_all_time_chart(
    result: pd.DataFrame,
    value_col: str,
):
    result = prep_monthly_graph(result, value_col)

    result = clean_for_json(result)

    return result.to_dict(orient="records")


def _prep_yoy_chart(
    result: pd.DataFrame,
    value_col: str,
):
    df = result.copy()

    df["month_year"] = pd.PeriodIndex(
        df["month_year"],
        freq="M",
    )

    df["year"] = df["month_year"].dt.year
    df["month_num"] = df["month_year"].dt.month
    df["month"] = df["month_year"].dt.strftime("%b")

    latest_year = int(df["year"].max())
    prior_year = latest_year - 1

    yoy_df = df[df["year"].isin([latest_year, prior_year])].copy()

    pivot = (
        yoy_df.pivot_table(
            index=["month_num", "month"],
            columns="year",
            values=value_col,
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
        .sort_values("month_num")
    )

    if latest_year not in pivot.columns:
        pivot[latest_year] = 0

    if prior_year not in pivot.columns:
        pivot[prior_year] = 0

    pivot["current_year"] = latest_year
    pivot["prior_year"] = prior_year

    pivot["current_value"] = pivot[latest_year]
    pivot["prior_value"] = pivot[prior_year]

    result = pivot[
        [
            "month_num",
            "month",
            "current_year",
            "current_value",
            "prior_year",
            "prior_value",
        ]
    ]

    result = clean_for_json(result)

    return result.to_dict(orient="records")


def build_expanded_chart(
    features_df: pd.DataFrame,
    active_pods_df: pd.DataFrame,
    metric: ChartMetric,
    view: ChartView,
    filters: dict,
    fill_rate_df: pd.DataFrame | None = None,
):
    if view == "all_time":
        chart_filters = remove_time_filters(filters)

    elif view == "default":
        chart_filters = filters.copy()

        # If the user has not explicitly selected a time period,
        # default the chart to the latest 12 months of actual sales data.
        if (
            not chart_filters.get("year")
            and not chart_filters.get("month_year")
        ):
            latest_month = features_df["month_year"].max()

            last_12_months = [
                month.strftime("%Y-%m")
                for month in pd.period_range(
                    end=latest_month,
                    periods=12,
                    freq="M",
                )
            ]

            chart_filters["month_year"] = last_12_months

    else:
        chart_filters = filters

    # Fill rate lives in its own monthly dataset.
    # All other expanded-chart metrics use the main feature dataset.
    if metric == "fill_rate":
        if fill_rate_df is None:
            raise ValueError(
                "fill_rate_df is required for fill_rate charts."
            )

        fill_rate_filters = {
            key: value
            for key, value in chart_filters.items()
            if key in fill_rate_df.columns
        }

        df = filter_table(
            fill_rate_df,
            **fill_rate_filters,
        )
    else:
        df = filter_table(
            features_df,
            **chart_filters,
        )

    active_pods_filtered = filter_table(
        active_pods_df,
        **chart_filters,
    )

    # Active PODs are forward-expanded, so historical charts
    # should stop at the latest month with actual sales data.
    latest_actual_month = features_df["month_year"].max()

    active_pods_filtered = active_pods_filtered[
        active_pods_filtered["month_year"] <= latest_actual_month
    ].copy()

    result, value_col = _get_monthly_metric_table(
        metric=metric,
        df=df,
        active_pods_df=active_pods_filtered,
    )

    if view == "yoy":
        return _prep_yoy_chart(
            result=result,
            value_col=value_col,
        )

    return _prep_all_time_chart(
        result=result,
        value_col=value_col,
    )
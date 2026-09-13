import pandas as pd
import numpy as np
from typing import Literal

from backend.filters.filter_table import filter_table
from backend.metrics.features import add_features

from backend.metrics.monthly_metric_calculators import (
    calculate_monthly_units,
    calculate_monthly_active_pods,
    calculate_monthly_buying_stores,
    calculate_monthly_vpo,
)

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

ChartMetric = Literal["units", "buyers", "velocity", "pods"]
ChartView = Literal["default", "all_time", "yoy"]


def _get_monthly_metric_table(
    metric: ChartMetric,
    df: pd.DataFrame,
    features_df: pd.DataFrame,
    filters: dict,
    selected_years=None,
    selected_months=None,
):
    if metric == "units":
        result = calculate_monthly_units(
            df,
            selected_years=selected_years,
            selected_months=selected_months,
            include_current_month=True,
        )

        return result, "units"

    if metric == "buyers":
        result = calculate_monthly_buying_stores(
            df,
            selected_years=selected_years,
            selected_months=selected_months,
            include_current_month=True,
        )

        return result, "buying_stores"

    if metric == "velocity":
        non_time_filters = remove_time_filters(filters)

        all_time_df = filter_table(features_df, **non_time_filters)

        result = calculate_monthly_vpo(
            df,
            all_time_df,
            selected_years=selected_years,
            selected_months=selected_months,
        )

        return result, "vpo"

    if metric == "pods":
        pod_filters = filters.copy()

        pod_filters.pop("year", None)
        pod_filters.pop("month", None)
        pod_filters.pop("month_year", None)

        pod_df = filter_table(features_df, **pod_filters)

        result = calculate_monthly_active_pods(
            df,
            pod_df,
            selected_years=selected_years,
            selected_months=selected_months,
        )

        return result, "active_pods"

    raise ValueError(f"Unsupported metric: {metric}")


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
    metric: ChartMetric,
    view: ChartView,
    filters: dict,
):
    if view == "all_time":
        chart_filters = remove_time_filters(filters)

        selected_years = None
        selected_months = None

    else:
        chart_filters = filters

        selected_years = convert_selected_years(
            filters.get("year")
        )

        selected_months = convert_selected_months(
            filters.get("month_year")
        )

    df = filter_table(features_df, **chart_filters)

    result, value_col = _get_monthly_metric_table(
        metric=metric,
        df=df,
        features_df=features_df,
        filters=chart_filters,
        selected_years=selected_years,
        selected_months=selected_months,
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

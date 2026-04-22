import pandas as pd
import numpy as np

from backend.filters.filter_table import filter_table
from backend.metrics.features import add_features

def clean_for_json(df: pd.DataFrame) -> pd.DataFrame:
    # convert periods/dates first
    for col in df.columns:
        if pd.api.types.is_period_dtype(df[col]) or pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].astype(str)

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.astype(object).where(pd.notnull(df), None)

    return df

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
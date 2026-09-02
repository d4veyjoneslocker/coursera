import pandas as pd
import numpy as np

# AGGREGATIONS

def total(series):
    return series.sum() if len(series) else None

def peak(series):
    return series.max() if len(series) else None

def average(series):
    return series.mean()

def latest_month(series):
    if len(series) == 0:
        return None
    value = series.iloc[-1]
    return None if pd.isna(value) else value

def l3m(series):
    return series.tail(3).sum() if len(series) else None

def safe_float(val):
    return float(val) if pd.notna(val) else None

def safe_int(val):
    return int(val) if pd.notna(val) else None

def pct_change(current, prior):
    current = pd.to_numeric(current, errors="coerce")
    prior = pd.to_numeric(prior, errors="coerce")

    return np.where(
        (prior.isna()) | (prior == 0),
        np.nan,
        current / prior - 1
    )

def abs_change(current, prior):
    return np.where(
        pd.notna(prior),
        current - prior,
        np.nan
    )


# HELPER FUNCTIONS

def grouped_cumsum(df, metric, group_cols):
    non_time_cols = [c for c in group_cols if c != "month_year"]

    if non_time_cols:
        return df.groupby(non_time_cols)[metric].cumsum()

    return df[metric].cumsum()


def clean_group_cols(group_cols):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    group_cols = group_cols or []

    if "month_year" in group_cols:
        group_cols = [c for c in group_cols if c != "month_year"] + ["month_year"]
    else:
        group_cols = group_cols + ["month_year"]

    return group_cols


def get_current_period(include_current_month=False):
    today = pd.Timestamp.today()
    current_period = pd.Period(today, freq="M")

    if not include_current_month:
        current_period -= 1

    return current_period

def calculate_avg_skus_per_store(df, grain):
    result = (
        df.groupby([grain, "coded_customer"])["sku"]
        .nunique()
        .reset_index(name="sku_count")
    )

    result = (
        result.groupby(grain, as_index=False)["sku_count"]
        .mean()
        .rename(columns={"sku_count": "avg_skus_per_store"})
    )

    return result


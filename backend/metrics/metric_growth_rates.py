import pandas as pd
import numpy as np
from backend.metrics.metric_helpers import ensure_month_spine

def pct_change(current, prior):
    return np.where(
        prior > 0,
        current / prior - 1,
        np.nan
    )

def add_pct_change_columns(df, metric, l1m=None, l3m=None, py=None):

    if l1m:
        df[f"{metric}_l1m_pct"] = pct_change(df[f"{metric}"], df[f"{metric}_l1m"])

    if l3m:
        df[f"{metric}_l3m_pct"] = pct_change(df[f"{metric}"], df[f"{metric}_l3m"])
    
    if py:
        df[f"{metric}_py_pct"] = pct_change(df[f"{metric}"], df[f"{metric}_py"])

    return df

def calculate_reorder_rate(df, timeframe):
    
    result = df[f"repeat_buyers_{timeframe}"] / df[f"existing_buyers_{timeframe}"]
    
    return result.replace([float("inf"), -float("inf")], None)

def prepare_time_series(df, group_cols, value_cols=None):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    if "month_year" in group_cols:
        group_cols = [c for c in group_cols if c != "month_year"] + ["month_year"]
    else:
        group_cols = group_cols + ["month_year"]

    non_time_cols = [c for c in group_cols if c != "month_year"]

    df = ensure_month_spine(
        df,
        group_cols=non_time_cols,
        value_cols=value_cols
    )

    return df, group_cols, non_time_cols


def add_prior_month_columns(df, group_cols, metric, l1m=None, l3m=None, py=None):
    df, group_cols, non_time_cols = prepare_time_series(
        df,
        group_cols,
        [metric]
    )

    result = df.sort_values(group_cols).copy()

    if non_time_cols:
        if l1m:
            result[f"{metric}_l1m"] = result.groupby(non_time_cols)[metric].shift(1)

        if l3m:
            result[f"{metric}_l3m"] = result.groupby(non_time_cols)[f"{metric}_3m"].shift(3)

        if py:
            result[f"{metric}_py"] = result.groupby(non_time_cols)[metric].shift(12)

    else:
        if l1m:
            result[f"{metric}_l1m"] = result[metric].shift(1)

        if l3m:
            result[f"{metric}_l3m"] = result[f"{metric}_3m"].shift(3)

        if py:
            result[f"{metric}_py"] = result[metric].shift(12)

    return result

# Additive metric examples: units, revenue, new_pods


def add_additive_metric_3m(df, group_cols, metric):
    df, group_cols, non_time_cols = prepare_time_series(
        df,
        group_cols,
        [metric]
    )

    result = df.sort_values(group_cols).copy()

    if non_time_cols:
        result[f"{metric}_3m"] = (
            result.groupby(non_time_cols)[metric]
            .rolling(3, min_periods=3)
            .sum()
            .reset_index(level=0, drop=True)
        )
    else:
        result[f"{metric}_3m"] = result[metric].rolling(3, min_periods=3).sum()

    return result

def add_buying_stores_3m(df, group_cols):


    if isinstance(group_cols, str):
        group_cols = [group_cols]

    if "month_year" in group_cols:
        group_cols = [c for c in group_cols if c != "month_year"] + ["month_year"]
    else:
        group_cols = group_cols + ["month_year"]

    non_time_cols = [c for c in group_cols if c != "month_year"]

    df = ensure_month_spine(
        df,
        group_cols=non_time_cols + ["coded_customer"],
    )

    months = sorted(df["month_year"].unique())
    rows = []

    for i in range(2, len(months)):
        current_month = months[i]
        window = months[i - 2:i + 1]

        df_window = df[df["month_year"].isin(window)]

        if non_time_cols:
            grouped = (
                df_window.groupby(non_time_cols, as_index=False)
                .agg(buying_stores_3m=("coded_customer", "nunique"))
            )
            grouped["month_year"] = current_month
        else:
            grouped = pd.DataFrame(
                {
                    "month_year": [current_month],
                    "buying_stores_3m": [df_window["coded_customer"].nunique()],
                }
            )

        rows.append(grouped)

    result = pd.concat(rows, ignore_index=True)

    return result

def add_vpo_3m(df, group_cols):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    if "month_year" in group_cols:
        group_cols = [c for c in group_cols if c != "month_year"] + ["month_year"]
    else:
        group_cols = group_cols + ["month_year"]
    
    
    units_3m = add_additive_metric_3m(df, group_cols, "units")
    active_pods_3m = add_additive_metric_3m(df, group_cols, "active_pods")

    result = units_3m.merge(
        active_pods_3m[group_cols + ["active_pods_3m"]],
        on = group_cols,
        how = "left"
    )

    result["vpo_3m"] = result["units_3m"]/result["active_pods_3m"]/4

    return result[group_cols + ["vpo_3m"]]

def add_reorder_rate_3m(df, group_cols):

    if isinstance(group_cols, str):
        group_cols = [group_cols]

    # Ensures that month_year is in the right order for the sorting before the cumsum

    if "month_year" in group_cols:
        group_cols = [c for c in group_cols if c != "month_year"] + ["month_year"]
    else:
        group_cols = group_cols + ["month_year"]
    
    non_time_cols = [c for c in group_cols if c != "month_year"]

    store_universe = (
        df.groupby(["coded_customer"] + group_cols, as_index=False)
        .agg(
            repeat_buyer=("reorder_flag", "max"),
            new_buyer=("first_store_flag", "max"),
        )
    )

    result = (
        store_universe.groupby(group_cols, as_index=False)
        .agg(
            repeat_buyers=("repeat_buyer", "sum"),
            new_buyers=("new_buyer", "sum"),
            buying_stores=("coded_customer", "nunique"),
        )
        .sort_values(group_cols)
        .reset_index(drop=True)
    )

    result = ensure_month_spine(
        result,
        group_cols=non_time_cols,
        value_cols=["repeat_buyers", "new_buyers", "buying_stores"]
    )

    if non_time_cols:
        result["total_buyers"] = result.groupby(non_time_cols)["new_buyers"].cumsum()
    else:
        result["total_buyers"] = result["new_buyers"].cumsum()

    result["existing_buyers"] = result["total_buyers"] - result["new_buyers"]

    result = add_additive_metric_3m(result, group_cols, "repeat_buyers")
    result = add_additive_metric_3m(result, group_cols, "existing_buyers")

    result["reorder_rate_3m"] = calculate_reorder_rate(result, "3m")

    return result[group_cols + ["reorder_rate_3m"]]

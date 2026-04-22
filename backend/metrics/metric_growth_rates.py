import pandas as pd
import numpy as np
from backend.metrics.metric_helpers import build_spine, clean_group_cols, build_comparison_spine
from backend.metrics.monthly_metric_calculators import(
    calculate_monthly_active_pods,
    calculate_monthly_existing_buyers,
    calculate_monthly_repeat_buyers,
    calculate_monthly_units
)

def pct_change(current, prior):
    return np.where(
        prior > 0,
        current / prior - 1,
        np.nan
    )

def abs_change(current, prior):
    return np.where(
        pd.notna(prior),
        current - prior,
        np.nan
    )

def add_pct_change_columns(df, metric, l1m=None, l3m=None, py=None):

    if l1m:
        df[f"{metric}_l1m_pct"] = pct_change(df[f"{metric}"], df[f"{metric}_l1m"])

    if l3m:
        df[f"{metric}_l3m_pct"] = pct_change(df[f"{metric}_3m"], df[f"{metric}_l3m"])
    
    if py:
        df[f"{metric}_py_pct"] = pct_change(df[f"{metric}"], df[f"{metric}_py"])

    return df

def add_abs_change_columns(df, metric, l1m=None, l3m=None, py=None):

    if l1m:
        df[f"{metric}_l1m_abs"] = abs_change(df[f"{metric}"], df[f"{metric}_l1m"])

    if l3m:
        df[f"{metric}_l3m_abs"] = abs_change(df[f"{metric}_3m"], df[f"{metric}_l3m"])
    
    if py:
        df[f"{metric}_py_abs"] = abs_change(df[f"{metric}"], df[f"{metric}_py"])

    return df

def calculate_reorder_rate(df, timeframe):
    
    result = df[f"repeat_buyers_{timeframe}"] / df[f"existing_buyers_{timeframe}"]
    
    return result.replace([float("inf"), -float("inf")], None)

def prepare_growth_time_series(df, group_cols, selected_years=None, selected_months=None):
    if group_cols is None:
        group_cols = []
    elif isinstance(group_cols, str):
        group_cols = [group_cols]


    if "month_year" in group_cols:
        group_cols = [c for c in group_cols if c != "month_year"] + ["month_year"]
    else:
        group_cols = group_cols + ["month_year"]

    non_time_cols = [c for c in group_cols if c != "month_year"]

    spine = build_spine(df, group_cols=non_time_cols, selected_years=selected_years, selected_months=selected_months, include_current_month=True)

    return spine, group_cols, non_time_cols


def add_prior_month_columns(df, group_cols, metric, df_all_time=None, l1m=None, l3m=None, py=None, selected_years=None, selected_months=None):
    group_cols = clean_group_cols(group_cols)
    non_time_cols = [c for c in group_cols if c != "month_year"]

    original_start = df["month_year"].min()
    original_end = df["month_year"].max()


    if df_all_time is None:
        df_all_time=df

    lookback_months = 0
    if l1m:
        lookback_months = max(lookback_months, 1)
    if l3m:
        lookback_months = max(lookback_months, 3)
    if py:
        lookback_months = max(lookback_months, 12)

    comparison_spine = build_comparison_spine(df_all_time, group_cols=non_time_cols, lookback_months=lookback_months, selected_years=selected_years, selected_months=selected_months, include_current_month=True)

    df = comparison_spine.merge(df, on=group_cols, how="left")
    df = df.sort_values(group_cols).copy()

    if non_time_cols:
        if l1m:
            df[f"{metric}_l1m"] = df.groupby(non_time_cols)[metric].shift(1)

        if l3m:
            df[f"{metric}_l3m"] = df.groupby(non_time_cols)[f"{metric}_3m"].shift(3)

        if py:
            df[f"{metric}_py"] = df.groupby(non_time_cols)[metric].shift(12)

    else:
        if l1m:
            df[f"{metric}_l1m"] = df[metric].shift(1)

        if l3m:
            df[f"{metric}_l3m"] = df[f"{metric}_3m"].shift(3)

        if py:
            df[f"{metric}_py"] = df[metric].shift(12)
    
    if selected_months:
        df = df[df["month_year"].isin(selected_months)]
    elif selected_years:
        df = df[df["month_year"].dt.year.isin(selected_years)]
    else:
        df = df[
        (df["month_year"] >= original_start) &
        (df["month_year"] <= original_end)
    ]

    return df

# Additive metric examples: units, revenue, new_pods


def add_additive_metric_3m(df, group_cols, metric, selected_years=None, selected_months=None):
    spine, group_cols, non_time_cols = prepare_growth_time_series(df, group_cols, selected_years=selected_years, selected_months=selected_months)

    df = df.sort_values(group_cols).copy()

    df = spine.merge(
        df,
        on=group_cols,
        how="left",
    )

    df[metric] = df[metric].fillna(0)

    if non_time_cols:
        df[f"{metric}_3m"] = (
            df.groupby(non_time_cols)[metric]
            .rolling(3, min_periods=3)
            .sum()
            .reset_index(level=list(range(len(non_time_cols))), drop=True)
        )
    else:
        df[f"{metric}_3m"] = df[metric].rolling(3, min_periods=3).sum()

    return df

def calculate_buying_stores_3m(df, group_cols, selected_years=None, selected_months=None):

# Merge back onto spine / general fix

    if isinstance(group_cols, str):
        group_cols = [group_cols]

    if "month_year" in group_cols:
        group_cols = [c for c in group_cols if c != "month_year"] + ["month_year"]
    else:
        group_cols = group_cols + ["month_year"]

    non_time_cols = [c for c in group_cols if c != "month_year"]

    spine = build_spine(df, group_cols=non_time_cols, selected_years=selected_years, selected_months=selected_months)
    months = sorted(spine["month_year"].unique())

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

    if not rows:
        result = pd.DataFrame(columns=group_cols + ["buying_stores_3m"])
    else:
        result = pd.concat(rows, ignore_index=True)

    result = spine.merge(
        result,
        on=group_cols,
        how="left"
    )

    result["buying_stores_3m"] = result["buying_stores_3m"].fillna(0)

    return result[group_cols + ["buying_stores_3m"]]

def calculate_vpo_3m(df_filtered, df_full, group_cols=None, selected_years=None, selected_months=None):
    if group_cols is None:
        group_cols = []
    elif isinstance(group_cols, str):
        group_cols = [group_cols]

    if "month_year" in group_cols:
        group_cols = [c for c in group_cols if c != "month_year"] + ["month_year"]
    else:
        group_cols = group_cols + ["month_year"]

    units = calculate_monthly_units(
        df=df_filtered,
        group_cols=group_cols,
    )

    active_pods = calculate_monthly_active_pods(
        df_filtered=df_filtered,
        df_full=df_full,
        group_cols=group_cols,
        selected_years=selected_years,
        selected_months=selected_months,
    )

    units_3m = add_additive_metric_3m(units, group_cols, "units")
    active_pods_3m = add_additive_metric_3m(active_pods, group_cols, "active_pods")

    result = units_3m.merge(
        active_pods_3m[group_cols + ["active_pods_3m"]],
        on=group_cols,
        how="left",
    )

    result["vpo_3m"] = (result["units_3m"] / result["active_pods_3m"].replace(0, None) / 4).replace([float("inf"), -float("inf")], None)

    return result[group_cols + ["vpo_3m"]]

def calculate_reorder_rate_3m(df_filtered, df_full, group_cols=None, selected_years=None, selected_months=None):
    if group_cols is None:
        group_cols = []
    elif isinstance(group_cols, str):
        group_cols = [group_cols]

    if "month_year" in group_cols:
        group_cols = [c for c in group_cols if c != "month_year"] + ["month_year"]
    else:
        group_cols = group_cols + ["month_year"]

    existing = calculate_monthly_existing_buyers(
        df_filtered=df_filtered,
        df_full=df_full,
        group_cols=group_cols,
        selected_years=selected_years,
        selected_months=selected_months,
    )

    repeat = calculate_monthly_repeat_buyers(
        df_filtered=df_filtered,
        group_cols=group_cols,
        selected_years=selected_years,
        selected_months=selected_months,
    )

    existing_3m = add_additive_metric_3m(existing, group_cols, "existing_buyers")
    repeat_3m = add_additive_metric_3m(repeat, group_cols, "repeat_buyers")

    result = existing_3m.merge(
        repeat_3m[group_cols + ["repeat_buyers_3m"]],
        on=group_cols,
        how="left",
    )

    result["repeat_buyers_3m"] = result["repeat_buyers_3m"].fillna(0)

    result["reorder_rate_3m"] = calculate_reorder_rate(result, "3m")

    return result[group_cols + ["reorder_rate_3m"]]

# PROB MOVE THESE TWO FUNCTIONS SOMEWHERE ELSE
import pandas as pd
from backend.metrics.metric_spine_builders import build_spine, build_window_universe_spine, build_full_universe_spine
from backend.metrics.metric_helpers import grouped_cumsum, clean_group_cols
from datetime import datetime

def calculate_reorder_rate(df):
    result = df["repeat_buyers"] / df["existing_buyers"]
    return result.replace([float("inf"), -float("inf")], None)

    

# ------------------------------------------------------------------------

def calculate_monthly_revenue(df, group_cols=None):
    group_cols = clean_group_cols(group_cols)

    result = (
        df.groupby(group_cols, as_index=False)
        .agg(revenue=("revenue", "sum"))
    )

    return result

def calculate_monthly_units(df, group_cols=None, selected_years=None, selected_months=None, include_current_month=True):
    group_cols = clean_group_cols(group_cols)
    non_time_cols = [c for c in group_cols if c != "month_year"]
    spine = build_spine(df, group_cols=non_time_cols, selected_years=selected_years, selected_months=selected_months, include_current_month=include_current_month,)

    result = (
        df.groupby(group_cols, as_index=False)
        .agg(units=("units", "sum"))
    )
    result = spine.merge(result, on=group_cols, how="left")
    result["units"] = result["units"].fillna(0)

    return result

def calculate_monthly_buying_stores(df, group_cols=None, selected_years=None, selected_months=None, include_current_month=True):
    group_cols = clean_group_cols(group_cols)
    non_time_cols = [c for c in group_cols if c != "month_year"]
    spine = build_spine(df, group_cols=non_time_cols, selected_years=selected_years, selected_months=selected_months, include_current_month=include_current_month,)


    result = (
        df.groupby(group_cols, as_index=False)
        .agg(buying_stores=("coded_customer", "nunique"))
    )

    result = spine.merge(result, on=group_cols, how="left")
    result["buying_stores"] = result["buying_stores"].fillna(0)

    return result


def calculate_monthly_active_pods(
    df_filtered,
    df_full,
    group_cols=None,
    selected_years=None,
    selected_months=None,
    include_current_month=True,
    lookback_months=6,
):
    group_cols = clean_group_cols(group_cols)
    non_time_cols = [c for c in group_cols if c != "month_year"]

    selected_periods = None

    if selected_months:
        if all(isinstance(month, pd.Period) for month in selected_months):
            selected_periods = selected_months
        elif selected_years:
            selected_periods = [
                pd.Period(f"{int(year)}-{int(month):02d}", freq="M")
                for year in selected_years
                for month in selected_months
            ]

    spine = build_window_universe_spine(
        df_filtered,
        df_full,
        group_cols=non_time_cols,
        selected_years=selected_years,
        selected_months=selected_periods,
        include_current_month=include_current_month,
    )

    full_universe_spine = build_full_universe_spine(
        df_filtered,
        df_full,
        group_cols=non_time_cols,
        selected_years=selected_years,
        selected_months=selected_periods,
        include_current_month=include_current_month,
    )

    rows = []

    for _, spine_row in full_universe_spine.iterrows():
        end_month = spine_row["month_year"]
        start_month = end_month - (lookback_months - 1)

        window = df_full[
            (df_full["month_year"] >= start_month) &
            (df_full["month_year"] <= end_month)
        ]

        for col in non_time_cols:
            window = window[window[col] == spine_row[col]]

        rows.append({
            **{col: spine_row[col] for col in non_time_cols},
            "month_year": end_month,
            "active_pods": window["pod_helper"].nunique(),
        })

    full_df = pd.DataFrame(rows)
    if full_df.empty:
        return pd.DataFrame(columns=group_cols + ["active_pods"])
    
    spine = spine.copy()
    full_df = full_df.copy()

    spine["month_year"] = pd.PeriodIndex(spine["month_year"].astype(str), freq="M")
    full_df["month_year"] = pd.PeriodIndex(full_df["month_year"].astype(str), freq="M")

    result = spine.merge(
        full_df[non_time_cols + ["month_year", "active_pods"]],
        on=non_time_cols + ["month_year"],
        how="left",
    )

    result["active_pods"] = result["active_pods"].fillna(0).astype(int)

    return result[group_cols + ["active_pods"]]


def calculate_monthly_vpo(df_filtered, df_full, group_cols=None, selected_years=None, selected_months=None):
    group_cols = clean_group_cols(group_cols)

    # spine = month_years x group_cols (1 month_year for every group_col in the filtered window)
    # take the max and min month of df_filtered where max month is the last month of the last year in the data 
    # (ie, if it's this year, current month - 1 | if it's 2025, 12/31/2025)
    # fill in all the months in between


    active_pods = calculate_monthly_active_pods(df_filtered, df_full, group_cols, selected_years=selected_years, selected_months=selected_months)
    units = calculate_monthly_units(df_filtered, group_cols)

    result = active_pods.merge(units,
        on = group_cols,
        how = "left"
    )

    result = result.sort_values(group_cols)
    result["units"] = result["units"].fillna(0)

    # FILL IN NAS W 0

    result["vpo"] = (result["units"] / result["active_pods"].replace(0, None) / 4).replace([float("inf"), -float("inf")], None)

    return result[group_cols + ["vpo"]]

def calculate_monthly_existing_buyers(df_filtered, df_full, group_cols=None, selected_years=None, selected_months=None, include_current_month=True):
    group_cols = clean_group_cols(group_cols)

    non_time_cols = [c for c in group_cols if c != "month_year"]

    # FULL UNIVERSE SPINE (key difference)
    spine = build_full_universe_spine(
        df_filtered=df_filtered,
        df_full=df_full,
        group_cols=non_time_cols,
        selected_years=selected_years,
        selected_months=selected_months,
        include_current_month=include_current_month
    )

    store_universe = (
        df_full.groupby(["coded_customer"] + group_cols, as_index=False)
        .agg(
            new_buyer=("first_store_flag", "max"),
        )
    )

    monthly = (
        store_universe.groupby(group_cols, as_index=False)
        .agg(
            new_buyers=("new_buyer", "sum"),
        )
        .sort_values(group_cols)
        .reset_index(drop=True)
    )

    if non_time_cols:
        monthly["total_buyers"] = grouped_cumsum(monthly, "new_buyers", non_time_cols)
    else:
        monthly["total_buyers"] = monthly["new_buyers"].cumsum()

    monthly["existing_buyers"] = monthly["total_buyers"] - monthly["new_buyers"]

    spine["month_year"] = pd.PeriodIndex(spine["month_year"], freq="M")
    monthly["month_year"] = pd.PeriodIndex(monthly["month_year"], freq="M")

    result = spine.merge(
        monthly[group_cols + ["existing_buyers"]],
        on=group_cols,
        how="left",
    ).sort_values(group_cols)

    if non_time_cols:
        result["existing_buyers"] = (
            result.groupby(non_time_cols)["existing_buyers"]
            .ffill()
            .fillna(0)
        )
    else:
        result["existing_buyers"] = result["existing_buyers"].ffill().fillna(0)

    return result[group_cols + ["existing_buyers"]]

def calculate_monthly_repeat_buyers(df_filtered, group_cols=None, selected_years=None, selected_months=None, include_current_month=True):
    group_cols = clean_group_cols(group_cols)

    non_time_cols = [c for c in group_cols if c != "month_year"]

    # NORMAL SPINE
    spine = build_spine(
        df_filtered,
        group_cols=non_time_cols,
        selected_years=selected_years,
        selected_months=selected_months,
        include_current_month=include_current_month
    )

    store_universe = (
        df_filtered.groupby(["coded_customer"] + group_cols, as_index=False)
        .agg(
            repeat_buyer=("reorder_flag", "max"),
        )
    )

    monthly = (
        store_universe.groupby(group_cols, as_index=False)
        .agg(
            repeat_buyers=("repeat_buyer", "sum"),
        )
        .sort_values(group_cols)
        .reset_index(drop=True)
    )

    result = spine.merge(
        monthly[group_cols + ["repeat_buyers"]],
        on=group_cols,
        how="left",
    ).sort_values(group_cols)

    result["repeat_buyers"] = result["repeat_buyers"].fillna(0)

    return result[group_cols + ["repeat_buyers"]]


def calculate_monthly_reorder_rate(df_filtered, df_full, group_cols=None, selected_years=None, selected_months=None, include_current_month=True):

    group_cols = clean_group_cols(group_cols)
    
    non_time_cols = [col for col in group_cols if col != "month_year"]

    spine = build_full_universe_spine(
        df_filtered, 
        df_full, 
        group_cols=non_time_cols, 
        selected_years=selected_years, 
        selected_months=selected_months,
        include_current_month=include_current_month
    )

    store_universe = (
        df_full.groupby(["coded_customer"] + group_cols, as_index=False)
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

    if non_time_cols:
        result["total_buyers"] = grouped_cumsum(result, "new_buyers", non_time_cols)
    else:
        result["total_buyers"] = result["new_buyers"].cumsum()
    

    result["existing_buyers"] = result["total_buyers"] - result["new_buyers"]

    result = spine.merge(
        result[group_cols + ["repeat_buyers","existing_buyers"]],
        on=group_cols,
        how="left",
    )

    result = result.sort_values(group_cols)

    if non_time_cols:
        result["existing_buyers"] = (
            result.groupby(non_time_cols)["existing_buyers"]
            .ffill()
            .fillna(0)
        )
    else:
        result["existing_buyers"] = result["existing_buyers"].ffill().fillna(0)

    result["repeat_buyers"] = result["repeat_buyers"].fillna(0)

    result["reorder_rate"] = calculate_reorder_rate(result)

    return result[group_cols + ["reorder_rate"]]

def calculate_monthly_new_pods(df, group_cols):
    group_cols = clean_group_cols(group_cols)

    result = (
        df.groupby(group_cols, as_index=False)
        .agg(new_pods=("first_pod_flag", "sum"))
    )

    return result

def calculate_monthly_average_skus_per_store(df, group_cols):
    group_cols = clean_group_cols(group_cols)

    store_level = (
        df.groupby(["coded_customer"] + group_cols, as_index=False)
        .agg(skus=("sku", "nunique"))
    )

    result = (
        store_level.groupby(group_cols, as_index=False)
        .agg(average_skus_per_store=("skus", "mean"))
    )

    return result
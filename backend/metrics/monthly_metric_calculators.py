# PROB MOVE THESE TWO FUNCTIONS SOMEWHERE ELSE

from backend.metrics.metric_helpers import (grouped_cumsum, build_spine, build_full_universe_spine)
from datetime import datetime

def calculate_reorder_rate(df):
    result = df["repeat_buyers"] / df["existing_buyers"]
    return result.replace([float("inf"), -float("inf")], None)

# ------------------------------------------------------------------------

def calculate_monthly_revenue(df, group_cols=None):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    if "month_year" not in group_cols:
        group_cols = ["month_year"] + group_cols

    result = (
        df.groupby(group_cols, as_index=False)
        .agg(revenue=("revenue", "sum"))
    )

    return result

def calculate_monthly_units(df, group_cols=None):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    if "month_year" not in group_cols:
        group_cols = ["month_year"] + group_cols

    result = (
        df.groupby(group_cols, as_index=False)
        .agg(units=("units", "sum"))
    )

    return result

def calculate_monthly_buying_stores(df, group_cols=None):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    if "month_year" not in group_cols:
        group_cols = ["month_year"] + group_cols

    result = (
        df.groupby(group_cols, as_index=False)
        .agg(buying_stores=("coded_customer", "nunique"))
    )

    return result

def calculate_monthly_active_pods(df_filtered, df_full, group_cols=None, selected_years=None, selected_months=None):
    if group_cols is None:
        group_cols = []
    elif isinstance(group_cols, str):
        group_cols = [group_cols]
    
    if "month_year" in group_cols:
        group_cols = [c for c in group_cols if c != "month_year"] + ["month_year"]
    else:
        group_cols = group_cols + ["month_year"]
    
    non_time_cols = [col for col in group_cols if col != "month_year"]

    spine = build_full_universe_spine(
        df_filtered, 
        df_full, 
        group_cols=non_time_cols, 
        selected_years=selected_years, 
        selected_months=selected_months
    )


    clone = (
        df_full.groupby(group_cols, as_index=False)
        .agg(new_pods=("first_pod_flag", "sum"))
        .sort_values(group_cols)
    )

    if non_time_cols:
        clone["active_pods"] = grouped_cumsum(clone, "new_pods", non_time_cols)
    else:
        clone["active_pods"] = clone["new_pods"].cumsum()

    result = spine.merge(
        clone[group_cols + ["active_pods"]],
        on=group_cols,
        how="left"
        )
    
    if non_time_cols:
        result["active_pods"] = (
            result.groupby(non_time_cols)["active_pods"]
            .ffill()
            .fillna(0)
        )
    else:
        result["active_pods"] = result["active_pods"].ffill().fillna(0)

    
    return result[group_cols + ["active_pods"]]


def calculate_monthly_vpo(df_filtered, df_full, group_cols=None):
    if group_cols is None:
        group_cols = []
    elif isinstance(group_cols, str):
        group_cols = [group_cols]

    if "month_year" not in group_cols:
        group_cols = ["month_year"] + group_cols

    
    # spine = month_years x group_cols (1 month_year for every group_col in the filtered window)
    # take the max and min month of df_filtered where max month is the last month of the last year in the data 
    # (ie, if it's this year, current month - 1 | if it's 2025, 12/31/2025)
    # fill in all the months in between


    active_pods = calculate_monthly_active_pods(df_filtered, df_full, group_cols)
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

def calculate_monthly_existing_buyers(df_filtered, df_full, group_cols=None, selected_years=None, selected_months=None):
    if group_cols is None:
        group_cols = []
    elif isinstance(group_cols, str):
        group_cols = [group_cols]

    if "month_year" in group_cols:
        group_cols = [c for c in group_cols if c != "month_year"] + ["month_year"]
    else:
        group_cols = group_cols + ["month_year"]

    non_time_cols = [c for c in group_cols if c != "month_year"]

    # FULL UNIVERSE SPINE (key difference)
    spine = build_full_universe_spine(
        df_filtered=df_filtered,
        df_full=df_full,
        group_cols=non_time_cols,
        selected_years=selected_years,
        selected_months=selected_months,
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

def calculate_monthly_repeat_buyers(df_filtered, group_cols=None, selected_years=None, selected_months=None):
    if group_cols is None:
        group_cols = []
    elif isinstance(group_cols, str):
        group_cols = [group_cols]

    if "month_year" in group_cols:
        group_cols = [c for c in group_cols if c != "month_year"] + ["month_year"]
    else:
        group_cols = group_cols + ["month_year"]

    non_time_cols = [c for c in group_cols if c != "month_year"]

    # NORMAL SPINE
    spine = build_spine(
        df_filtered,
        group_cols=non_time_cols,
        selected_years=selected_years,
        selected_months=selected_months,
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


def calculate_monthly_reorder_rate(df_filtered, df_full, group_cols=None, selected_years=None, selected_months=None):

    if group_cols is None:
        group_cols = []
    elif isinstance(group_cols, str):
        group_cols = [group_cols]

    # Ensures that month_year is in the right order for the sorting before the cumsum

    if "month_year" in group_cols:
        group_cols = [c for c in group_cols if c != "month_year"] + ["month_year"]
    else:
        group_cols = group_cols + ["month_year"]
    
    non_time_cols = [col for col in group_cols if col != "month_year"]

    spine = build_full_universe_spine(
        df_filtered, 
        df_full, 
        group_cols=non_time_cols, 
        selected_years=selected_years, 
        selected_months=selected_months
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
        how="left"
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
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    if "month_year" not in group_cols:
        group_cols = ["month_year"] + group_cols

    result = (
        df.groupby(group_cols, as_index=False)
        .agg(new_pods=("first_pod_flag", "sum"))
    )

    return result

def calculate_monthly_average_skus_per_store(df, group_cols):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    if "month_year" not in group_cols:
        group_cols = ["month_year"] + group_cols

    store_level = (
        df.groupby(["coded_customer"] + group_cols, as_index=False)
        .agg(skus=("sku", "nunique"))
    )

    result = (
        store_level.groupby(group_cols, as_index=False)
        .agg(average_skus_per_store=("skus", "mean"))
    )

    return result
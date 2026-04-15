import numpy as np
import pandas as pd

from backend.metrics.metric_helpers import ensure_month_spine

def calculate_revenue(df, group_cols):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    result = (
        df.groupby(group_cols, as_index=False)
        .agg(revenue=("revenue", "sum"))
    )

    return result

def calculate_units(df, group_cols):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    result = (
        df.groupby(group_cols, as_index=False)
        .agg(units=("units", "sum"))
    )

    return result

def calculate_buying_stores(df, group_cols):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    result = (
        df.groupby(group_cols, as_index=False)
        .agg(buying_stores=("coded_customer", "nunique"))
    )

    return result

def calculate_active_pods(df, group_cols):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    result = (
        df.groupby(group_cols, as_index=False)
        .agg(active_pods=("pod_helper", "nunique"))
    )

    return result


def calculate_vpo(df, group_cols):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    # this metric should aggregate over time, so keep month_year separate
    group_cols = [c for c in group_cols if c != "month_year"]
    monthly_group_cols = group_cols + ["month_year"]

    # build monthly table at the grouped level
    units = (
        df.groupby(monthly_group_cols, as_index=False)
        .agg(units=("units", "sum"))
    )

    new_pods = (
        df.groupby(monthly_group_cols, as_index=False)
        .agg(new_pods=("first_pod_flag", "sum"))
    )

    result = units.merge(new_pods, on=monthly_group_cols, how="outer")

    result = result.sort_values(monthly_group_cols).reset_index(drop=True)

    # active pod base = cumulative new pods
    if group_cols:
        result["active_pods"] = result.groupby(group_cols)["new_pods"].cumsum()

        total_pod_months = (
            result.groupby(group_cols, as_index=False)
            .agg(pod_months=("active_pods", "sum"))
        )

        total_units = (
            result.groupby(group_cols, as_index=False)
            .agg(units=("units", "sum"))
        )
    
        final = total_units.merge(total_pod_months, on=group_cols, how="left")


    else:
        result["active_pods"] = result["new_pods"].cumsum()

        final = pd.DataFrame(
            {
                "units": [result["units"].sum()],
                "pod_months": [result["active_pods"].sum()],
            }
        )


    # denominator = total pod-month opportunities

    final["vpo"] = final["units"] / final["pod_months"].replace(0, None) / 4

    return final[group_cols + ["vpo"]]

def calculate_reorder_rate(df, group_cols):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    current_month = pd.Timestamp.today().to_period("M")
    latest_full_month = df.loc[df["month_year"] != current_month, "month_year"].max()

    store_keys = [c for c in group_cols if c != "coded_customer"] + ["coded_customer"]

    store_universe = (
        df.groupby(store_keys + ["month_year"], as_index=False)
        .agg(
            repeat_buyer=("reorder_flag", "max"),
            new_buyer=("first_store_flag", "max"),
        )
    )

    store_start = (
        store_universe.groupby(store_keys, as_index=False)
        .agg(first_month=("month_year", "min"))
    )

    #Use ordinal below to convert a Series to an int
    store_start["possible_reorders"] = (
        latest_full_month.ordinal - store_start["first_month"].astype(int).clip(lower=0)
        )

    total_possible_reorders = (
        store_start.groupby(group_cols, as_index=False)
        .agg(possible_reorders=("possible_reorders", "sum"))
    )

    repeat_buyers = (
        store_universe.groupby(group_cols, as_index=False)
        .agg(repeat_buyers=("repeat_buyer", "sum"))
    )

    result = repeat_buyers.merge(
        total_possible_reorders,
        on=group_cols,
        how="left"
    )

    result["reorder_rate"] = (
        result["repeat_buyers"] / result["possible_reorders"]
    ).replace([np.inf, -np.inf], np.nan)

    return result[group_cols + ["reorder_rate"]]

def calculate_new_pods(df, group_cols):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    result = (
        df.groupby(group_cols, as_index=False)
        .agg(new_pods=("first_pod_flag", "sum"))
    )

    return result


def calculate_average_skus_per_store(df, group_cols):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    # Step 1: store-level SKU counts
    store_skus = (
        df.groupby(group_cols + ["coded_customer"], as_index=False)
        .agg(skus_per_store=("sku", "nunique"))
    )

    # Step 2: average across stores
    result = (
        store_skus.groupby(group_cols, as_index=False)
        .agg(average_skus_per_store=("skus_per_store", "mean"))
    )

    return result
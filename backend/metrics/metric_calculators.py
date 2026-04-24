import numpy as np
import pandas as pd

from backend.metrics.metric_helpers import build_spine, build_full_universe_spine, clean_group_cols
from backend.metrics.monthly_metric_calculators import calculate_monthly_active_pods, calculate_monthly_units

def calculate_revenue(df, group_cols=None):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    result = (
        df.groupby(group_cols, as_index=False)
        .agg(revenue=("revenue", "sum"))
    )

    return result

def calculate_units(df, group_cols=None):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    if not group_cols:
        return df["units"].sum()

    # if group_cols exist

    result = (
        df.groupby(group_cols, as_index=False)
        .agg(units=("units", "sum"))
    )

    return result


def calculate_buying_stores(df, group_cols=None):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    if not group_cols:
        return df["coded_customer"].nunique()

    result = (
        df.groupby(group_cols, as_index=False)
        .agg(buying_stores=("coded_customer", "nunique"))
    )

    return result

def calculate_active_pods(
    df_filtered,
    df_full,
    group_cols=None,
    selected_years=None,
    selected_months=None,
    include_current_month=True,
):
    group_cols = clean_group_cols(group_cols)
    non_time_cols = [c for c in group_cols if c != "month_year"]

    monthly = calculate_monthly_active_pods(
        df_filtered=df_filtered,
        df_full=df_full,
        group_cols=non_time_cols,
        selected_years=selected_years,
        selected_months=selected_months,
        include_current_month=include_current_month,
        lookback_months=6,
    )

    latest_month = monthly["month_year"].max()
    result = monthly[monthly["month_year"] == latest_month].copy()

    # returns value as int if no group_cols
    if not non_time_cols:
        val = result["active_pods"].iloc[0] if not result.empty else None
        return int(val) if pd.notna(val) else None

    return result[non_time_cols + ["active_pods"]]



def calculate_vpo(
    df_filtered,
    df_full,
    group_cols=None,
    selected_years=None,
    selected_months=None,
):
    group_cols = clean_group_cols(group_cols)
    non_time_cols = [c for c in group_cols if c != "month_year"]

    monthly_units = calculate_monthly_units(
        df=df_filtered,
        group_cols=non_time_cols,
        selected_years=selected_years,
        selected_months=selected_months,
        include_current_month=False,
    )

    monthly_active_pods = calculate_monthly_active_pods(
        df_filtered=df_filtered,
        df_full=df_full,
        group_cols=non_time_cols,
        selected_years=selected_years,
        selected_months=selected_months,
        include_current_month=False,
    )

    result = monthly_units.merge(
        monthly_active_pods,
        on=non_time_cols + ["month_year"],
        how="left",
    )

    result["units"] = result["units"].fillna(0)
    result["active_pods"] = result["active_pods"].fillna(0)

    if non_time_cols:
        final = (
            result.groupby(non_time_cols, as_index=False)
            .agg(
                units=("units", "sum"),
                pod_months=("active_pods", "sum"),
            )
        )
    else:
        final = pd.DataFrame({
            "units": [result["units"].sum()],
            "pod_months": [result["active_pods"].sum()],
        })

    final["vpo"] = (
        final["units"] / final["pod_months"].replace(0, pd.NA) / 4
    ).replace([float("inf"), -float("inf")], None)

    if not non_time_cols:
        val = final["vpo"].iloc[0] if not final.empty else None
        return float(val) if pd.notna(val) else None

    return final[non_time_cols + ["vpo"]]


def calculate_reorder_rate(df_filtered, df_full, group_cols=None, selected_years=None, selected_months=None):
    if group_cols is None:
        group_cols = []
    elif isinstance(group_cols, str):
        group_cols = [group_cols]

    group_cols = [c for c in group_cols if c not in ["month_year", "coded_customer"]]
    store_keys = group_cols + ["coded_customer"]
    monthly_group_cols = group_cols + ["month_year"]

    spine = build_full_universe_spine(
        df_filtered,
        df_full,
        group_cols=group_cols,
        selected_years=selected_years,
        selected_months=selected_months
    )

    # numerator from filtered activity
    store_universe_filtered = (
        df_filtered.groupby(store_keys + ["month_year"], as_index=False)
        .agg(repeat_buyer=("reorder_flag", "max"))
    )

    if group_cols:
        numerator = (
            store_universe_filtered.groupby(monthly_group_cols, as_index=False)
            .agg(repeat_buyers=("repeat_buyer", "sum"))
            .sort_values(monthly_group_cols)
            .reset_index(drop=True)
        )
    else:
        numerator = (
            store_universe_filtered.groupby("month_year", as_index=False)
            .agg(repeat_buyers=("repeat_buyer", "sum"))
            .sort_values("month_year")
            .reset_index(drop=True)
        )

    # denominator from full-history store eligibility
    store_start = (
        df_full.groupby(store_keys, as_index=False)
        .agg(first_month=("month_year", "min"))
    )

    store_month_frame = build_full_universe_spine(
        df_filtered,
        df_full,
        group_cols=store_keys
    )

    store_month_frame = store_month_frame.merge(
        store_start,
        on=store_keys,
        how="left"
    )

    store_month_frame["reorder_opportunity"] = (
        store_month_frame["month_year"] > store_month_frame["first_month"]
    ).astype(int)

    if group_cols:
        denominator = (
            store_month_frame.groupby(monthly_group_cols, as_index=False)
            .agg(possible_reorders=("reorder_opportunity", "sum"))
            .sort_values(monthly_group_cols)
            .reset_index(drop=True)
        )
    else:
        denominator = (
            store_month_frame.groupby("month_year", as_index=False)
            .agg(possible_reorders=("reorder_opportunity", "sum"))
            .sort_values("month_year")
            .reset_index(drop=True)
        )

    result = spine.merge(
        denominator,
        on=monthly_group_cols if group_cols else "month_year",
        how="left",
    )

    result["possible_reorders"] = result["possible_reorders"].fillna(0)

    result = result.merge(
        numerator,
        on=monthly_group_cols if group_cols else "month_year",
        how="left",
    )

    result["repeat_buyers"] = result["repeat_buyers"].fillna(0)

    if group_cols:
        final = (
            result.groupby(group_cols, as_index=False)
            .agg(
                repeat_buyers=("repeat_buyers", "sum"),
                possible_reorders=("possible_reorders", "sum"),
            )
        )
    else:
        final = pd.DataFrame(
            {
                "repeat_buyers": [result["repeat_buyers"].sum()],
                "possible_reorders": [result["possible_reorders"].sum()],
            }
        )

    final["reorder_rate"] = (
        final["repeat_buyers"] / final["possible_reorders"]
    ).replace([np.inf, -np.inf], np.nan)

    if not group_cols:
        val = final["reorder_rate"].iloc[0] if not final.empty else None
        return float(val) if pd.notna(val) else None

    return final[group_cols + ["reorder_rate"]]

def calculate_new_pods(df, group_cols):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    result = (
        df.groupby(group_cols, as_index=False)
        .agg(new_pods=("first_pod_flag", "sum"))
    )

    return result


def calculate_average_skus_per_store(df, group_cols=None):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    # no grouping case
    if not group_cols:
        store_skus = (
            df.groupby("coded_customer", as_index=False)
            .agg(skus_per_store=("sku", "nunique"))
        )

        return store_skus["skus_per_store"].mean()

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
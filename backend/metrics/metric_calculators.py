import numpy as np
import pandas as pd

from backend.metrics.metric_helpers import clean_group_cols, clean_group_cols_new


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
    active_pods_df,
    group_cols=None,
):
    """
    Calculate active PODs from the precomputed active_pods_df.

    active_pods_df already contains one row per active
    POD/month/filter-dimension combination.
    """

    if group_cols is None:
        group_cols = []

    if isinstance(group_cols, str):
        group_cols = [group_cols]

    if not group_cols:
        return active_pods_df["pod_helper"].nunique()

    result = (
        active_pods_df
        .groupby(
            group_cols,
            as_index=False,
        )["pod_helper"]
        .nunique()
        .rename(
            columns={
                "pod_helper": "active_pods",
            }
        )
    )

    return result

def calculate_active_pod_opportunities(active_pods_df, group_cols=None):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    group_cols = group_cols or []

    if not group_cols:
        return len(active_pods_df)

    return (
        active_pods_df
        .groupby(group_cols, dropna=False)
        .size()
        .reset_index(name="active_pod_opportunities")
    )


def calculate_velocity(df_filtered, active_pods_df, group_cols=None):
    group_cols = clean_group_cols_new(group_cols)

    opportunities = calculate_active_pod_opportunities(active_pods_df=active_pods_df, group_cols=group_cols)

    if not group_cols:
        if opportunities == 0:
            return None
        units = calculate_units(df_filtered)
        return float(units / opportunities / 4)

    units = calculate_units(df_filtered, group_cols=group_cols)

    result = opportunities.merge(units, on=group_cols, how="left")
    result["units"] = result["units"].fillna(0)
    result["vpo"] = result["units"] / result["active_pod_opportunities"].replace(0, pd.NA) / 4

    return result[group_cols + ["vpo"]]


def calculate_store_reorder_rate(active_pods_df, group_cols=None):
    if group_cols is None:
        group_cols = []

    if isinstance(group_cols, str):
        group_cols = [group_cols]

    store_month_grouping = list(dict.fromkeys([
        "month_year",
        *group_cols,
        "coded_customer",
    ]))

    store_month = (
        active_pods_df
        .groupby(
            store_month_grouping,
            as_index=False,
            dropna=False,
        )
        .agg(
            could_reorder=("could_reorder", "max"),
            ordered=("ordered", "max"),
        )
    )

    eligible = store_month[
        store_month["could_reorder"]
    ].copy()

    if group_cols:
        result = (
            eligible
            .groupby(
                group_cols,
                as_index=False,
                dropna=False,
            )
            .agg(
                reorder_opportunities=("coded_customer", "size"),
                reorders=("ordered", "sum"),
            )
        )

        result["reorder_rate"] = (
            result["reorders"]
            / result["reorder_opportunities"]
        )

        return result[group_cols + ["reorder_rate"]]

    reorder_opportunities = len(eligible)

    if reorder_opportunities == 0:
        return None

    return float(
        eligible["ordered"].sum()
        / reorder_opportunities
    )


def calculate_pod_reorder_rate(active_pods_df, group_cols=None):
    if group_cols is None:
        group_cols = []

    if isinstance(group_cols, str):
        group_cols = [group_cols]

    eligible = active_pods_df[
        active_pods_df["could_reorder"]
    ].copy()

    if group_cols:
        result = (
            eligible
            .groupby(
                group_cols,
                as_index=False,
                dropna=False,
            )
            .agg(
                reorder_opportunities=("pod_helper", "size"),
                reorders=("ordered", "sum"),
            )
        )

        result["reorder_rate"] = (
            result["reorders"]
            / result["reorder_opportunities"]
        )

        return result[group_cols + ["reorder_rate"]]

    reorder_opportunities = len(eligible)

    if reorder_opportunities == 0:
        return None

    return float(
        eligible["ordered"].sum()
        / reorder_opportunities
    )

def calculate_new_pods(active_pods_df, group_cols=None):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    new_pods = active_pods_df[
        active_pods_df["ordered"]
        & ~active_pods_df["could_reorder"]
    ]

    if not group_cols:
        return new_pods["pod_helper"].nunique()

    return (
        new_pods.groupby(group_cols, as_index=False)
        .agg(new_pods=("pod_helper", "nunique"))
    )


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

def calculate_skus_selling(df, group_cols=None):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    if not group_cols:
        return df["sku"].nunique()

    return (
        df.groupby(group_cols, as_index=False)
        .agg(skus_selling=("sku", "nunique"))
    )

def calculate_active_skus(active_pods_df, group_cols=None):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    if not group_cols:
        return active_pods_df["sku"].nunique()

    return (
        active_pods_df.groupby(group_cols, as_index=False)
        .agg(active_skus=("sku", "nunique"))
    )
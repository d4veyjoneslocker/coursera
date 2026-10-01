import pandas as pd

from backend.metrics.metric_helpers import (
    get_current_period,
    filter_to_period,
)

from backend.metrics.metric_calculators import (
    calculate_units,
    calculate_buying_stores,
    calculate_active_pods,
    calculate_velocity,
    calculate_store_reorder_rate,
    calculate_new_pods,
    calculate_average_skus_per_store,
)

from backend.metrics.metric_callers import compare_metric


def export_monthly_summary(df, active_pods_df):
    """
    Export one row per completed month.

    Each month is treated as a period and passed to the canonical
    metric calculators.
    """

    current_month = get_current_period(include_current_month=True)

    months = sorted(
        month
        for month in active_pods_df["month_year"].dropna().unique()
        if month != current_month
    )

    rows = []

    for month in months:
        month_df = filter_to_period(df, month, month)
        month_active_pods_df = filter_to_period(
            active_pods_df,
            month,
            month,
        )

        units = calculate_units(month_df, [])
        new_pods = calculate_new_pods(
            month_active_pods_df,
            [],
        )
        active_pods = calculate_active_pods(
            month_active_pods_df,
            [],
        )
        buying_stores = calculate_buying_stores(
            month_df,
            [],
        )
        velocity = calculate_velocity(
            month_df,
            month_active_pods_df,
            [],
        )
        reorder_rate = calculate_store_reorder_rate(
            month_active_pods_df,
            [],
        )
        average_skus_per_store = calculate_average_skus_per_store(
            month_df,
            [],
        )

        rows.append(
            {
                "month_year": month,
                "units": units,
                "new_pods": new_pods,
                "active_pods": active_pods,
                "buying_stores": buying_stores,
                "vpo": velocity,
                "reorder_rate": reorder_rate,
                "average_skus_per_store": average_skus_per_store,
            }
        )

    return pd.DataFrame(rows)


def export_summary_by_grain(df, active_pods_df, grain):
    """
    Export all-time and L3M performance by the requested grain.

    Period-specific metrics and comparisons come from
    compare_metric() rather than dedicated *_3m calculators.
    """

    if isinstance(grain, str):
        grain = [grain]

    result = calculate_units(df, grain)

    result = result.merge(
        calculate_new_pods(
            active_pods_df,
            grain,
        ),
        on=grain,
        how="left",
    )

    result = result.merge(
        calculate_active_pods(
            active_pods_df,
            grain,
        ),
        on=grain,
        how="left",
    )

    result = result.merge(
        calculate_buying_stores(
            df,
            grain,
        ),
        on=grain,
        how="left",
    )

    result = result.merge(
        calculate_velocity(
            df,
            active_pods_df,
            grain,
        ),
        on=grain,
        how="left",
    )

    result = result.merge(
        calculate_store_reorder_rate(
            active_pods_df,
            grain,
        ),
        on=grain,
        how="left",
    )

    result = result.merge(
        calculate_average_skus_per_store(
            df,
            grain,
        ),
        on=grain,
        how="left",
    )

    l3m_metrics = {}

    for metric_name in [
        "units",
        "new_pods",
        "buying_stores",
        "velocity",
        "reorder_rate",
    ]:
        l3m_metrics[metric_name] = compare_metric(
            df=df,
            df_full=df,
            active_pods_df=active_pods_df,
            metric_name=metric_name,
            period="L3M",
            comparison="PP",
            group_cols=grain,
        )

    column_names = {
        "units": "units",
        "new_pods": "new_pods",
        "buying_stores": "buying_stores",
        "velocity": "vpo",
        "reorder_rate": "reorder_rate",
    }

    for metric_name, metric_df in l3m_metrics.items():
        output_name = column_names[metric_name]

        metric_df = metric_df[
            grain + ["value_current", "pct_change"]
        ].rename(
            columns={
                "value_current": f"{output_name}_3m",
                "pct_change": f"{output_name}_l3m_pct",
            }
        )

        result = result.merge(
            metric_df,
            on=grain,
            how="left",
        )

    return result[
        grain
        + [
            "units",
            "new_pods",
            "active_pods",
            "buying_stores",
            "vpo",
            "reorder_rate",
            "average_skus_per_store",
            "units_3m",
            "new_pods_3m",
            "buying_stores_3m",
            "vpo_3m",
            "reorder_rate_3m",
            "units_l3m_pct",
            "new_pods_l3m_pct",
            "buying_stores_l3m_pct",
            "vpo_l3m_pct",
            "reorder_rate_l3m_pct",
        ]
    ]


def export_store_level_table(df, active_pods_df, grain):
    """
    Export store-level performance using the canonical metric architecture.
    """

    if isinstance(grain, str):
        grain = [grain]

    grain = ["coded_customer"] + [
        g for g in grain
        if g != "coded_customer"
    ]

    store_month = (
        df.groupby(
            grain + ["month_year"],
            as_index=False,
        )
        .agg(
            reordered=("reorder_flag", "max"),
        )
    )

    reorders = (
        store_month.groupby(
            grain,
            as_index=False,
        )
        .agg(
            reorders=("reordered", "sum"),
        )
    )

    base_result = (
        df.groupby(
            grain,
            as_index=False,
        )
        .agg(
            chain=("chain", "first"),
            city=("city", "first"),
            state=("state", "first"),
            zip=("zip", "first"),
            channel=("channel", "first"),
            distributor=("distributor", "first"),
            dc=("dc", "first"),
            status=("status", "first"),
            first_month_purchased=("first_month_purchased", "first"),
            last_month_purchased=("last_month_purchased", "first"),
            skus_carrying=("sku", "nunique"),
        )
    )

    base_result = base_result.merge(
        reorders,
        on=grain,
        how="left",
    )

    base_result = base_result.merge(
        calculate_units(
            df,
            grain,
        ),
        on=grain,
        how="left",
    )

    base_result = base_result.merge(
        calculate_velocity(
            df,
            active_pods_df,
            grain,
        ),
        on=grain,
        how="left",
    )

    l3m_metrics = {}

    for metric_name in [
        "units",
        "velocity",
    ]:
        l3m_metrics[metric_name] = compare_metric(
            df=df,
            df_full=df,
            active_pods_df=active_pods_df,
            metric_name=metric_name,
            period="L3M",
            comparison="PP",
            group_cols=grain,
        )

    column_names = {
        "units": "units",
        "velocity": "vpo",
    }

    result = base_result

    for metric_name, metric_df in l3m_metrics.items():
        output_name = column_names[metric_name]

        metric_df = metric_df[
            grain + ["value_current", "pct_change"]
        ].rename(
            columns={
                "value_current": f"{output_name}_3m",
                "pct_change": f"{output_name}_l3m_pct",
            }
        )

        result = result.merge(
            metric_df,
            on=grain,
            how="left",
        )

    return result[
        [
            "coded_customer",
            "chain",
            "city",
            "state",
            "zip",
            "channel",
            "distributor",
            "dc",
            "units",
            "vpo",
            "first_month_purchased",
            "last_month_purchased",
            "status",
            "skus_carrying",
            "reorders",
            "units_3m",
            "vpo_3m",
            "units_l3m_pct",
            "vpo_l3m_pct",
        ]
    ]
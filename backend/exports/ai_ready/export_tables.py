import pandas as pd
from backend.metrics.metric_helpers import get_current_period
from backend.metrics.monthly_metric_calculators import (
    calculate_monthly_units,
    calculate_monthly_buying_stores,
    calculate_monthly_active_pods,
    calculate_monthly_vpo,
    calculate_monthly_reorder_rate,
    calculate_monthly_new_pods,
    calculate_monthly_revenue,
    calculate_monthly_average_skus_per_store,
)

from backend.metrics.metric_calculators import (
    calculate_revenue,
    calculate_units,
    calculate_buying_stores,
    calculate_active_pods,
    calculate_vpo,
    calculate_reorder_rate,
    calculate_new_pods,
    calculate_average_skus_per_store,
)

from backend.metrics.metric_growth_rates import (
    add_additive_metric_3m,
    calculate_buying_stores_3m,
    calculate_reorder_rate_3m,
    calculate_vpo_3m,
    add_prior_month_columns,
    add_pct_change_columns,
)


def export_monthly_summary(df):
    result = calculate_monthly_active_pods(df, df, [])

    print("active_pods base:", len(result), result["month_year"].min(), result["month_year"].max())
    print(result["month_year"].tolist())

    result = result.merge(calculate_monthly_revenue(df, []), on="month_year", how="left")
    result = result.merge(calculate_monthly_units(df, []), on="month_year", how="left")
    result = result.merge(calculate_monthly_new_pods(df, []), on="month_year", how="left")
    result = result.merge(calculate_monthly_buying_stores(df, []), on="month_year", how="left")
    result = result.merge(
        calculate_monthly_vpo(df, df, []), on="month_year", how="left"
    )
    result = result.merge(
        calculate_monthly_reorder_rate(df, df, []), on="month_year", how="left"
    )
    result = result.merge(
        calculate_monthly_average_skus_per_store(df, []), on="month_year", how="left"
    )

    print("post merge:", len(result), result["month_year"].min(), result["month_year"].max())
    print(result["month_year"].tolist())

    result = add_additive_metric_3m(result, [], "revenue")
    result = add_additive_metric_3m(result, [], "units")
    result = add_additive_metric_3m(result, [], "new_pods")

    print("after additive:", len(result), result["month_year"].min(), result["month_year"].max())
    print(result["month_year"].tolist())

    result = result.merge(
        calculate_buying_stores_3m(df, [])[["month_year", "buying_stores_3m"]], 
        on="month_year", 
        how="left"
    )
    result = result.merge(
        calculate_vpo_3m(df, df, [])[["month_year", "vpo_3m"]], 
        on="month_year", 
        how="left"
    )
    result = result.merge(
        calculate_reorder_rate_3m(df, df, [])[["month_year", "reorder_rate_3m"]], 
        on="month_year", 
        how="left"
    )

    print("after all 3m:", len(result), result["month_year"].min(), result["month_year"].max())
    print(result["month_year"].tolist())

    result = add_prior_month_columns(result, [], "revenue", l3m=True)
    result = add_prior_month_columns(result, [], "units", l3m=True)
    result = add_prior_month_columns(result, [], "new_pods", l3m=True)
    result = add_prior_month_columns(result, [], "buying_stores", l3m=True)
    result = add_prior_month_columns(result, [], "vpo", l3m=True)
    result = add_prior_month_columns(result, [], "reorder_rate", l3m=True)

    print("after prior month columns:", len(result), result["month_year"].min(), result["month_year"].max())
    print(result["month_year"].tolist())

    result = add_pct_change_columns(result, "revenue", l3m=True)
    result = add_pct_change_columns(result, "units", l3m=True)
    result = add_pct_change_columns(result, "new_pods", l3m=True)
    result = add_pct_change_columns(result, "buying_stores", l3m=True)
    result = add_pct_change_columns(result, "vpo", l3m=True)
    result = add_pct_change_columns(result, "reorder_rate", l3m=True)

    return result[
        [
            "month_year",
            "revenue",
            "units",
            "new_pods",
            "active_pods",
            "buying_stores",
            "vpo",
            "reorder_rate",
            "average_skus_per_store",
            "revenue_3m",
            "units_3m",
            "new_pods_3m",
            "buying_stores_3m",
            "vpo_3m",
            "reorder_rate_3m",
            "revenue_l3m_pct",
            "units_l3m_pct",
            "new_pods_l3m_pct",
            "buying_stores_l3m_pct",
            "vpo_l3m_pct",
            "reorder_rate_l3m_pct",
        ]
    ]


def export_summary_by_grain(df, grain):
    if isinstance(grain, str):
        grain = [grain]

    result = calculate_revenue(df, grain)
    result = result.merge(calculate_units(df, grain), on=grain, how="left")
    result = result.merge(calculate_new_pods(df, grain), on=grain, how="left")
    result = result.merge(calculate_active_pods(df, df, grain), on=grain, how="left")
    result = result.merge(calculate_buying_stores(df, grain), on=grain, how="left")
    result = result.merge(calculate_vpo(df, df, grain), on=grain, how="left")
    result = result.merge(calculate_reorder_rate(df, df, grain), on=grain, how="left")
    result = result.merge(calculate_average_skus_per_store(df, grain), on=grain, how="left")

    monthly_result = calculate_monthly_revenue(df, grain)
    monthly_result = monthly_result.merge(
        calculate_monthly_units(df, grain), on=grain + ["month_year"], how="left"
    )
    monthly_result = monthly_result.merge(
        calculate_monthly_new_pods(df, grain), on=grain + ["month_year"], how="left"
    )
    monthly_result = monthly_result.merge(
        calculate_monthly_active_pods(df, df, grain), on=grain + ["month_year"], how="left"
    )
    monthly_result = monthly_result.merge(
        calculate_monthly_buying_stores(df, grain), on=grain + ["month_year"], how="left"
    )
    monthly_result = monthly_result.merge(
        calculate_monthly_vpo(df, df, grain), on=grain + ["month_year"], how="left"
    )
    monthly_result = monthly_result.merge(
        calculate_monthly_reorder_rate(df, df, grain), on=grain + ["month_year"], how="left"
    )
    monthly_result = monthly_result.merge(
        calculate_monthly_average_skus_per_store(df, grain), on=grain + ["month_year"], how="left"
    )

    monthly_result = add_additive_metric_3m(monthly_result, grain, "revenue")
    monthly_result = add_additive_metric_3m(monthly_result, grain, "units")
    monthly_result = add_additive_metric_3m(monthly_result, grain, "new_pods")

    monthly_result = monthly_result.merge(
        calculate_buying_stores_3m(df, grain),
        on=grain + ["month_year"],
        how="left",
    )
    monthly_result = monthly_result.merge(
        calculate_vpo_3m(df, df, grain),
        on=grain + ["month_year"],
        how="left",
    )
    monthly_result = monthly_result.merge(
        calculate_reorder_rate_3m(df, df, grain),
        on=grain + ["month_year"],
        how="left",
    )

    monthly_result = add_prior_month_columns(monthly_result, grain, "revenue", l3m=True)
    monthly_result = add_prior_month_columns(monthly_result, grain, "units", l3m=True)
    monthly_result = add_prior_month_columns(monthly_result, grain, "new_pods", l3m=True)
    monthly_result = add_prior_month_columns(monthly_result, grain, "buying_stores", l3m=True)
    monthly_result = add_prior_month_columns(monthly_result, grain, "vpo", l3m=True)
    monthly_result = add_prior_month_columns(monthly_result, grain, "reorder_rate", l3m=True)

    monthly_result = add_pct_change_columns(monthly_result, "revenue", l3m=True)
    monthly_result = add_pct_change_columns(monthly_result, "units", l3m=True)
    monthly_result = add_pct_change_columns(monthly_result, "new_pods", l3m=True)
    monthly_result = add_pct_change_columns(monthly_result, "buying_stores", l3m=True)
    monthly_result = add_pct_change_columns(monthly_result, "vpo", l3m=True)
    monthly_result = add_pct_change_columns(monthly_result, "reorder_rate", l3m=True)

    current_month = get_current_period(include_current_month=True)    
    monthly_result = monthly_result[monthly_result["month_year"] != current_month]

    latest_month = monthly_result["month_year"].max()
    monthly_latest = monthly_result[monthly_result["month_year"] == latest_month].copy()

    monthly_latest = monthly_latest[
        grain
        + [
            "revenue_3m",
            "units_3m",
            "new_pods_3m",
            "buying_stores_3m",
            "vpo_3m",
            "reorder_rate_3m",
            "revenue_l3m_pct",
            "units_l3m_pct",
            "new_pods_l3m_pct",
            "buying_stores_l3m_pct",
            "vpo_l3m_pct",
            "reorder_rate_l3m_pct",
        ]
    ]

    result = result.merge(monthly_latest, on=grain, how="left")

    return result[
        grain
        + [
            "revenue",
            "units",
            "new_pods",
            "active_pods",
            "buying_stores",
            "vpo",
            "reorder_rate",
            "average_skus_per_store",
            "revenue_3m",
            "units_3m",
            "new_pods_3m",
            "buying_stores_3m",
            "vpo_3m",
            "reorder_rate_3m",
            "revenue_l3m_pct",
            "units_l3m_pct",
            "new_pods_l3m_pct",
            "buying_stores_l3m_pct",
            "vpo_l3m_pct",
            "reorder_rate_l3m_pct",
        ]
    ]


def export_store_level_table(df, grain):
    if isinstance(grain, str):
        grain = [grain]

    grain = ["coded_customer"] + [g for g in grain if g != "coded_customer"]

    store_month = (
        df.groupby(grain + ["month_year"], as_index=False)
        .agg(reordered=("reorder_flag", "max"))
    )

    reorders = (
        store_month.groupby(grain, as_index=False)
        .agg(reorders=("reordered", "sum"))
    )

    base_result = (
        df.groupby(grain, as_index=False)
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

    base_result = base_result.merge(reorders, on=grain, how="left")
    base_result = base_result.merge(calculate_revenue(df, grain), on=grain, how="left")
    base_result = base_result.merge(calculate_units(df, grain), on=grain, how="left")
    base_result = base_result.merge(calculate_vpo(df, df, grain), on=grain, how="left")

    monthly_result = calculate_monthly_revenue(df, grain)
    monthly_result = monthly_result.merge(
        calculate_monthly_units(df, grain),
        on=grain + ["month_year"],
        how="left",
    )
    monthly_result = monthly_result.merge(
        calculate_monthly_vpo(df, df, grain),
        on=grain + ["month_year"],
        how="left",
    )

    monthly_result = add_additive_metric_3m(monthly_result, grain, "revenue")
    monthly_result = add_additive_metric_3m(monthly_result, grain, "units")

    monthly_result = monthly_result.merge(
        calculate_vpo_3m(df, df, grain)[grain + ["month_year", "vpo_3m"]],
        on=grain + ["month_year"],
        how="left",
    )

    monthly_result = add_prior_month_columns(monthly_result, grain, "revenue", l3m=True)
    monthly_result = add_prior_month_columns(monthly_result, grain, "units", l3m=True)
    monthly_result = add_prior_month_columns(monthly_result, grain, "vpo", l3m=True)

    monthly_result = add_pct_change_columns(monthly_result, "revenue", l3m=True)
    monthly_result = add_pct_change_columns(monthly_result, "units", l3m=True)
    monthly_result = add_pct_change_columns(monthly_result, "vpo", l3m=True)

    current_month = get_current_period(include_current_month=True)
    monthly_result = monthly_result[monthly_result["month_year"] != current_month]

    latest_month = monthly_result["month_year"].max()
    monthly_latest = monthly_result[monthly_result["month_year"] == latest_month].copy()

    monthly_latest = monthly_latest[
        grain + [
            "revenue_3m",
            "units_3m",
            "vpo_3m",
            "revenue_l3m_pct",
            "units_l3m_pct",
            "vpo_l3m_pct",
        ]
    ]

    result = base_result.merge(monthly_latest, on=grain, how="left")

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
            "revenue",
            "units",
            "vpo",
            "first_month_purchased",
            "last_month_purchased",
            "status",
            "skus_carrying",
            "reorders",
            "revenue_3m",
            "units_3m",
            "vpo_3m",
            "revenue_l3m_pct",
            "units_l3m_pct",
            "vpo_l3m_pct",
        ]
    ]
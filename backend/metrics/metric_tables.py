
import pandas as pd
from backend.metrics.monthly_metric_calculators import calculate_monthly_units, calculate_monthly_active_pods, calculate_monthly_new_pods, calculate_monthly_buying_stores, calculate_monthly_vpo, calculate_monthly_reorder_rate, calculate_monthly_revenue
from backend.metrics.metric_growth_rates import add_additive_metric_3m, calculate_buying_stores_3m, calculate_vpo_3m, calculate_reorder_rate_3m, add_prior_month_columns, add_pct_change_columns, add_abs_change_columns
from backend.metrics.metric_calculators import calculate_units, calculate_revenue, calculate_buying_stores, calculate_vpo


def kpi_monthly_table(df, df_all_time, selected_years=None, selected_months=None):

    # ----------------------------------
    # 1. Build base dataset (NO time filter)
    # ----------------------------------
    # df already has non-time filters applied upstream
    df_base = df  # assuming df = filter_table(df_all_time, non-time filters only)
    


    # ----------------------------------
    # 2. Build full monthly table (with history)
    # ----------------------------------
    result = calculate_monthly_active_pods(df_base, df_all_time, [])
    result = result.merge(calculate_monthly_new_pods(df_base, []), on="month_year", how="left")
    result = result.merge(calculate_monthly_units(df_base, []), on="month_year", how="left")
    result = result.merge(calculate_monthly_buying_stores(df_base, []), on="month_year", how="left")
    result = result.merge(calculate_monthly_vpo(df_base, df_all_time, []), on="month_year", how="left")
    result = result.merge(calculate_monthly_reorder_rate(df_base, df_all_time, []), on="month_year", how="left")


    # ----------------------------------
    # 3. Add rolling metrics (full history)
    # ----------------------------------
    result = add_additive_metric_3m(result, [], "units")
    result = add_additive_metric_3m(result, [], "new_pods")

    result = result.merge(
        calculate_buying_stores_3m(df_base, [])[["month_year", "buying_stores_3m"]],
        on="month_year", how="left"
    )
    result = result.merge(
        calculate_vpo_3m(df_base, df_all_time, [])[["month_year", "vpo_3m"]],
        on="month_year", how="left"
    )
    result = result.merge(
        calculate_reorder_rate_3m(df_base, df_all_time, [])[["month_year", "reorder_rate_3m"]],
        on="month_year", how="left"
    )

    print("after step 3 result:", sorted(result["month_year"].unique()))
    
    # ----------------------------------
    # 4. Add prior period columns (full history)
    # ----------------------------------
    result = add_prior_month_columns(result, [], "units", l1m=True, l3m=True)
    result = add_prior_month_columns(result, [], "new_pods", l1m=True, l3m=True)
    result = add_prior_month_columns(result, [], "buying_stores", l1m=True, l3m=True)
    result = add_prior_month_columns(result, [], "vpo", l1m=True, l3m=True)
    result = add_prior_month_columns(result, [], "reorder_rate", l1m=True, l3m=True)

    print("after step 4:", sorted(result["month_year"].unique()))

    # ----------------------------------
    # 5. Growth calculations
    # ----------------------------------
    result = add_pct_change_columns(result, "units", l1m=True, l3m=True)
    result = add_pct_change_columns(result, "new_pods", l1m=True, l3m=True)
    result = add_pct_change_columns(result, "buying_stores", l1m=True, l3m=True)
    result = add_pct_change_columns(result, "vpo", l1m=True, l3m=True)
    result = add_abs_change_columns(result, "reorder_rate", l1m=True, l3m=True)

    print("after step 5:", sorted(result["month_year"].unique()))

    # ----------------------------------
    # 6. NOW apply time filter (final step)
    # ----------------------------------
    if selected_months:
        result = result[result["month_year"].isin(selected_months)]
    elif selected_years:
        result = result[result["month_year"].apply(lambda p: p.year in selected_years)]

    # ----------------------------------
    # 7. Return final columns
    # ----------------------------------
    return result[
        [
            "month_year",
            "units",
            "new_pods",
            "active_pods",
            "buying_stores",
            "vpo",
            "reorder_rate",
            "units_l1m_pct",
            "new_pods_l1m_pct",
            "buying_stores_l1m_pct",
            "vpo_l1m_pct",
            "reorder_rate_l1m_abs",
            "units_3m",
            "new_pods_3m",
            "buying_stores_3m",
            "vpo_3m",
            "reorder_rate_3m",
            "units_l3m_pct",
            "new_pods_l3m_pct",
            "buying_stores_l3m_pct",
            "vpo_l3m_pct",
            "reorder_rate_l3m_abs"
        ]
    ]

def chain_table(df):

    result = calculate_revenue(df, "chain")
    result = result.merge(calculate_units(df, "chain"), on="chain", how="left")
    result = result.merge(calculate_buying_stores(df, "chain"), on="chain", how="left")
    result = result.merge(calculate_vpo(df, df, "chain"), on="chain", how="left")

    monthly_result = calculate_monthly_units(df, "chain")
    monthly_result = add_additive_metric_3m(monthly_result, "chain", "units")
    monthly_result = add_prior_month_columns(monthly_result, "chain", "units", l1m=True, l3m=True)
    monthly_result = add_pct_change_columns(monthly_result, "units", l1m=True, l3m=True)

    current_month = pd.Timestamp.today().to_period("M")
    monthly_result = monthly_result[monthly_result["month_year"] != current_month]

    latest_month = monthly_result["month_year"].max()
    monthly_latest = monthly_result[monthly_result["month_year"] == latest_month].copy()

    monthly_latest = monthly_latest[["chain", "units_l1m_pct", "units_l3m_pct"]]

    result = result.merge(monthly_latest, on="chain", how="left")
    result = result.sort_values("units", ascending=False)

    return result[[
        "chain",
        "units",
        "revenue",
        "buying_stores",
        "vpo",
        "units_l1m_pct",
        "units_l3m_pct",
        ]]

def store_performance(df, df_all_time):

    grain = ["coded_customer"] + ["chain"]

    store_month = (
        df.groupby(grain + ["month_year"], as_index=False)
        .agg(reordered=("reorder_flag", "max"))
    )

    reorders = (
        store_month.groupby(grain, as_index=False)
        .agg(reorders=("reordered", "sum"))
    )

    base_result = (
        df.groupby("coded_customer", as_index=False)
        .agg(
            chain =("chain", "first"),
            status=("status", "first"),
            first_month_purchased=("first_month_purchased", "first"),
            last_month_purchased=("last_month_purchased", "first"),
        )
    )

    base_result = base_result.merge(reorders, on=grain, how="left")
    base_result = base_result.merge(calculate_revenue(df, grain), on=grain, how="left")
    base_result = base_result.merge(calculate_units(df, grain), on=grain, how="left")
    base_result = base_result.merge(calculate_vpo(df, df_all_time, group_cols=grain), on=grain, how="left")

    monthly_result = calculate_monthly_revenue(df, grain)
    monthly_result = monthly_result.merge(
        calculate_monthly_units(df, grain),
        on=grain + ["month_year"],
        how="left",
    )

    monthly_result = add_additive_metric_3m(monthly_result, grain, "revenue")
    monthly_result = add_additive_metric_3m(monthly_result, grain, "units")


    monthly_result = add_prior_month_columns(monthly_result, grain, "revenue", l3m=True)
    monthly_result = add_prior_month_columns(monthly_result, grain, "units", l3m=True)

    monthly_result = add_pct_change_columns(monthly_result, "revenue", l3m=True)
    monthly_result = add_pct_change_columns(monthly_result, "units", l3m=True)

    current_month = pd.Timestamp.today().to_period("M")
    monthly_result = monthly_result[monthly_result["month_year"] != current_month]

    latest_month = monthly_result["month_year"].max()
    monthly_latest = monthly_result[monthly_result["month_year"] == latest_month].copy()

    monthly_latest = monthly_latest[
        ["coded_customer"] + [
            "revenue_l3m_pct",
            "units_l3m_pct",
        ]
    ]

    result = base_result.merge(monthly_latest, on="coded_customer", how="left")

    result = result.sort_values("units", ascending=False)

    return result[[
        "coded_customer",
        "units",
        "revenue",
        "reorders",
        "vpo",
        "first_month_purchased",
        "last_month_purchased",
        "status"
    ]]

# this is for status pie chart
def status_counts_dict(df):
    store_status = (
        df.groupby("coded_customer", as_index=False)
        .agg(status=("status", "first"))
    )

    result = (
        store_status["status"]
        .value_counts()
        .to_dict()
    )

    return {
        "Healthy": int(result.get("Healthy", 0)),
        "Struggling": int(result.get("Struggling", 0)),
        "Revived": int(result.get("Revived", 0)),
        "Inactive": int(result.get("Inactive", 0)),
        "New": int(result.get("New", 0)),
    }
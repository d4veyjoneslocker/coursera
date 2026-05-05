
import pandas as pd
from backend.metrics.monthly_metric_calculators import calculate_monthly_units, calculate_monthly_active_pods, calculate_monthly_new_pods, calculate_monthly_buying_stores, calculate_monthly_vpo, calculate_monthly_reorder_rate, calculate_monthly_revenue
from backend.metrics.metric_growth_rates import add_additive_metric_3m, calculate_buying_stores_3m, calculate_vpo_3m, calculate_reorder_rate_3m, add_prior_month_columns, add_pct_change_columns, add_abs_change_columns
from backend.metrics.metric_calculators import calculate_units, calculate_revenue, calculate_buying_stores, calculate_vpo, calculate_store_table_vpo


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
    result = result.merge(calculate_monthly_units(df_base, selected_years=selected_years, selected_months=selected_months), on="month_year", how="left")
    result = result.merge(calculate_monthly_buying_stores(df_base, selected_years=selected_years, selected_months=selected_months), on="month_year", how="left")
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
    
    # ----------------------------------
    # 4. Add prior period columns (full history)
    # ----------------------------------
    result = add_prior_month_columns(result, [], "units", l1m=True, l3m=True)
    result = add_prior_month_columns(result, [], "new_pods", l1m=True, l3m=True)
    result = add_prior_month_columns(result, [], "buying_stores", l1m=True, l3m=True)
    result = add_prior_month_columns(result, [], "vpo", l1m=True, l3m=True)
    result = add_prior_month_columns(result, [], "reorder_rate", l1m=True, l3m=True)

    # ----------------------------------
    # 5. Growth calculations
    # ----------------------------------
    result = add_pct_change_columns(result, "units", l1m=True, l3m=True)
    result = add_pct_change_columns(result, "new_pods", l1m=True, l3m=True)
    result = add_pct_change_columns(result, "buying_stores", l1m=True, l3m=True)
    result = add_pct_change_columns(result, "vpo", l1m=True, l3m=True)
    result = add_abs_change_columns(result, "reorder_rate", l1m=True, l3m=True)

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
    grain = ["coded_customer", "chain"]

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
            status=("status", "first"),
            first_month_purchased=("first_month_purchased", "first"),
            last_month_purchased=("last_month_purchased", "first"),
        )
    )

    revenue = calculate_revenue(df, grain)
    units = calculate_units(df, grain)
    vpo = calculate_store_table_vpo(df_all_time, group_cols=grain)

    result = (
        base_result
        .merge(reorders, on=grain, how="left")
        .merge(revenue, on=grain, how="left")
        .merge(units, on=grain, how="left")
        .merge(vpo, on=grain, how="left")
    )

    result = result.sort_values("units", ascending=False)

    return result[
        [
            "coded_customer",
            "chain",
            "units",
            "revenue",
            "reorders",
            "vpo",
            "first_month_purchased",
            "last_month_purchased",
            "status",
        ]
    ]

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

def chain_insight_table(df):
    monthly_result = calculate_monthly_units(df, "chain")
    monthly_result = add_additive_metric_3m(monthly_result, "chain", "units")
    monthly_result = add_prior_month_columns(monthly_result, "chain", "units", l3m=True)
    monthly_result = add_pct_change_columns(monthly_result, "units", l3m=True)
    monthly_result = add_abs_change_columns(monthly_result, "units", l3m=True)

    current_month = pd.Timestamp.today().to_period("M")
    monthly_result = monthly_result[monthly_result["month_year"] != current_month]

    latest_month = monthly_result["month_year"].max()
    monthly_latest = monthly_result[monthly_result["month_year"] == latest_month].copy()

    return monthly_latest[
        [
            "chain",
            "units_3m",
            "units_l3m",
            "units_l3m_pct",
            "units_l3m_abs",
        ]
    ]

def sku_insight_table(df):
    monthly_units = calculate_monthly_units(df, "sku")
    monthly_vpo = calculate_vpo_3m(df, df, "sku")

    monthly_result = monthly_units.merge(
        monthly_vpo,
        on=["sku", "month_year"],
        how="left",
    )

    monthly_result = add_additive_metric_3m(monthly_result, "sku", "units")
    monthly_result = add_prior_month_columns(monthly_result, "sku", "units", l3m=True)

    monthly_result = add_prior_month_columns(monthly_result, "sku", "vpo", l3m=True)
    monthly_result = add_pct_change_columns(monthly_result, "vpo", l3m=True)
    monthly_result = add_abs_change_columns(monthly_result, "vpo", l3m=True)

    current_month = pd.Timestamp.today().to_period("M")
    monthly_result = monthly_result[monthly_result["month_year"] != current_month]

    latest_month = monthly_result["month_year"].max()
    monthly_latest = monthly_result[monthly_result["month_year"] == latest_month].copy()

    monthly_latest = monthly_latest.dropna(subset=["vpo_3m", "vpo_l3m"])

    return monthly_latest[
        [
            "sku",
            "units_3m",
            "units_l3m",
            "vpo_3m",
            "vpo_l3m",
            "vpo_l3m_pct",
            "vpo_l3m_abs",
        ]
    ]

def channel_reorder_insight_table(df, df_all_time):
    df = df.copy()
    df_all_time = df_all_time.copy()

    df = df[df["month_year"].notna()]
    df_all_time = df_all_time[df_all_time["month_year"].notna()]

    df = df[df["channel"].notna()]
    df_all_time = df_all_time[df_all_time["channel"].notna()]

    monthly = calculate_reorder_rate_3m(df, df_all_time, "channel")

    buying_stores = calculate_buying_stores_3m(df, "channel")

    monthly = monthly.merge(
        buying_stores[["channel", "month_year", "buying_stores_3m"]],
        on=["channel", "month_year"],
        how="left",
    )

    monthly = add_prior_month_columns(
        monthly,
        "channel",
        "reorder_rate",
        l3m=True,
    )

    monthly = add_prior_month_columns(
        monthly,
        "channel",
        "buying_stores",
        l3m=True,
    )

    monthly = add_abs_change_columns(
        monthly,
        "reorder_rate",
        l3m=True,
    )

    current_month = pd.Timestamp.today().to_period("M")
    monthly = monthly[monthly["month_year"] != current_month]

    latest_month = monthly["month_year"].max()
    latest = monthly[monthly["month_year"] == latest_month].copy()

    return latest.dropna(subset=["reorder_rate_3m", "reorder_rate_l3m"])[
        [
            "channel",
            "reorder_rate_3m",
            "reorder_rate_l3m",
            "reorder_rate_l3m_abs",
            "buying_stores_3m",
            "buying_stores_l3m",
        ]
    ]

def chain_sku_velocity_gap_opportunity_table(df, df_all_time):
    df = df.copy()
    df_all_time = df_all_time.copy()

    df["month_year"] = pd.PeriodIndex(df["month_year"].astype(str), freq="M")
    df_all_time["month_year"] = pd.PeriodIndex(df_all_time["month_year"].astype(str), freq="M")

    grain = ["channel", "sku", "chain"]

    monthly_vpo = calculate_vpo_3m(df, df_all_time, grain)
    buying_stores = calculate_buying_stores_3m(df, grain)
    units = calculate_monthly_units(df, grain)

    monthly = (
        monthly_vpo
        .merge(
            buying_stores[grain + ["month_year", "buying_stores_3m"]],
            on=grain + ["month_year"],
            how="left",
        )
        .merge(
            units,
            on=grain + ["month_year"],
            how="left",
        )
    )

    monthly = add_additive_metric_3m(monthly, grain, "units")

    current_month = pd.Timestamp.today().to_period("M")
    monthly = monthly[monthly["month_year"] != current_month]

    if monthly.empty:
        return monthly

    latest_month = monthly["month_year"].max()
    latest = monthly[monthly["month_year"] == latest_month].copy()

    return latest.dropna(
        subset=["channel", "sku", "chain", "vpo_3m", "buying_stores_3m", "units_3m"]
    )[
        [
            "channel",
            "sku",
            "chain",
            "month_year",
            "vpo_3m",
            "buying_stores_3m",
            "units_3m",
        ]
    ]

def top_sales_month_insight_table(df, df_all_time):
    monthly = kpi_monthly_table(
        df=df,
        df_all_time=df_all_time,
        selected_years=None,
        selected_months=None,
    )

    monthly = monthly[[
        "month_year",
        "units",
        "buying_stores",
        "vpo",
        "reorder_rate",
    ]].copy()

    current_month = pd.Timestamp.today().to_period("M")
    monthly = monthly[monthly["month_year"] != current_month]

    return monthly
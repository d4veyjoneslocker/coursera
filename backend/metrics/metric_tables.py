
import pandas as pd
import time
from backend.metrics.monthly_metric_calculators import calculate_monthly_units, calculate_monthly_active_pods, calculate_monthly_new_pods, calculate_monthly_buying_stores, calculate_monthly_vpo, calculate_monthly_reorder_rate, calculate_monthly_revenue
from backend.metrics.metric_growth_rates import add_additive_metric_3m, calculate_buying_stores_3m, calculate_vpo_3m, calculate_reorder_rate_3m, add_prior_month_columns, add_pct_change_columns, add_abs_change_columns
from backend.metrics.metric_calculators import calculate_units, calculate_revenue, calculate_buying_stores, calculate_vpo, calculate_store_table_vpo
from backend.metrics.metric_helpers import calculate_avg_skus_per_store, resolve_period, filter_to_period
from backend.metrics.metric_comparisons import compare_metric, compare_metric_new

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


def chain_table(df, active_pods_df):

    result = calculate_revenue(df, "chain")
    result = result.merge(calculate_units(df, "chain"), on="chain", how="left")
    result = result.merge(calculate_buying_stores(df, "chain"), on="chain", how="left")
    result = result.merge(calculate_vpo(df, df, "chain"), on="chain", how="left")
    result = result.merge(calculate_avg_skus_per_store(df, "chain"), on="chain", how="left")

    l1m_period = resolve_period("L1M")
    df_l1m = filter_to_period(df, l1m_period["start"], l1m_period["end"])

    buying_l1m = calculate_buying_stores(df_l1m, "chain").rename(
        columns={"buying_stores": "buying_stores_l1m"}
    )

    result = result.merge(buying_l1m, on="chain", how="left")

    # -------------------------------------------------
    # FIX BUYING STORES L1M 0 VS NaN
    #
    # If a chain had active PODs in L1M but no buying
    # stores, the correct value is 0.
    #
    # If the chain had no active PODs in L1M, leave the
    # value as NaN because the period is not applicable.
    # -------------------------------------------------

    active_l1m = filter_to_period(
        active_pods_df,
        l1m_period["start"],
        l1m_period["end"],
    )

    active_l1m = (
        active_l1m
        .groupby("chain", as_index=False)["pod_helper"]
        .nunique()
        .rename(
            columns={
                "pod_helper": "active_pods_l1m",
            }
        )
    )

    result = result.merge(
        active_l1m,
        on="chain",
        how="left",
    )

    has_active_pods = (
        result["active_pods_l1m"]
        .fillna(0)
        .gt(0)
    )

    missing_buyers = (
        result["buying_stores_l1m"]
        .isna()
    )

    result.loc[
        has_active_pods & missing_buyers,
        "buying_stores_l1m",
    ] = 0

    result = result.drop(
        columns=["active_pods_l1m"]
    )


    l3m_period = resolve_period("L3M")
    df_l3m = filter_to_period(df, l3m_period["start"], l3m_period["end"])

    buying_l3m = calculate_buying_stores(df_l3m, "chain").rename(
        columns={"buying_stores": "buying_stores_3m"}
    )

    result = result.merge(buying_l3m, on="chain", how="left")

    units_l1m = compare_metric_new(
        df=df,
        df_full=df,
        active_pods_df=active_pods_df,
        metric="units",
        period="L1M",
        year=None,
        comparison="PP",
        group_cols=["chain"],
    )


    units_l1m = units_l1m[
        ["chain", "pct_change"]
    ].rename(columns={"pct_change": "units_l1m_pct"})

    result = result.merge(units_l1m, on="chain", how="left")

    units_l3m = compare_metric_new(
        df=df,
        df_full=df,
        active_pods_df=active_pods_df,
        metric="units",
        period="L3M",
        year=None,
        comparison="PP",
        group_cols=["chain"],
    )

    units_l3m = units_l3m[
        ["chain", "pct_change"]
    ].rename(columns={"pct_change": "units_l3m_pct"})

    result = result.merge(units_l3m, on="chain", how="left")

    result = result.sort_values("units", ascending=False)

    return result[[
        "chain",
        "units",
        "revenue",
        "avg_skus_per_store",
        "buying_stores",
        "buying_stores_3m",
        "buying_stores_l1m",
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
    base_grain = ["channel", "chain"]

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
        .merge(units, on=grain + ["month_year"], how="left")
    )

    monthly = add_additive_metric_3m(monthly, grain, "units")

    current_month = pd.Timestamp.today().to_period("M")
    monthly = monthly[monthly["month_year"] != current_month]

    if monthly.empty:
        return monthly

    latest_month = monthly["month_year"].max()
    latest = monthly[monthly["month_year"] == latest_month].copy()

    latest = latest.dropna(
        subset=["channel", "sku", "chain", "vpo_3m", "buying_stores_3m", "units_3m"]
    )

    if latest.empty:
        return latest

    completed_months = sorted(
        m for m in df["month_year"].unique()
        if m < current_month and m <= latest_month
    )

    recent_3m = completed_months[-3:]
    carrying_months = completed_months[-6:]
    universe_months = completed_months[-12:]

    explanation_df = df[df["month_year"].isin(recent_3m)].copy()
    carrying_df = df[df["month_year"].isin(carrying_months)].copy()
    universe_df = df[df["month_year"].isin(universe_months)].copy()

    if "status" in explanation_df.columns:
        explanation_df = explanation_df[explanation_df["status"] != "Inactive"]

    if "status" in carrying_df.columns:
        carrying_df = carrying_df[carrying_df["status"] != "Inactive"]

    if "status" in universe_df.columns:
        universe_df = universe_df[universe_df["status"] != "Inactive"]

    if explanation_df.empty or carrying_df.empty or universe_df.empty:
        return latest

    store_brand_universe = (
        universe_df
        .groupby(base_grain + ["coded_customer"], as_index=False)
        .agg(brand_units_12m=("units", "sum"))
    )

    store_brand_universe = store_brand_universe[
        store_brand_universe["brand_units_12m"] > 0
    ]

    store_brand_units = (
        explanation_df
        .groupby(base_grain + ["coded_customer"], as_index=False)
        .agg(brand_units_3m=("units", "sum"))
    )

    store_sku_units_3m = (
        explanation_df
        .groupby(grain + ["coded_customer"], as_index=False)
        .agg(sku_units_3m=("units", "sum"))
    )

    store_sku_units_3m = store_sku_units_3m[
        store_sku_units_3m["sku_units_3m"] > 0
    ]

    store_sku_units_6m = (
        carrying_df
        .groupby(grain + ["coded_customer"], as_index=False)
        .agg(sku_units_6m=("units", "sum"))
    )

    store_sku_units_6m = store_sku_units_6m[
        store_sku_units_6m["sku_units_6m"] > 0
    ]

    universe = latest[grain].drop_duplicates().merge(
        store_brand_universe,
        on=base_grain,
        how="left",
    )

    universe = universe.merge(
        store_brand_units,
        on=base_grain + ["coded_customer"],
        how="left",
    )

    universe = universe.merge(
        store_sku_units_3m[grain + ["coded_customer", "sku_units_3m"]],
        on=grain + ["coded_customer"],
        how="left",
    )

    universe = universe.merge(
        store_sku_units_6m[grain + ["coded_customer", "sku_units_6m"]],
        on=grain + ["coded_customer"],
        how="left",
    )

    store_sku_counts = (
        universe_df
        .groupby(base_grain + ["coded_customer"], as_index=False)
        .agg(num_skus_carried=("sku", "nunique"))
    )

    universe = universe.merge(
        store_sku_counts,
        on=base_grain + ["coded_customer"],
        how="left",
    )

    universe["brand_units_3m"] = universe["brand_units_3m"].fillna(0)
    universe["carries_sku_3m"] = universe["sku_units_3m"].fillna(0) > 0
    universe["carries_sku_6m"] = universe["sku_units_6m"].fillna(0) > 0

    explanation = (
        universe
        .groupby(grain, as_index=False)
        .agg(
            total_brand_stores_3m=("coded_customer", "nunique"),
            carrying_stores_6m=(
                "coded_customer",
                lambda x: x[universe.loc[x.index, "carries_sku_6m"]].nunique(),
            ),
            carrying_brand_units_per_store_3m=(
                "brand_units_3m",
                lambda x: x[universe.loc[x.index, "carries_sku_3m"]].mean(),
            ),
            noncarrying_brand_units_per_store_3m=(
                "brand_units_3m",
                lambda x: x[~universe.loc[x.index, "carries_sku_6m"]].mean(),
            ),
            opportunity_avg_skus=(
                "num_skus_carried",
                lambda x: x[~universe.loc[x.index, "carries_sku_6m"]].mean(),
            ),
            opportunity_stores_1_sku=(
                "num_skus_carried",
                lambda x: int(
                    (
                        (~universe.loc[x.index, "carries_sku_6m"])
                        & (x <= 1)
                    ).sum()
                ),
            ),
            chain_avg_skus=("num_skus_carried", "mean"),
        )
    )

    latest = latest.merge(explanation, on=grain, how="left")

    channel_sku_counts = (
        universe_df
        .groupby(["channel", "coded_customer"], as_index=False)
        .agg(num_skus_carried=("sku", "nunique"))
    )

    channel_avg_skus = (
        channel_sku_counts
        .groupby("channel", as_index=False)
        .agg(channel_avg_skus=("num_skus_carried", "mean"))
    )

    latest = latest.merge(channel_avg_skus, on="channel", how="left")

    latest["void_stores_3m"] = (
        latest["total_brand_stores_3m"] - latest["carrying_stores_6m"]
    )

    latest["brand_units_lift_pct"] = (
        (
            latest["carrying_brand_units_per_store_3m"]
            - latest["noncarrying_brand_units_per_store_3m"]
        )
        / latest["noncarrying_brand_units_per_store_3m"]
    )

    latest.loc[
        latest["noncarrying_brand_units_per_store_3m"].isna()
        | (latest["noncarrying_brand_units_per_store_3m"] <= 0),
        "brand_units_lift_pct",
    ] = pd.NA

    return latest[
        [
            "channel",
            "sku",
            "chain",
            "month_year",
            "vpo_3m",
            "buying_stores_3m",
            "carrying_stores_6m",
            "units_3m",
            "total_brand_stores_3m",
            "void_stores_3m",
            "carrying_brand_units_per_store_3m",
            "noncarrying_brand_units_per_store_3m",
            "brand_units_lift_pct",
            "opportunity_avg_skus",
            "opportunity_stores_1_sku",
            "chain_avg_skus",
            "channel_avg_skus",
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

def distribution_opportunity_store_detail_table(df, chain, sku, channel):
    table = df.copy()

    chain_norm = chain.strip().upper()
    sku_norm = sku.strip().upper()
    channel_norm = channel.strip().upper()

    table = table[
        (table["chain"].astype(str).str.strip().str.upper() == chain_norm)
        & (table["channel"].astype(str).str.strip().str.upper() == channel_norm)
    ].copy()

    if table.empty:
        return table

    store_month = (
        table.groupby(["coded_customer", "month_year"], as_index=False)
        .agg(reordered=("reorder_flag", "max"))
    )

    reorders = (
        store_month.groupby("coded_customer", as_index=False)
        .agg(brand_reorders=("reordered", "sum"))
    )

    brand_stores = (
        table.groupby("coded_customer", as_index=False)
        .agg({
            "chain": "first",
            "channel": "first",
            "store_number": "first",
            "street_address": "first",
            "city": "first",
            "state": "first",
            "zip": "first",
            "units": "sum",
            "first_month_purchased": "first",
            "last_month_purchased": "first",
            "status": "first",
            "sku": lambda x: sorted(x.dropna().astype(str).unique()),
        })
    )

    brand_stores["num_skus_carried"] = brand_stores["sku"].apply(len)
    brand_stores["carried_skus"] = brand_stores["sku"]

    brand_stores = brand_stores.rename(columns={
        "units": "brand_units",
    })

    brand_stores = brand_stores.merge(
        reorders,
        on="coded_customer",
        how="left",
    )

    sku_stores = (
        table[
            table["sku"].astype(str).str.strip().str.upper() == sku_norm
        ]
        .groupby("coded_customer", as_index=False)
        .agg(
            sku_units=("units", "sum"),
        )
    )

    result = brand_stores.merge(
        sku_stores,
        on="coded_customer",
        how="left",
    )

    result = result[result["sku_units"].isna()].copy()

    if result.empty:
        return result

    result["target_sku"] = sku

    columns = [
        "coded_customer",
        "chain",
        "channel",
        "store_number",
        "street_address",
        "city",
        "state",
        "zip",
        "carried_skus",
        "num_skus_carried",
        "brand_units",
        "brand_reorders",
        "first_month_purchased",
        "last_month_purchased",
        "status",
    ]

    existing_cols = [col for col in columns if col in result.columns]

    return result[existing_cols].sort_values(
        "brand_units",
        ascending=False,
    )
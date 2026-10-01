import pandas as pd

from backend.metrics.metric_callers import calculate_metric, calculate_monthly_metric, compare_metric
from backend.metrics.metric_helpers import filter_to_period, resolve_period


def _metric_table(metric_name, df, active_pods_df, group_cols, output_col):
    """Canonical metric call with the public/output column renamed in one place."""
    result = calculate_metric(
        metric_name=metric_name,
        df_filtered=df,
        active_pods_df=active_pods_df,
        group_cols=group_cols,
    )
    return result.rename(columns={"value": output_col})


def _raw_sum(df, value_col, group_cols, output_col=None):
    """
    Non-metric field aggregation only.

    Revenue is not currently in METRIC_CALCULATORS, so this preserves the existing
    output without importing the legacy metric calculator. Once revenue is added
    to the canonical registry, replace this with _metric_table("revenue", ...).
    """
    output_col = output_col or value_col
    return (
        df.groupby(group_cols, as_index=False, dropna=False)
        .agg(**{output_col: (value_col, "sum")})
    )


def chain_table(df, df_full, active_pods_df, active_pods_full, end_month=None):
    grain = ["chain"]

    units = _metric_table(
        "units",
        df,
        active_pods_df,
        grain,
        "units",
    )

    buying_stores = _metric_table(
        "buying_stores",
        df,
        active_pods_df,
        grain,
        "buying_stores",
    )

    velocity = _metric_table(
        "velocity",
        df,
        active_pods_df,
        grain,
        "vpo",
    )

    avg_skus = _metric_table(
        "average_skus_per_store",
        df,
        active_pods_df,
        grain,
        "avg_skus_per_store",
    )

    # Revenue is not yet registered in METRIC_CALCULATORS.
    revenue = _raw_sum(
        df,
        "revenue",
        grain,
        "revenue",
    )

    buying_l1m = compare_metric(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_full,
        metric_name="buying_stores",
        period="L1M",
        comparison="PP",
        group_cols=grain,
        end_month=end_month,
    )[
        ["chain", "value_current"]
    ].rename(
        columns={"value_current": "buying_stores_l1m"}
    )

    buying_l3m = compare_metric(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_full,
        metric_name="buying_stores",
        period="L3M",
        comparison="PP",
        group_cols=grain,
        end_month=end_month,
    )[
        ["chain", "value_current"]
    ].rename(
        columns={"value_current": "buying_stores_3m"}
    )

    units_l1m = compare_metric(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_full,
        metric_name="units",
        period="L1M",
        comparison="PP",
        group_cols=grain,
        end_month=end_month,
    )[
        ["chain", "pct_change"]
    ].rename(
        columns={"pct_change": "units_l1m_pct"}
    )

    units_l3m = compare_metric(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_full,
        metric_name="units",
        period="L3M",
        comparison="PP",
        group_cols=grain,
        end_month=end_month,
    )[
        ["chain", "pct_change"]
    ].rename(
        columns={"pct_change": "units_l3m_pct"}
    )

    def check_grain(name, table, key):
        print(
            f"{name}: "
            f"rows={len(table)}, "
            f"unique_{key}={table[key].nunique()}, "
            f"duplicates={table.duplicated(key).sum()}"
        )

    print("\n=== CHAIN TABLE GRAIN DEBUG ===")

    check_grain("units", units, "chain")
    check_grain("revenue", revenue, "chain")
    check_grain("avg_skus", avg_skus, "chain")
    check_grain("buying_stores", buying_stores, "chain")
    check_grain("buying_l3m", buying_l3m, "chain")
    check_grain("buying_l1m", buying_l1m, "chain")
    check_grain("velocity", velocity, "chain")
    check_grain("units_l1m", units_l1m, "chain")
    check_grain("units_l3m", units_l3m, "chain")

    result = (
        revenue
        .merge(units, on=grain, how="outer")
        .merge(buying_stores, on=grain, how="outer")
        .merge(velocity, on=grain, how="outer")
        .merge(avg_skus, on=grain, how="outer")
        .merge(buying_l1m, on=grain, how="left")
        .merge(buying_l3m, on=grain, how="left")
        .merge(units_l1m, on=grain, how="left")
        .merge(units_l3m, on=grain, how="left")
    )

    return (
        result.sort_values("units", ascending=False)[
            [
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
            ]
        ]
        .reset_index(drop=True)
    )


def store_performance(df, active_pods_df):
    grain = ["coded_customer", "chain"]

    # This is a descriptive count of reorder_flag months, not the canonical
    # reorder-rate metric, so preserve the existing store-detail behavior.
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

    # Use the distributor / DC from the store's most recent month.
    latest_store_supply = (
        df.sort_values("month_year")
        .groupby(grain, as_index=False)
        .tail(1)[
            grain + ["distributor", "dc"]
        ]
    )

    units = _metric_table(
        "units",
        df,
        active_pods_df,
        grain,
        "units",
    )

    velocity = _metric_table(
        "velocity",
        df,
        active_pods_df,
        grain,
        "vpo",
    )

    skus_selling = _metric_table(
        "skus_selling",
        df,
        active_pods_df,
        grain,
        "skus_selling",
    )

    # Revenue is not yet registered in METRIC_CALCULATORS.
    revenue = _raw_sum(
        df,
        "revenue",
        grain,
        "revenue",
    )

    result = (
        base_result
        .merge(reorders, on=grain, how="left")
        .merge(revenue, on=grain, how="left")
        .merge(units, on=grain, how="left")
        .merge(velocity, on=grain, how="left")
        .merge(skus_selling, on=grain, how="left")
        .merge(latest_store_supply, on=grain, how="left")
    )

    return (
        result.sort_values("units", ascending=False)[
            [
                "coded_customer",
                "chain",
                "units",
                "revenue",
                "reorders",
                "vpo",
                "skus_selling",
                "distributor",
                "dc",
                "first_month_purchased",
                "last_month_purchased",
                "status",
            ]
        ]
        .reset_index(drop=True)
    )


# This is status/business-state logic, not metric plumbing.
def status_counts_dict(df):
    store_status = (
        df.groupby("coded_customer", as_index=False)
        .agg(status=("status", "first"))
    )

    result = store_status["status"].value_counts().to_dict()

    return {
        "Healthy": int(result.get("Healthy", 0)),
        "Struggling": int(result.get("Struggling", 0)),
        "Revived": int(result.get("Revived", 0)),
        "Inactive": int(result.get("Inactive", 0)),
        "New": int(result.get("New", 0)),
    }


def chain_insight_table(df, df_full, active_pods_full, end_month=None):
    result = compare_metric(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_full,
        metric_name="units",
        period="L3M",
        comparison="PP",
        group_cols=["chain"],
        end_month=end_month,
    )

    return result[
        [
            "chain",
            "value_current",
            "value_comparison",
            "pct_change",
            "abs_change",
        ]
    ].rename(
        columns={
            "value_current": "units_3m",
            "value_comparison": "units_l3m",
            "pct_change": "units_l3m_pct",
            "abs_change": "units_l3m_abs",
        }
    )


def sku_insight_table(df, df_full, active_pods_full, end_month=None):
    units = compare_metric(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_full,
        metric_name="units",
        period="L3M",
        comparison="PP",
        group_cols=["sku"],
        end_month=end_month,
    )[
        ["sku", "value_current", "value_comparison"]
    ].rename(
        columns={
            "value_current": "units_3m",
            "value_comparison": "units_l3m",
        }
    )

    velocity = compare_metric(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_full,
        metric_name="velocity",
        period="L3M",
        comparison="PP",
        group_cols=["sku"],
        end_month=end_month,
    )[
        [
            "sku",
            "value_current",
            "value_comparison",
            "pct_change",
            "abs_change",
        ]
    ].rename(
        columns={
            "value_current": "vpo_3m",
            "value_comparison": "vpo_l3m",
            "pct_change": "vpo_l3m_pct",
            "abs_change": "vpo_l3m_abs",
        }
    )

    result = units.merge(
        velocity,
        on="sku",
        how="left",
    )

    return result.dropna(
        subset=["vpo_3m", "vpo_l3m"]
    )[
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


def channel_reorder_insight_table(df, df_full, active_pods_full, end_month=None):
    reorder = compare_metric(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_full,
        metric_name="reorder_rate",
        period="L3M",
        comparison="PP",
        group_cols=["channel"],
        end_month=end_month,
    )[
        [
            "channel",
            "value_current",
            "value_comparison",
            "abs_change",
        ]
    ].rename(
        columns={
            "value_current": "reorder_rate_3m",
            "value_comparison": "reorder_rate_l3m",
            "abs_change": "reorder_rate_l3m_abs",
        }
    )

    buying_stores = compare_metric(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_full,
        metric_name="buying_stores",
        period="L3M",
        comparison="PP",
        group_cols=["channel"],
        end_month=end_month,
    )[
        [
            "channel",
            "value_current",
            "value_comparison",
        ]
    ].rename(
        columns={
            "value_current": "buying_stores_3m",
            "value_comparison": "buying_stores_l3m",
        }
    )

    result = reorder.merge(
        buying_stores,
        on="channel",
        how="left",
    )

    result = result[
        result["channel"].notna()
    ].copy()

    return result.dropna(
        subset=["reorder_rate_3m", "reorder_rate_l3m"]
    )[
        [
            "channel",
            "reorder_rate_3m",
            "reorder_rate_l3m",
            "reorder_rate_l3m_abs",
            "buying_stores_3m",
            "buying_stores_l3m",
        ]
    ]


def chain_sku_velocity_gap_opportunity_table(
    df,
    df_full,
    active_pods_full,
    end_month=None,
):
    df = df.copy()
    df_full = df_full.copy()
    active_pods_full = active_pods_full.copy()

    df["month_year"] = pd.PeriodIndex(
        df["month_year"].astype(str),
        freq="M",
    )
    df_full["month_year"] = pd.PeriodIndex(
        df_full["month_year"].astype(str),
        freq="M",
    )
    active_pods_full["month_year"] = pd.PeriodIndex(
        active_pods_full["month_year"].astype(str),
        freq="M",
    )

    grain = ["channel", "sku", "chain"]
    base_grain = ["channel", "chain"]

    l3m_period = resolve_period(
        "L3M",
        end_month=end_month,
    )

    df_l3m = filter_to_period(
        df,
        l3m_period["start"],
        l3m_period["end"],
    )

    active_pods_l3m = filter_to_period(
        active_pods_full,
        l3m_period["start"],
        l3m_period["end"],
    )

    velocity = _metric_table(
        "velocity",
        df_l3m,
        active_pods_l3m,
        grain,
        "vpo_3m",
    )

    buying_stores = _metric_table(
        "buying_stores",
        df_l3m,
        active_pods_l3m,
        grain,
        "buying_stores_3m",
    )

    units = _metric_table(
        "units",
        df_l3m,
        active_pods_l3m,
        grain,
        "units_3m",
    )

    latest = (
        velocity
        .merge(
            buying_stores,
            on=grain,
            how="left",
        )
        .merge(
            units,
            on=grain,
            how="left",
        )
    )

    latest["month_year"] = l3m_period["end"]

    latest = latest.dropna(
        subset=[
            "channel",
            "sku",
            "chain",
            "vpo_3m",
            "buying_stores_3m",
            "units_3m",
        ]
    )

    if latest.empty:
        return latest

    # Everything below this point is the existing bespoke opportunity/explanation
    # logic. The old metric-generation layer above it has been removed.
    latest_month = l3m_period["end"]

    completed_months = sorted(
        m
        for m in df["month_year"].unique()
        if m <= latest_month
    )

    recent_3m = completed_months[-3:]
    carrying_months = completed_months[-6:]
    universe_months = completed_months[-12:]

    explanation_df = df[
        df["month_year"].isin(recent_3m)
    ].copy()

    carrying_df = df[
        df["month_year"].isin(carrying_months)
    ].copy()

    universe_df = df[
        df["month_year"].isin(universe_months)
    ].copy()

    if "status" in explanation_df.columns:
        explanation_df = explanation_df[
            explanation_df["status"] != "Inactive"
        ]

    if "status" in carrying_df.columns:
        carrying_df = carrying_df[
            carrying_df["status"] != "Inactive"
        ]

    if "status" in universe_df.columns:
        universe_df = universe_df[
            universe_df["status"] != "Inactive"
        ]

    if explanation_df.empty or carrying_df.empty or universe_df.empty:
        return latest

    store_brand_universe = (
        universe_df
        .groupby(
            base_grain + ["coded_customer"],
            as_index=False,
        )
        .agg(
            brand_units_12m=("units", "sum"),
        )
    )

    store_brand_universe = store_brand_universe[
        store_brand_universe["brand_units_12m"] > 0
    ]

    store_brand_units = (
        explanation_df
        .groupby(
            base_grain + ["coded_customer"],
            as_index=False,
        )
        .agg(
            brand_units_3m=("units", "sum"),
        )
    )

    store_sku_units_3m = (
        explanation_df
        .groupby(
            grain + ["coded_customer"],
            as_index=False,
        )
        .agg(
            sku_units_3m=("units", "sum"),
        )
    )

    store_sku_units_3m = store_sku_units_3m[
        store_sku_units_3m["sku_units_3m"] > 0
    ]

    store_sku_units_6m = (
        carrying_df
        .groupby(
            grain + ["coded_customer"],
            as_index=False,
        )
        .agg(
            sku_units_6m=("units", "sum"),
        )
    )

    store_sku_units_6m = store_sku_units_6m[
        store_sku_units_6m["sku_units_6m"] > 0
    ]

    universe = latest[
        grain
    ].drop_duplicates().merge(
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
        store_sku_units_3m[
            grain + ["coded_customer", "sku_units_3m"]
        ],
        on=grain + ["coded_customer"],
        how="left",
    )

    universe = universe.merge(
        store_sku_units_6m[
            grain + ["coded_customer", "sku_units_6m"]
        ],
        on=grain + ["coded_customer"],
        how="left",
    )

    store_sku_counts = (
        universe_df
        .groupby(
            base_grain + ["coded_customer"],
            as_index=False,
        )
        .agg(
            num_skus_carried=("sku", "nunique"),
        )
    )

    universe = universe.merge(
        store_sku_counts,
        on=base_grain + ["coded_customer"],
        how="left",
    )

    universe["brand_units_3m"] = (
        universe["brand_units_3m"].fillna(0)
    )

    universe["carries_sku_3m"] = (
        universe["sku_units_3m"].fillna(0) > 0
    )

    universe["carries_sku_6m"] = (
        universe["sku_units_6m"].fillna(0) > 0
    )

    explanation = (
        universe
        .groupby(
            grain,
            as_index=False,
        )
        .agg(
            total_brand_stores_3m=(
                "coded_customer",
                "nunique",
            ),
            carrying_stores_6m=(
                "coded_customer",
                lambda x: x[
                    universe.loc[
                        x.index,
                        "carries_sku_6m",
                    ]
                ].nunique(),
            ),
            carrying_brand_units_per_store_3m=(
                "brand_units_3m",
                lambda x: x[
                    universe.loc[
                        x.index,
                        "carries_sku_3m",
                    ]
                ].mean(),
            ),
            noncarrying_brand_units_per_store_3m=(
                "brand_units_3m",
                lambda x: x[
                    ~universe.loc[
                        x.index,
                        "carries_sku_6m",
                    ]
                ].mean(),
            ),
            opportunity_avg_skus=(
                "num_skus_carried",
                lambda x: x[
                    ~universe.loc[
                        x.index,
                        "carries_sku_6m",
                    ]
                ].mean(),
            ),
            opportunity_stores_1_sku=(
                "num_skus_carried",
                lambda x: int(
                    (
                        ~universe.loc[
                            x.index,
                            "carries_sku_6m",
                        ]
                        & (x <= 1)
                    ).sum()
                ),
            ),
            chain_avg_skus=(
                "num_skus_carried",
                "mean",
            ),
        )
    )

    latest = latest.merge(
        explanation,
        on=grain,
        how="left",
    )

    channel_sku_counts = (
        universe_df
        .groupby(
            ["channel", "coded_customer"],
            as_index=False,
        )
        .agg(
            num_skus_carried=("sku", "nunique"),
        )
    )

    channel_avg_skus = (
        channel_sku_counts
        .groupby(
            "channel",
            as_index=False,
        )
        .agg(
            channel_avg_skus=("num_skus_carried", "mean"),
        )
    )

    latest = latest.merge(
        channel_avg_skus,
        on="channel",
        how="left",
    )

    latest["void_stores_3m"] = (
        latest["total_brand_stores_3m"]
        - latest["carrying_stores_6m"]
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
        | (
            latest["noncarrying_brand_units_per_store_3m"]
            <= 0
        ),
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


def top_sales_month_insight_table(df, active_pods_df):
    units = calculate_monthly_metric(
        metric_name="units",
        df_filtered=df,
        active_pods_df=active_pods_df,
    ).rename(
        columns={"value": "units"}
    )

    buying_stores = calculate_monthly_metric(
        metric_name="buying_stores",
        df_filtered=df,
        active_pods_df=active_pods_df,
    ).rename(
        columns={"value": "buying_stores"}
    )

    velocity = calculate_monthly_metric(
        metric_name="velocity",
        df_filtered=df,
        active_pods_df=active_pods_df,
    ).rename(
        columns={"value": "vpo"}
    )

    reorder_rate = calculate_monthly_metric(
        metric_name="reorder_rate",
        df_filtered=df,
        active_pods_df=active_pods_df,
    ).rename(
        columns={"value": "reorder_rate"}
    )

    print("\n=== TOP SALES MONTH DEBUG ===")

    print("\nUNITS")
    print(units.columns.tolist())
    print(units.head())

    print("\nBUYING STORES")
    print(buying_stores.columns.tolist())
    print(buying_stores.head())

    print("\nVELOCITY")
    print(velocity.columns.tolist())
    print(velocity.head())

    print("\nREORDER RATE")
    print(reorder_rate.columns.tolist())
    print(reorder_rate.head())

    monthly = (
        units
        .merge(
            buying_stores,
            on="month_year",
            how="outer",
        )
        .merge(
            velocity,
            on="month_year",
            how="outer",
        )
        .merge(
            reorder_rate,
            on="month_year",
            how="outer",
        )
        .sort_values("month_year")
        .reset_index(drop=True)
    )

    current_month = pd.Timestamp.today().to_period("M")

    return monthly[
        monthly["month_year"] != current_month
    ][
        [
            "month_year",
            "units",
            "buying_stores",
            "vpo",
            "reorder_rate",
        ]
    ]


def distribution_opportunity_store_detail_table(
    df,
    chain,
    sku,
    channel,
):
    table = df.copy()

    chain_norm = chain.strip().upper()
    sku_norm = sku.strip().upper()
    channel_norm = channel.strip().upper()

    table = table[
        (
            table["chain"]
            .astype(str)
            .str.strip()
            .str.upper()
            == chain_norm
        )
        & (
            table["channel"]
            .astype(str)
            .str.strip()
            .str.upper()
            == channel_norm
        )
    ].copy()

    if table.empty:
        return table

    store_month = (
        table
        .groupby(
            ["coded_customer", "month_year"],
            as_index=False,
        )
        .agg(
            reordered=("reorder_flag", "max"),
        )
    )

    reorders = (
        store_month
        .groupby(
            "coded_customer",
            as_index=False,
        )
        .agg(
            brand_reorders=("reordered", "sum"),
        )
    )

    brand_stores = (
        table
        .groupby(
            "coded_customer",
            as_index=False,
        )
        .agg(
            {
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
                "sku": lambda x: sorted(
                    x.dropna().astype(str).unique()
                ),
            }
        )
    )

    brand_stores["num_skus_carried"] = (
        brand_stores["sku"].apply(len)
    )

    brand_stores["carried_skus"] = brand_stores["sku"]

    brand_stores = brand_stores.rename(
        columns={"units": "brand_units"}
    )

    brand_stores = brand_stores.merge(
        reorders,
        on="coded_customer",
        how="left",
    )

    sku_stores = (
        table[
            (
                table["sku"]
                .astype(str)
                .str.strip()
                .str.upper()
                == sku_norm
            )
        ]
        .groupby(
            "coded_customer",
            as_index=False,
        )
        .agg(
            sku_units=("units", "sum"),
        )
    )

    result = brand_stores.merge(
        sku_stores,
        on="coded_customer",
        how="left",
    )

    result = result[
        result["sku_units"].isna()
    ].copy()

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

    existing_cols = [
        col
        for col in columns
        if col in result.columns
    ]

    return result[
        existing_cols
    ].sort_values(
        "brand_units",
        ascending=False,
    )
import pandas as pd
from backend.insights.insights_helper import format_pct, format_number, format_float
from backend.metrics.metric_growth_rates import calculate_vpo_3m, calculate_buying_stores_3m, add_additive_metric_3m, pct_change
from backend.metrics.monthly_metric_calculators import calculate_monthly_units


def build_void_opportunity_table(df, df_all_time):

    # Build table with 3M VPO, 3M buying stores, and 3M units by chain/SKU/channel
    # Only return the results for the latest full month
    latest = _build_latest_void_candidate_metrics(df, df_all_time)

    if latest.empty:
        return latest
    
    # Returns all active stores in 3 dataframes with data from last 3, 6, and 12 months
    windows = _get_void_opportunity_windows(df, latest)

    # Build a store-level table showing which stores carry the SKU, recent brand performance in those stores, 
    # and how many SKUs each store carries across each chain/SKU combination.
    universe = _build_void_store_universe(
        latest=latest,
        explanation_df=windows["recent_3m_df"],
        carrying_df=windows["carrying_6m_df"],
        universe_df=windows["universe_12m_df"],
    )

    if universe.empty:
        return latest
    
    # Aggregates stats for carrying vs non-carrying stores for each chain/SKU combination
    explanation = _summarize_void_store_universe(universe)

    # Merges in channel SKU average and percent change and returns final table
    return _finalize_void_opportunity_table(
        latest=latest,
        explanation=explanation,
        universe_df=windows["universe_12m_df"],
    )

def _build_latest_void_candidate_metrics(df, df_all_time):
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
        subset=[
            "channel",
            "sku",
            "chain",
            "vpo_3m",
            "buying_stores_3m",
            "units_3m",
        ]
    )

    return latest


def _get_void_opportunity_windows(df, latest):
    latest_month = latest["month_year"].max()

    recent_3m = pd.period_range(latest_month - 2, latest_month, freq="M")
    carrying_months = pd.period_range(latest_month - 5, latest_month, freq="M")
    universe_months = pd.period_range(latest_month - 11, latest_month, freq="M")

    recent_3m_df = df[df["month_year"].isin(recent_3m)].copy()
    carrying_6m_df = df[df["month_year"].isin(carrying_months)].copy()
    universe_12m_df = df[df["month_year"].isin(universe_months)].copy()

    recent_3m_df = _exclude_inactive_stores(recent_3m_df)
    carrying_6m_df = _exclude_inactive_stores(carrying_6m_df)
    universe_12m_df = _exclude_inactive_stores(universe_12m_df)

    return {
        "recent_3m_df": recent_3m_df,
        "carrying_6m_df": carrying_6m_df,
        "universe_12m_df": universe_12m_df,
    }


def _exclude_inactive_stores(df):
    if "status" not in df.columns:
        return df

    return df[df["status"] != "Inactive"].copy()


def _build_void_store_universe(
    latest,
    explanation_df,
    carrying_df,
    universe_df,
):
    if explanation_df.empty or carrying_df.empty or universe_df.empty:
        return pd.DataFrame()

    grain = ["channel", "sku", "chain"]
    base_grain = ["channel", "chain"]

    store_brand_universe = (
        universe_df
        .groupby(base_grain + ["coded_customer"], as_index=False)
        .agg(brand_units_12m=("units", "sum"))
    )

    store_brand_universe = store_brand_universe[
        store_brand_universe["brand_units_12m"] > 0
    ]

    store_brand_units_3m = (
        explanation_df
        .groupby(base_grain + ["coded_customer"], as_index=False)
        .agg(brand_units_3m=("units", "sum"))
    )

    store_sku_status = (
        carrying_df[
            grain + ["coded_customer", "sku_status"]
        ]
        .drop_duplicates()
    )

    store_sku_counts = (
        universe_df
        .groupby(base_grain + ["coded_customer"], as_index=False)
        .agg(num_skus_carried=("sku", "nunique"))
    )

    universe = (
        latest[grain]
        .drop_duplicates()
        .merge(store_brand_universe, on=base_grain, how="left")
        .merge(
            store_brand_units_3m,
            on=base_grain + ["coded_customer"],
            how="left",
        )
        .merge(
            store_sku_status,
            on=grain + ["coded_customer"],
            how="left",
        )
        .merge(
            store_sku_counts,
            on=base_grain + ["coded_customer"],
            how="left",
        )
    )

    universe["brand_units_3m"] = universe["brand_units_3m"].fillna(0)

    universe["carries_sku"] = (
        universe["sku_status"].notna()
        & ~universe["sku_status"].eq("Inactive")
    )

    return universe


def _summarize_void_store_universe(universe):
    grain = ["channel", "sku", "chain"]

    carrying = universe[universe["carries_sku"]].copy()
    noncarrying = universe[~universe["carries_sku"]].copy()

    total_brand_stores = (
        universe
        .groupby(grain, as_index=False)
        .agg(total_brand_stores=("coded_customer", "nunique"))
    )

    carrying_stores = (
        carrying
        .groupby(grain, as_index=False)
        .agg(carrying_stores=("coded_customer", "nunique"))
    )

    noncarrying_stores = (
        noncarrying
        .groupby(grain, as_index=False)
        .agg(noncarrying_stores=("coded_customer", "nunique"))
    )

    carrying_brand_units = (
        carrying
        .groupby(grain, as_index=False)
        .agg(carrying_brand_units_per_store_3m=("brand_units_3m", "mean"))
    )

    noncarrying_brand_units = (
        noncarrying
        .groupby(grain, as_index=False)
        .agg(noncarrying_brand_units_per_store_3m=("brand_units_3m", "mean"))
    )

    carrying_avg_skus = (
        carrying
        .groupby(grain, as_index=False)
        .agg(carrying_avg_skus=("num_skus_carried", "mean"))
    )

    opportunity_avg_skus = (
        noncarrying
        .groupby(grain, as_index=False)
        .agg(opportunity_avg_skus=("num_skus_carried", "mean"))
    )

    opportunity_stores_1_sku = (
        noncarrying[noncarrying["num_skus_carried"] <= 1]
        .groupby(grain, as_index=False)
        .agg(opportunity_stores_1_sku=("coded_customer", "nunique"))
    )

    chain_avg_skus = (
        universe
        .groupby(grain, as_index=False)
        .agg(chain_avg_skus=("num_skus_carried", "mean"))
    )

    explanation = (
        total_brand_stores
        .merge(carrying_stores, on=grain, how="left")
        .merge(noncarrying_stores, on=grain, how="left")
        .merge(carrying_brand_units, on=grain, how="left")
        .merge(noncarrying_brand_units, on=grain, how="left")
        .merge(opportunity_avg_skus, on=grain, how="left")
        .merge(carrying_avg_skus, on=grain, how="left")
        .merge(opportunity_stores_1_sku, on=grain, how="left")
        .merge(chain_avg_skus, on=grain, how="left")
    )

    explanation["carrying_stores"] = (explanation["carrying_stores"].fillna(0))
    explanation["noncarrying_stores"] = (explanation["noncarrying_stores"].fillna(0))
    explanation["opportunity_stores_1_sku"] = (explanation["opportunity_stores_1_sku"].fillna(0))

    return explanation


def _finalize_void_opportunity_table(latest, explanation, universe_df):
    grain = ["channel", "sku", "chain"]

    latest = latest.merge(explanation, on=grain, how="left")

    channel_avg_skus = _calculate_channel_avg_skus(universe_df)

    latest = latest.merge(channel_avg_skus, on="channel", how="left")

    latest["brand_units_lift_pct"] = pct_change(latest["carrying_brand_units_per_store_3m"], latest["noncarrying_brand_units_per_store_3m"])
    latest["void_stores"] = latest["noncarrying_stores"]

    return latest[
        [
            "channel",
            "sku",
            "chain",
            "month_year",
            "vpo_3m",
            "buying_stores_3m",
            "carrying_stores",
            "units_3m",
            "total_brand_stores",
            "void_stores",
            "noncarrying_stores",
            "carrying_brand_units_per_store_3m",
            "noncarrying_brand_units_per_store_3m",
            "brand_units_lift_pct",
            "opportunity_avg_skus",
            "opportunity_stores_1_sku",
            "chain_avg_skus",
            "channel_avg_skus",
        ]
    ]


def _calculate_channel_avg_skus(universe_df):
    channel_sku_counts = (
        universe_df
        .groupby(["channel", "coded_customer"], as_index=False)
        .agg(num_skus_carried=("sku", "nunique"))
    )

    return (
        channel_sku_counts
        .groupby("channel", as_index=False)
        .agg(channel_avg_skus=("num_skus_carried", "mean"))
    )


def analyze_void_opportunity(
    table: pd.DataFrame,
    limit: int = 2,
) -> pd.DataFrame | None:
    """
    Applies insight criteria and selects the strongest
    void-distribution opportunities.
    """
    table = table.copy()

    if table.empty:
        return None

    required_cols = [
        "channel",
        "sku",
        "chain",
        "vpo_3m",
        "buying_stores_3m",
        "total_brand_stores",
        "noncarrying_stores",
        "brand_units_lift_pct",
    ]

    missing_cols = [col for col in required_cols if col not in table.columns]

    if missing_cols:
        return None

    # REMOVE CONFIDENTIAL / NON-REAL CHAINS
    table = table[
        table["chain"].notna()
        & ~table["chain"]
            .astype(str)
            .str.strip()
            .str.upper()
            .eq("CONFIDENTIAL")
    ].copy()

    # INSIGHT CRITERIA
    table = table[
        (table["noncarrying_stores"] > 0)
        & (table["buying_stores_3m"] >= 2)
        & (table["brand_units_lift_pct"].notna())
        & (table["brand_units_lift_pct"] > 0)
        & (table["vpo_3m"] > 0)
    ].copy()

    if table.empty:
        return None

    # ESTIMATE ANNUALIZED UNIT OPPORTUNITY
    table["captured_units"] = (
        table["vpo_3m"]
        * table["noncarrying_stores"]
        * 52
    )

    # REMOVE LOW-IMPACT OPPORTUNITIES
    table = table[
        table["captured_units"] >= 200
    ]

    if table.empty:
        return None

    # SELECT TOP OPPORTUNITIES
    table = table.sort_values(
        "captured_units",
        ascending=False,
    )

    return table.head(limit)

def normalize_void_opportunity_data(
    table: pd.DataFrame,
) -> list[dict] | dict | None:
    """
    Normalizes analyzed void-opportunity rows into
    structured insight-ready data objects.
    """
    if table is None or table.empty:
        return None

    results = []

    for _, row in table.iterrows():

        result = {
            "sku": row["sku"],
            "chain": row["chain"],
            "channel": row["channel"],

            "buying_stores": int(row["carrying_stores"]),
            "void_stores": int(row["noncarrying_stores"]),
            "total_stores": int(row["total_brand_stores"]),

            "vpo": float(row["vpo_3m"]),
            "lift": float(row["brand_units_lift_pct"]),
            "captured_units": int(row["captured_units"]),

            "opportunity_avg_skus": row.get("opportunity_avg_skus"),
            "carrying_avg_skus": row.get("carrying_avg_skus"),
            "chain_avg_skus": row.get("chain_avg_skus"),
            "channel_avg_skus": row.get("channel_avg_skus"),

            "opportunity_stores_1_sku": int(
                row.get("opportunity_stores_1_sku", 0) or 0
            ),

            "carrying_brand_units_per_store_3m": row.get(
                "carrying_brand_units_per_store_3m"
            ),

            "noncarrying_brand_units_per_store_3m": row.get(
                "noncarrying_brand_units_per_store_3m"
            ),

            "metrics": {
                "buying_stores": int(row["carrying_stores"]),
                "void_stores": int(row["noncarrying_stores"]),
                "total_brand_stores": int(row["total_brand_stores"]),
                "vpo_3m": float(row["vpo_3m"]),
                "brand_units_lift_pct": float(row["brand_units_lift_pct"]),
                "impact_units": int(row["captured_units"]),

                "opportunity_avg_skus": row.get("opportunity_avg_skus"),
                "carrying_avg_skus": row.get("carrying_avg_skus"),
                "chain_avg_skus": row.get("chain_avg_skus"),
                "channel_avg_skus": row.get("channel_avg_skus"),

                "carrying_brand_units_per_store_3m": row.get(
                    "carrying_brand_units_per_store_3m"
                ),

                "noncarrying_brand_units_per_store_3m": row.get(
                    "noncarrying_brand_units_per_store_3m"
                ),
            },

            "entities": {
                "sku": row["sku"],
                "chain": row["chain"],
                "channel": row["channel"],
            },
        }

        results.append(result)

    if len(results) == 1:
        return results[0]

    return results

def describe_void_opportunity(data):
    if data is None:
        return None

    sku = data["sku"]
    chain = data["chain"]
    channel = data["channel"]

    void_stores = data["void_stores"]
    buying_stores = data["buying_stores"]

    vpo = data["vpo"]
    lift = data["lift"]
    captured_units = data["captured_units"]

    opportunity_avg_skus = data.get("opportunity_avg_skus")
    carrying_avg_skus = data.get("carrying_avg_skus")

    opportunity_stores_1_sku = data.get(
        "opportunity_stores_1_sku"
    )

    carrying_brand_units = data.get(
        "carrying_brand_units_per_store_3m"
    )

    noncarrying_brand_units = data.get(
        "noncarrying_brand_units_per_store_3m"
    )

    # FORMAT METRICS

    lift_pct = format_pct(lift)
    vpo_fmt = format_float(vpo)
    captured_units_fmt = format_number(captured_units)
    void_stores_fmt = format_number(void_stores)
    buying_stores_fmt = format_number(buying_stores)
    carrying_brand_units_fmt = format_number(carrying_brand_units)
    noncarrying_brand_units_fmt = format_number(noncarrying_brand_units)
    opportunity_avg_skus_fmt = format_float(opportunity_avg_skus)
    carrying_avg_skus_fmt = format_float(carrying_avg_skus)
    opportunity_stores_1_sku_fmt = format_number(opportunity_stores_1_sku)

    # HEADLINE

    headline = (
        f"{sku} has room to expand across {chain}."
    )

    # SUMMARY

    summary = (
        f"{sku} has a distribution opportunity at {chain}, "
        f"with {void_stores_fmt} stores buying the brand "
        f"but not currently carrying the SKU."
    )

    # SUMMARY PARTS

    parts = [
        {
            "type": "chip",
            "value": sku,
            "tone": "neutral",
        },

        {
            "type": "text",
            "value": " has a distribution opportunity at ",
        },

        {
            "type": "chip",
            "value": chain,
            "tone": "neutral",
        },

        {
            "type": "text",
            "value": ", with ",
        },

        {
            "type": "chip",
            "value": f"{void_stores_fmt} stores",
            "tone": "positive",
        },

        {
            "type": "text",
            "value": " buying the brand but not currently carrying the SKU.",
        },
    ]

    # DESCRIPTION BLOCKS

    intro_block = {
        "type": "text",
        "value": (
            f"{sku} is currently sold in {buying_stores_fmt} "
            f"stores at {chain}, while {void_stores_fmt} "
            f"additional stores buy the brand but do not "
            f"currently carry the SKU."
        ),
    }

    assortment_block = {
        "type": "text",
        "value": (
            f"Stores carrying the SKU average "
            f"{carrying_avg_skus_fmt} SKUs from the brand, "
            f"compared to {opportunity_avg_skus_fmt} "
            f"in non-carrying stores."
        ),
    }

    velocity_block = {
        "type": "text",
        "value": (
            f"The SKU is currently averaging "
            f"{vpo_fmt} units per store per week."
        ),
    }

    single_sku_block = {
        "type": "text",
        "value": (
            f"{opportunity_stores_1_sku_fmt} opportunity stores "
            f"currently carry only one SKU from the brand."
        ),
    }

    opportunity_block = {
        "type": "text",
        "value": (
            f"If distributed across those opportunity stores "
            f"at current productivity levels, this could represent "
            f"approximately {captured_units_fmt} incremental "
            f"annualized units."
        ),
    }

    lift_block = {
        "type": "text",
        "value": (
            f"Stores currently carrying the SKU sold "
            f"{lift_pct} more total brand units over the last "
            f"3 months than stores not carrying the SKU "
            f"({carrying_brand_units_fmt} vs "
            f"{noncarrying_brand_units_fmt})."
        ),
    }

    # OPTIONAL BLOCK CONDITIONS

    include_assortment_block = (
        opportunity_avg_skus is not None
        and carrying_avg_skus is not None
    )

    include_single_sku_block = (
        opportunity_stores_1_sku is not None
        and opportunity_stores_1_sku > 0
    )

    include_lift_block = (
        carrying_brand_units is not None
        and noncarrying_brand_units is not None
        and lift is not None
    )

    # ASSEMBLE DESCRIPTION

    description = [
        intro_block,

        assortment_block
        if include_assortment_block
        else None,

        velocity_block,

        single_sku_block
        if include_single_sku_block
        else None,

        opportunity_block,

        lift_block
        if include_lift_block
        else None,
    ]

    description = [
        block for block in description
        if block is not None
    ]

    key_points = [
        (
            f"{sku} is currently sold in {buying_stores_fmt} stores at "
            f"{chain}, while {void_stores_fmt} additional stores buy the "
            f"brand but do not currently carry the SKU."
        ),
        (
            f"The SKU is currently averaging {vpo_fmt} units per store "
            f"per week."
        ),
        (
            f"If distributed across those opportunity stores at current "
            f"productivity levels, this could represent approximately "
            f"{captured_units_fmt} incremental annualized units."
        ),
    ]

    if include_assortment_block:
        key_points.append(
            (
                f"Stores carrying the SKU average "
                f"{carrying_avg_skus_fmt} SKUs from the brand, compared "
                f"to {opportunity_avg_skus_fmt} in non-carrying stores."
            )
        )

    #if include_single_sku_block:
    #    key_points.append(
    #        (
    #            f"{opportunity_stores_1_sku_fmt} opportunity stores "
    #            f"currently carry only one SKU from the brand."
    #        )
    #    )

    if include_lift_block:
        key_points.append(
            (
                f"Stores currently carrying the SKU sold {lift_pct} more "
                f"total brand units over the last 3 months than stores "
                f"not carrying the SKU ({carrying_brand_units_fmt} vs "
                f"{noncarrying_brand_units_fmt})."
            )
        )

    return {
        "headline": headline,
        "summary": summary,
        "parts": parts,
        "description": description,
        "key_points": key_points,

    }


def create_void_opportunity_store_list(df, chain, sku, channel):
    table = df.copy()

    chain_norm = chain.strip().upper()
    sku_norm = sku.strip().upper()
    channel_norm = channel.strip().upper()

    table = table[
        (table["chain"] == chain)
        & (table["channel"] == channel)
    ].copy()

    if table.empty:
        return table

    # Keep only brand-active stores
    if "status" in table.columns:
        table = table[table["status"] != "Inactive"].copy()

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

    target_sku_status = (
        table[
            table["sku"] == sku
        ][["coded_customer", "sku_status"]]
        .drop_duplicates()
    )

    target_sku_status = target_sku_status.rename(columns={
        "sku_status": "target_sku_status",
    })

    result = brand_stores.merge(
        target_sku_status,
        on="coded_customer",
        how="left",
    )

    result = result[
        result["target_sku_status"].isna()
        | result["target_sku_status"].eq("Inactive")
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
        "target_sku",
        "carried_skus",
        "num_skus_carried",
        "brand_units",
        "brand_reorders",
        "first_month_purchased",
        "last_month_purchased",
        "status",
        "target_sku_status",
    ]

    existing_cols = [col for col in columns if col in result.columns]

    return result[existing_cols].sort_values(
        "brand_units",
        ascending=False,
    )

def build_void_opportunity_insight(df, df_all_time):
    table = build_void_opportunity_table(df, df_all_time)

    analyzed = analyze_void_opportunity(table)

    data = normalize_void_opportunity_data(analyzed)

    if data is None:
        return None

    data_list = data if isinstance(data, list) else [data]

    insights = []

    for item in data_list:
        description = describe_void_opportunity(item)

        if description is None:
            continue

        sku = item["sku"]
        chain = item["chain"]
        channel = item["channel"]

        insights.append({
            "type": "distribution_opportunity",
            "section": "opportunities",

            **description,

            "metrics": item["metrics"],
            "entities": item["entities"],

            "sku": sku,
            "chain": chain,
            "channel": channel,
            "impact_units": item["captured_units"],

            "drilldown": {
                "label": "View opportunity stores",
                "href": (
                    f"/insights/distribution_opportunity"
                    f"?chain={chain}&sku={sku}&channel={channel}"
                ),
            },
        })

    if not insights:
        return None

    return insights
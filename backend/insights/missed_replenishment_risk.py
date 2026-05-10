import pandas as pd
from backend.insights.insights_helper import get_last_full_month, format_float, format_number, build_filter_context


def _build_store_replenishment_history_table(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Builds one row per chain x store with replenishment-history context.

    This is the core source-of-truth table for identifying stores
    that historically replenished consistently but recently stopped.
    """

    table = df.copy()

    last_full_month = get_last_full_month()
    latest_month_in_data = table["month_year"].max()
    four_month_history_window = [last_full_month - i for i in range(1, 5)]

    # STORE x MONTH PURCHASE FLAG
    store_month = (
        table.groupby(
            ["coded_customer", "month_year"],
            as_index=False,
        )
        .agg(
            units=("units", "sum"),
        )
    )

    store_month["purchased"] = store_month["units"] > 0

    trailing_4m = store_month[
        store_month["month_year"].isin(four_month_history_window)
    ].copy()

    purchase_history = (
        trailing_4m.groupby("coded_customer", as_index=False)
        .agg(
            months_purchased_last_4_prior=("purchased", "sum")
        )
    )

    last_month_flag = (
        store_month[store_month["month_year"] == last_full_month][["coded_customer", "purchased"]]
        .rename(columns={"purchased": "purchased_last_full_month"})
    )

    result = purchase_history.merge(
        last_month_flag,
        on="coded_customer",
        how="left",
    )

    result["purchased_last_full_month"] = (result["purchased_last_full_month"].fillna(False).astype(bool))

    # OPTIONAL CURRENT-MONTH CHECK
    if latest_month_in_data > last_full_month:

        current_month_flag = (
            store_month[
                store_month["month_year"] == latest_month_in_data
            ][["coded_customer", "purchased"]]
            .rename(columns={"purchased": "purchased_current_month"})
        )

        result = result.merge(
            current_month_flag,
            on=["coded_customer"],
            how="left",
        )

        result["purchased_current_month"] = (result["purchased_current_month"].fillna(False).astype(bool))

    else:
        result["purchased_current_month"] = False

    # STORE DETAILS
    store_details = (
        table.groupby(
            ["coded_customer"],
            as_index=False,
        )
        .agg(
            chain=("chain", "first"),
            dc=("dc", "first"),
            last_month_purchased=("last_month_purchased", "first"))
    )

    result = result.merge(
        store_details,
        on=["coded_customer"],
        how="left",
    )

    return result

def _attach_store_replenishment_metrics(
    table: pd.DataFrame,
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Adds supporting commercial context:
    - avg monthly units
    - carried skus
    - sku count
    """

    grain = ["coded_customer"]

    # AVG MONTHLY UNITS (LAST 4M)
    monthly_units = (
        df.groupby(
            grain + ["month_year"],
            as_index=False,
        )
        .agg(
            units=("units", "sum")
        )
    )

    avg_units = (
        monthly_units.groupby(
            grain,
            as_index=False,
        )
        .agg(
            avg_monthly_units_4m=("units", "mean")
        )
    )

    # CARRIED SKUS
    sku_table = (
        df.groupby(grain)
        .agg(
            carried_skus=("sku", lambda x: sorted(set(x))),
        ).reset_index()
    )

    sku_table["sku_count"] = (sku_table["carried_skus"].apply(len))

    return (
        table
        .merge(avg_units, on=grain, how="left")
        .merge(sku_table, on=grain, how="left")
    )

def build_order_cadence_risk_table(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Builds the analytical source-of-truth table for
    missed replenishment / order cadence risk insights.
    """

    table = _build_store_replenishment_history_table(df)
    table = _attach_store_replenishment_metrics(table=table, df=df)

    return table

def analyze_order_cadence_risk(
    table: pd.DataFrame,
) -> pd.DataFrame | None:
    """
    Returns the full universe of stores that had a consistent recent
    replenishment pattern but missed the latest expected replenishment.
    """

    if table is None or table.empty:
        return None

    table = table.copy()

    required_cols = [
        "coded_customer",
        "months_purchased_last_4_prior",
        "purchased_last_full_month",
        "purchased_current_month",
        "avg_monthly_units_4m",
    ]

    missing_cols = [col for col in required_cols if col not in table.columns]

    if missing_cols:
        return None

    affected = table[
        (table["months_purchased_last_4_prior"] >= 3)
        & (~table["purchased_last_full_month"])
        & (~table["purchased_current_month"])
        & (table["avg_monthly_units_4m"].fillna(0) > 0)
    ].copy()

    if "chain" in affected.columns:
        affected = affected[
            affected["chain"].notna()
            & ~affected["chain"].eq("CONFIDENTIAL")
        ].copy()

    if affected.empty:
        return None

    return affected.sort_values(
        ["avg_monthly_units_4m"],
        ascending=False,
    )

def normalize_order_cadence_risk_data(
    table: pd.DataFrame,
) -> dict | None:
    """
    Normalizes missed replenishment stores into a
    structured insight-ready object.
    """

    if table is None or table.empty:
        return None

    table = table.copy()

    MIN_CONCENTRATION_STORES = 3
    MIN_CONCENTRATION_SHARE = 0.40

    affected_stores = int(table["coded_customer"].nunique())

    avg_monthly_units_4m = float(table["avg_monthly_units_4m"].sum())

    avg_replenished_months = float(table["months_purchased_last_4_prior"].mean())

    # TOP CHAIN

    top_chain = None

    top_chain_table = (
        table.groupby("chain", as_index=False)
        .agg(
            stores=("coded_customer", "nunique"),
            units=("avg_monthly_units_4m", "sum"),
        )
        .sort_values(["stores", "units"], ascending=[False, False],
        )
    )

    if not top_chain_table.empty:

        top_chain_row = top_chain_table.iloc[0]

        top_chain = {
            "chain": top_chain_row["chain"],
            "stores": int(top_chain_row["stores"]),
            "units": float(top_chain_row["units"]),
            "share": float(
                top_chain_row["stores"] / affected_stores
            ),
        }

        top_chain["include"] = (
            top_chain["stores"] >= MIN_CONCENTRATION_STORES
            and top_chain["share"] >= MIN_CONCENTRATION_SHARE
        )

    # TOP DC

    top_dc = None

    top_dc_table = (
        table.groupby("dc", as_index=False)
        .agg(
            stores=("coded_customer", "nunique"),
            units=("avg_monthly_units_4m", "sum"),
        )
        .sort_values(
            ["stores", "units"],
            ascending=[False, False],
        )
    )

    if not top_dc_table.empty:

        top_dc_row = top_dc_table.iloc[0]

        top_dc = {
            "dc": top_dc_row["dc"],
            "stores": int(top_dc_row["stores"]),
            "units": float(top_dc_row["units"]),
            "share": float(
                top_dc_row["stores"] / affected_stores
            ),
        }

        top_dc["include"] = (
            top_dc["stores"] >= MIN_CONCENTRATION_STORES
            and top_dc["share"] >= MIN_CONCENTRATION_SHARE
        )

    # SINGLE SKU EXPOSURE

    top_single_sku = None

    single_sku_stores = table[
        table["sku_count"] == 1
    ].copy()

    single_sku_store_count = int(single_sku_stores["coded_customer"].nunique())

    if not single_sku_stores.empty:

        exploded = (
            single_sku_stores[
                ["coded_customer", "carried_skus"]
            ]
            .explode("carried_skus")
        )

        top_sku_table = (
            exploded.groupby(
                "carried_skus",
                as_index=False,
            )
            .agg(
                stores=("coded_customer", "nunique")
            )
            .sort_values(
                "stores",
                ascending=False,
            )
        )

        if not top_sku_table.empty:

            top_sku_row = top_sku_table.iloc[0]

            top_single_sku = {
                "sku": top_sku_row["carried_skus"],
                "stores": int(top_sku_row["stores"]),
                "share": float(
                    top_sku_row["stores"] / affected_stores
                ),
            }

            top_single_sku["include"] = (
                top_single_sku["stores"] >= MIN_CONCENTRATION_STORES
                and top_single_sku["share"] >= MIN_CONCENTRATION_SHARE
            )

    return {
        "affected_stores": affected_stores,

        "avg_monthly_units_4m": avg_monthly_units_4m,

        "avg_replenished_months": avg_replenished_months,

        "top_chain": top_chain,

        "top_dc": top_dc,

        "single_sku_store_count": single_sku_store_count,

        "top_single_sku": top_single_sku,

        "metrics": {
            "affected_stores": affected_stores,
            "avg_monthly_units_4m": avg_monthly_units_4m,
            "avg_replenished_months": avg_replenished_months,
            "single_sku_store_count": single_sku_store_count,
        },
    }

def describe_order_cadence_risk(
    data,
    filters=None,
):
    """
    Builds narrative description for missed replenishment risk.
    """

    if data is None:
        return None

    affected_stores = data["affected_stores"]

    avg_monthly_units_4m = data["avg_monthly_units_4m"]

    avg_replenished_months = data[
        "avg_replenished_months"
    ]

    top_chain = data.get("top_chain")
    top_dc = data.get("top_dc")

    single_sku_store_count = data.get(
        "single_sku_store_count"
    )

    top_single_sku = data.get(
        "top_single_sku"
    )

    context_str, context_parts = build_filter_context(
        filters,
    )

    # FORMAT

    affected_stores_fmt = format_number(affected_stores)

    avg_monthly_units_fmt = format_number(avg_monthly_units_4m)

    avg_replenished_months_fmt = format_float(avg_replenished_months,decimals=1)

    # HEADLINE

    headline = (
        f"{affected_stores_fmt} stores missed expected replenishment."
    )

    # SUMMARY

    summary = (
        f"{affected_stores_fmt} stores{context_str} "
        f"had replenished in an average of "
        f"{avg_replenished_months_fmt} of the prior 4 months, "
        f"but have not yet recorded a shipment this month."
    )

    # SUMMARY PARTS

    parts = [
        {
            "type": "chip",
            "value": affected_stores_fmt,
            "tone": "negative",
        },

        {
            "type": "text",
            "value": " stores",
        },

        *context_parts,

        {
            "type": "text",
            "value": (
                " had replenished in an average of "
            ),
        },

        {
            "type": "chip",
            "value": avg_replenished_months_fmt,
            "tone": "neutral",
        },

        {
            "type": "text",
            "value": (
                " of the prior 4 months, but have not yet "
                "recorded a shipment this month."
            ),
        },
    ]

    # DESCRIPTION BLOCKS

    intro_block = {
        "type": "text",
        "value": (
            f"{affected_stores_fmt} historically consistent "
            f"stores have not yet replenished within their "
            f"normal cadence{context_str}. "
            f"Over the last 4 months, these accounts averaged "
            f"a combined {avg_monthly_units_fmt} units per month."
        ),
    }

    replenishment_history_block = {
        "type": "text",
        "value": (
            f"Prior to the recent interruption, affected stores "
            f"had replenished in an average of "
            f"{avg_replenished_months_fmt} of the prior 4 months, "
            f"suggesting the behavior change is relatively recent "
            f"rather than part of a longer-term decline."
        ),
    }

    chain_block = None

    if top_chain is not None:

        chain_block = {
            "type": "text",
            "value": (
                f"Missed replenishments are also concentrated within "
                f"{top_chain['chain']}, which accounts for "
                f"{format_number(top_chain['stores'])} affected stores."
            ),
        }

    dc_block = None

    if top_dc is not None:

        dc_block = {
            "type": "text",
            "value": (
                f"Missed replenishments appear concentrated within "
                f"the {top_dc['dc']} distribution center, which "
                f"accounts for {format_number(top_dc['stores'])} "
                f"affected stores."
            ),
        }

    sku_block = None

    if (
        top_single_sku is not None
        and top_single_sku.get("include")
    ):

        sku_block = {
            "type": "text",
            "value": (
                f"{format_number(single_sku_store_count)} affected "
                f"stores currently carry only "
                f"{top_single_sku['sku']}, suggesting the disruption "
                f"may be tied to a specific SKU rather than broader "
                f"store-level disengagement."
            ),
        }

    operational_block = {
        "type": "text",
        "value": (
            "Early follow-up may help identify inventory gaps, "
            "reset activity, or distribution disruptions before "
            "they become longer-term losses."
        ),
    }

    description = [
        intro_block,
        replenishment_history_block,
        chain_block,
        dc_block,
        sku_block,
        operational_block,
    ]

    description = [
        block for block in description
        if block is not None
    ]

    return {
        "headline": headline,
        "summary": summary,
        "parts": parts,
        "description": description,
    }

def create_order_cadence_risk_store_list(
    analyzed_table: pd.DataFrame,
) -> pd.DataFrame:
    """
    Returns the store-level drilldown for missed replenishment risk.

    Uses the analyzed affected-store universe directly so the
    insight and drilldown always stay aligned.
    """

    if analyzed_table is None or analyzed_table.empty:
        return pd.DataFrame()

    table = analyzed_table.copy()

    columns = [
        "coded_customer",
        "dc",
        "avg_monthly_units_4m",
        "months_purchased_last_4_prior",
        "last_month_purchased",
        "sku_count",
        "carried_skus",
    ]

    existing_cols = [col for col in columns if col in table.columns]

    result = table[existing_cols].copy()

    return result.sort_values(
        ["avg_monthly_units_4m", "months_purchased_last_4_prior"],
        ascending=[False, False],
    )

def build_order_cadence_risk_insight(
    df: pd.DataFrame,
    filters=None,
):
    table = build_order_cadence_risk_table(df)

    analyzed = analyze_order_cadence_risk(table)

    data = normalize_order_cadence_risk_data(analyzed)

    description = describe_order_cadence_risk(data=data, filters=filters)

    if data is None or description is None:
        return None

    return {
        "type": "order_cadence_risk",
        "section": "at_risk",

        **description,

        "metrics": data["metrics"],
        "entities": {},

        "drilldown": {
            "label": "View missed replenishment stores",
            "href": "/insights/order_cadence_risk",
        },
    }
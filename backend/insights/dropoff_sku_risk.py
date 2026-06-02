import pandas as pd

from backend.insights.insights_helper import build_filter_context, format_number, format_pct, get_last_full_month


DEFAULT_LIMIT = 1

MIN_AFFECTED_STORES = 10
MIN_AFFECTED_STORE_SHARE = 0
MIN_TOTAL_PRIOR_SKU_UNITS = 1
MIN_CONCENTRATION_STORES = 3
MIN_CONCENTRATION_SHARE = 0.5


def build_dropoff_sku_risk_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Builds one row per store x SKU where the store previously bought the SKU,
    stopped buying that SKU recently, but is still buying the brand.

    Assumes names/fields are already normalized before reaching the insight layer.
    """

    if df is None or df.empty:
        return pd.DataFrame()

    required_cols = ["coded_customer", "sku", "month_year", "units"]
    if any(col not in df.columns for col in required_cols):
        return pd.DataFrame()

    table = df.copy()

    last_full_month = get_last_full_month()
    latest_month_in_data = table["month_year"].max()
    recent_months = [last_full_month - i for i in range(0, 3)]
    prior_months = [last_full_month - i for i in range(3, 6)]

    store_sku_units = table.groupby(["coded_customer", "sku", "month_year"], as_index=False).agg(units=("units", "sum"))

    prior_sku = store_sku_units[store_sku_units["month_year"].isin(prior_months)].groupby(["coded_customer", "sku"], as_index=False).agg(prior_3m_sku_units=("units", "sum"))
    recent_sku = store_sku_units[store_sku_units["month_year"].isin(recent_months)].groupby(["coded_customer", "sku"], as_index=False).agg(recent_3m_sku_units=("units", "sum"))

    result = prior_sku.merge(recent_sku, on=["coded_customer", "sku"], how="outer").fillna({"prior_3m_sku_units": 0, "recent_3m_sku_units": 0})

    store_brand_units = table.groupby(["coded_customer", "month_year"], as_index=False).agg(units=("units", "sum"))
    recent_brand = store_brand_units[store_brand_units["month_year"].isin(recent_months)].groupby("coded_customer", as_index=False).agg(recent_3m_brand_units=("units", "sum"))

    result = result.merge(recent_brand, on="coded_customer", how="left").fillna({"recent_3m_brand_units": 0})

    if latest_month_in_data > last_full_month:
        current_sku = store_sku_units[store_sku_units["month_year"] == latest_month_in_data].groupby(["coded_customer", "sku"], as_index=False).agg(current_month_sku_units=("units", "sum"))
        result = result.merge(current_sku, on=["coded_customer", "sku"], how="left").fillna({"current_month_sku_units": 0})
    else:
        result["current_month_sku_units"] = 0

    result["purchased_sku_current_month"] = result["current_month_sku_units"].fillna(0) > 0

    prior_purchase_months = store_sku_units[(store_sku_units["units"] > 0) & (store_sku_units["month_year"] <= last_full_month)].groupby(["coded_customer", "sku"], as_index=False).agg(last_month_sku_purchased=("month_year", "max"))
    result = result.merge(prior_purchase_months, on=["coded_customer", "sku"], how="left")

    recent_brand_skus = table[(table["month_year"].isin(recent_months)) & (table["units"] > 0)].groupby("coded_customer").agg(recent_brand_skus=("sku", lambda x: sorted(set(x)))).reset_index()
    result = result.merge(recent_brand_skus, on="coded_customer", how="left")

    store_detail_cols = [col for col in ["coded_customer", "chain", "dc", "state"] if col in table.columns]
    store_details = table[store_detail_cols].drop_duplicates(subset=["coded_customer"]).copy()
    result = result.merge(store_details, on="coded_customer", how="left")

    result = result[
        (result["prior_3m_sku_units"].fillna(0) > 0)
        & (result["recent_3m_sku_units"].fillna(0) == 0)
        & (result["recent_3m_brand_units"].fillna(0) > 0)
        & (~result["purchased_sku_current_month"])
    ].copy()

    total_recent_brand_stores = recent_brand[recent_brand["recent_3m_brand_units"].fillna(0) > 0]["coded_customer"].nunique()
    result["total_recent_brand_stores"] = total_recent_brand_stores

    return result.sort_values(["prior_3m_sku_units", "recent_3m_brand_units"], ascending=[False, False])


def analyze_dropoff_sku_risk(table: pd.DataFrame, limit: int = DEFAULT_LIMIT) -> pd.DataFrame | None:
    if table is None or table.empty:
        return None

    required_cols = ["sku", "coded_customer", "prior_3m_sku_units", "recent_3m_brand_units", "total_recent_brand_stores"]
    if any(col not in table.columns for col in required_cols):
        return None

    sku_summary = table.groupby("sku", as_index=False).agg(
        affected_stores=("coded_customer", "nunique"),
        prior_3m_sku_units=("prior_3m_sku_units", "sum"),
        recent_3m_brand_units=("recent_3m_brand_units", "sum"),
        total_recent_brand_stores=("total_recent_brand_stores", "max"),
    )

    sku_summary["affected_store_share"] = sku_summary["affected_stores"] / sku_summary["total_recent_brand_stores"].replace(0, pd.NA)

    candidates = sku_summary[
        (sku_summary["affected_stores"].fillna(0) >= MIN_AFFECTED_STORES)
        & (sku_summary["affected_store_share"].fillna(0) >= MIN_AFFECTED_STORE_SHARE)
        & (sku_summary["prior_3m_sku_units"].fillna(0) >= MIN_TOTAL_PRIOR_SKU_UNITS)
    ].copy()

    if candidates.empty:
        return None

    candidates["risk_score"] = candidates["affected_store_share"].fillna(0) + candidates["affected_stores"].fillna(0) / 100 + candidates["prior_3m_sku_units"].fillna(0) / 10000

    return candidates.sort_values(["risk_score", "affected_stores", "prior_3m_sku_units"], ascending=[False, False, False]).head(limit)


def normalize_dropoff_sku_risk_data(analyzed_table: pd.DataFrame, detail_table: pd.DataFrame) -> dict | None:
    if analyzed_table is None or analyzed_table.empty or detail_table is None or detail_table.empty:
        return None

    items = []

    for _, row in analyzed_table.iterrows():
        sku = row["sku"]
        affected = detail_table[detail_table["sku"] == sku].copy()

        if affected.empty:
            continue

        affected_stores = int(affected["coded_customer"].nunique())
        prior_3m_sku_units = float(affected["prior_3m_sku_units"].sum())
        recent_3m_brand_units = float(affected["recent_3m_brand_units"].sum())
        total_recent_brand_stores = int(row.get("total_recent_brand_stores") or 0)
        affected_store_share = row.get("affected_store_share")

        top_chain = None
        if "chain" in affected.columns:
            chain_table = affected.groupby("chain", as_index=False).agg(stores=("coded_customer", "nunique"), prior_3m_sku_units=("prior_3m_sku_units", "sum")).sort_values(["stores", "prior_3m_sku_units"], ascending=[False, False])
            if not chain_table.empty:
                top_chain_row = chain_table.iloc[0]
                top_chain = {"chain": top_chain_row["chain"], "stores": int(top_chain_row["stores"]), "prior_3m_sku_units": float(top_chain_row["prior_3m_sku_units"]), "share": float(top_chain_row["stores"] / affected_stores)}
                top_chain["include"] = top_chain["stores"] >= MIN_CONCENTRATION_STORES and top_chain["share"] >= MIN_CONCENTRATION_SHARE

        top_dc = None
        if "dc" in affected.columns:
            dc_table = affected.groupby("dc", as_index=False).agg(stores=("coded_customer", "nunique"), prior_3m_sku_units=("prior_3m_sku_units", "sum")).sort_values(["stores", "prior_3m_sku_units"], ascending=[False, False])
            if not dc_table.empty:
                top_dc_row = dc_table.iloc[0]
                top_dc = {"dc": top_dc_row["dc"], "stores": int(top_dc_row["stores"]), "prior_3m_sku_units": float(top_dc_row["prior_3m_sku_units"]), "share": float(top_dc_row["stores"] / affected_stores)}
                top_dc["include"] = top_dc["stores"] >= MIN_CONCENTRATION_STORES and top_dc["share"] >= MIN_CONCENTRATION_SHARE

        item = {
            "sku": sku,
            "affected_stores": affected_stores,
            "affected_store_share": affected_store_share,
            "total_recent_brand_stores": total_recent_brand_stores,
            "prior_3m_sku_units": prior_3m_sku_units,
            "recent_3m_brand_units": recent_3m_brand_units,
            "top_chain": top_chain,
            "top_dc": top_dc,
        }

        item["metrics"] = {k: v for k, v in item.items() if k not in ["sku", "top_chain", "top_dc"]}
        item["entities"] = {"sku": sku, "chain": top_chain["chain"] if top_chain and top_chain.get("include") else None, "dc": top_dc["dc"] if top_dc and top_dc.get("include") else None}
        items.append(item)

    if not items:
        return None

    return {"items": items, "metrics": items[0]["metrics"], "entities": items[0]["entities"]}


def describe_dropoff_sku_risk(data: dict | None, filters=None) -> dict | None:
    if data is None or not data.get("items"):
        return None

    item = data["items"][0]
    context_str, context_parts = build_filter_context(filters, exclude_keys={"sku"})

    sku = item["sku"]
    affected_stores_fmt = format_number(item["affected_stores"])
    affected_store_share_fmt = format_pct(item["affected_store_share"])
    prior_units_fmt = format_number(item["prior_3m_sku_units"])
    recent_brand_units_fmt = format_number(item["recent_3m_brand_units"])

    headline = f"{sku} dropped off in active brand stores."
    summary = f"{sku}{context_str} dropped out of {affected_stores_fmt} stores that are still buying the brand."

    parts = [
        {"type": "chip", "value": sku, "tone": "negative"},
        *context_parts,
        {"type": "text", "value": " dropped out of "},
        {"type": "chip", "value": affected_stores_fmt, "tone": "negative"},
        {"type": "text", "value": " stores that are still buying the brand."},
    ]

    description = [
        {"type": "text", "value": f"{sku} has dropped off in {affected_stores_fmt} active brand stores{context_str}. These stores bought {prior_units_fmt} units of {sku} in the prior 3 months, but bought none in the latest 3 full months while still buying the brand."},
        {"type": "text", "value": f"Together, these stores still bought {recent_brand_units_fmt} brand units recently, so this looks more like a SKU-specific issue than a fully lost store relationship. The affected stores represent about {affected_store_share_fmt} of recent active brand stores."},
    ]

    top_chain = item.get("top_chain")
    if top_chain and top_chain.get("include"):
        description.append({"type": "text", "value": f"The issue is concentrated in {top_chain['chain']}, which accounts for {format_number(top_chain['stores'])} affected stores."})

    top_dc = item.get("top_dc")
    if top_dc and top_dc.get("include"):
        description.append({"type": "text", "value": f"Affected stores are also concentrated in the {top_dc['dc']} DC, which may be worth checking for availability, setup, or distribution issues."})

    description.append({"type": "text", "value": "Because these stores are still buying other SKUs, this is a practical follow-up list: check whether the SKU is still authorized, available, correctly set up, or being displaced by other items."})

    return {"headline": headline, "summary": summary, "parts": parts, "description": description}


def create_dropoff_sku_risk_store_list(analyzed_table: pd.DataFrame, detail_table: pd.DataFrame) -> pd.DataFrame:
    if analyzed_table is None or analyzed_table.empty or detail_table is None or detail_table.empty:
        return pd.DataFrame()

    sku = analyzed_table.iloc[0]["sku"]
    result = detail_table[detail_table["sku"] == sku].copy()

    output_cols = [col for col in ["coded_customer", "chain", "dc", "state", "sku", "prior_3m_sku_units", "recent_3m_sku_units", "recent_3m_brand_units", "recent_brand_skus", "last_month_sku_purchased"] if col in result.columns]

    return result[output_cols].sort_values(["prior_3m_sku_units", "recent_3m_brand_units"], ascending=[False, False])


def build_dropoff_sku_risk_insight(df: pd.DataFrame, filters=None, limit: int = DEFAULT_LIMIT):
    detail_table = build_dropoff_sku_risk_table(df)
    analyzed = analyze_dropoff_sku_risk(detail_table, limit=limit)
    data = normalize_dropoff_sku_risk_data(analyzed_table=analyzed, detail_table=detail_table)
    description = describe_dropoff_sku_risk(data=data, filters=filters)

    if data is None or description is None:
        return None

    item = data["items"][0]

    return {
        "type": "dropoff_sku_risk",
        "section": "at_risk",
        **description,
        "metrics": item["metrics"],
        "entities": item["entities"],
        "drilldown": {"label": "View affected stores", "href": "/insights/dropoff_sku_risk"},
    }

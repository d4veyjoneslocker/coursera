from fastapi import APIRouter, Depends, Query
from typing import Optional, List
import time

from backend.serving.api_helpers import clean_for_json
from backend.metrics.metric_tables import chain_insight_table, sku_insight_table, channel_reorder_insight_table, chain_sku_velocity_gap_opportunity_table, top_sales_month_insight_table, distribution_opportunity_store_detail_table
from backend.insights.chain_insights import (
    build_chain_growth_insight,
    build_chain_decline_insight,
)
from backend.insights.sku_insights import build_sku_velocity_insight, build_void_opportunity_insight, build_velocity_gap_opportunity_insight
from backend.insights.channel_insights import build_channel_reorder_driver_insight
from backend.insights.store_health_insights import build_chain_struggling_insight
from backend.filters.filters import get_filters  # assuming you already have this
from backend.filters.filter_table import filter_table
from backend.serving.api_helpers import clean_for_json  # or wherever this lives
from backend.data_pipeline.table_loader import load_org_tables
from backend.insights.sales_insights import build_top_sales_month_insight, build_top_reorder_rate_month_insight
from backend.exports.insights_email.email_tables import chain_struggling_store_detail_table
from backend.insights.failure_to_launch_new_store_risk import build_failure_to_launch_new_store_risk_insight
from backend.insights.overperforming_channel_momentum import build_overperforming_channel_momentum_insight
from backend.insights.dropoff_sku_risk import (
    build_dropoff_sku_risk_table,
    analyze_dropoff_sku_risk,
    create_dropoff_sku_risk_store_list,
)

from backend.insights.missed_replenishment_risk import (
    build_order_cadence_risk_table,
    analyze_order_cadence_risk,
    create_order_cadence_risk_store_list,
)


router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get("/overview")
def get_overview_insights(
    org_id: str = Query(...),
    filters: dict = Depends(get_filters),
):
    TIME_FILTERS = {"year", "month", "month_year"}

    has_time_filter = any(filters.get(k) for k in TIME_FILTERS)
    if has_time_filter:
        return []

    features_df = load_org_tables(org_id)

    NON_TIME_FILTERS = {
        k: v for k, v in filters.items()
        if k not in TIME_FILTERS
    }

    df = filter_table(features_df, **filters)
    df_all_time = filter_table(features_df, **NON_TIME_FILTERS)

    chain_df = chain_insight_table(df)
    sku_df = sku_insight_table(df)

    #chain_velocity_gap_df = chain_sku_velocity_gap_opportunity_table(
    #    df,
    #    df_all_time,
    #)

    insights = []

    # ✅ pass filters
    chain_growth = build_chain_growth_insight(chain_df, filters=filters)
    sku_velocity = build_sku_velocity_insight(sku_df, filters=filters)

    top_sales_month_df = top_sales_month_insight_table(df, df_all_time)
    top_sales_month = build_top_sales_month_insight(top_sales_month_df)

    #velocity_gap = build_velocity_gap_opportunity_insight(chain_velocity_gap_df)

    if top_sales_month:
        insights.append(top_sales_month)

    if chain_growth:
        insights.append(chain_growth)

    if sku_velocity:
        insights.append(sku_velocity)

    #if velocity_gap:
    #    insights.append(velocity_gap)

    BLOCK_VOID_FILTERS = {"sku", "status"}
    has_blocked_void_filter = any(filters.get(k) for k in BLOCK_VOID_FILTERS)

    if not has_blocked_void_filter:
        void_filters = {
            k: v for k, v in NON_TIME_FILTERS.items()
            if k not in BLOCK_VOID_FILTERS
        }

        void_df = filter_table(features_df, **void_filters)

        #opportunity_df = chain_sku_velocity_gap_opportunity_table(
        #    void_df,
        #    void_df,
        #)

        #sku_voids = build_void_opportunity_insight(
        #    opportunity_df,
        #    filters=filters,
        #)

        #if sku_voids:
        #    insights.append(sku_voids)

    return insights

@router.get("/store-health")
def get_store_health_insights(
    org_id: str = Query(...),
    filters: dict = Depends(get_filters),
):
    features_df = load_org_tables(org_id)
    df = filter_table(features_df, **filters)
    df

    insights = []

    TIME_FILTERS = {"year", "month", "month_year"}

    NON_TIME_FILTERS = {
        k: v for k, v in filters.items()
        if k not in TIME_FILTERS
    }

    df_all_time = filter_table(features_df, **NON_TIME_FILTERS)

    top_sales_month_df = top_sales_month_insight_table(df, df_all_time)

    top_reorder_rate = build_top_reorder_rate_month_insight(top_sales_month_df)

    if top_reorder_rate:
        insights.append(top_reorder_rate)

    channel_reorder_df = channel_reorder_insight_table(
        df,
        df_all_time,
    )

    # ✅ pass filters
    channel_reorder = build_channel_reorder_driver_insight(
        channel_reorder_df,
        filters=filters,
    )

    if channel_reorder:
        insights.append(channel_reorder)

    # ✅ pass filters
    store_health_mix = build_chain_struggling_insight(df, filters=filters)

    if store_health_mix:
        insights.append(store_health_mix)

    return insights

@router.get("/struggling_stores")
def get_chain_struggling_stores(
    org_id: str = Query(...),
    chain: str = Query(...),
):
    features_df = load_org_tables(org_id)

    df = features_df.copy()

    table = chain_struggling_store_detail_table(df, df, chain=chain)

    if table.empty:
        return {
            "title": f"Struggling stores in {chain}",
            "subtitle": "No struggling stores found.",
            "columns": [],
            "rows": [],
        }
    
    result = clean_for_json(table)

    return {
        "title": f"Struggling stores in {chain}",
        "subtitle": "Stores currently marked as struggling, ranked by unit volume.",
        "columns": [
            {"key": "coded_customer", "label": "Customer", "align": "left"},
            {"key": "chain", "label": "Chain", "align": "left"},
            {"key": "units", "label": "Units", "align": "right", "format": "number"},
            {"key": "revenue", "label": "Revenue", "align": "right", "format": "currency"},
            {"key": "reorders", "label": "Reorders", "align": "right", "format": "number"},
            {"key": "first_month_purchased", "label": "First Order", "align": "left", "format": "month"},
            {"key": "last_month_purchased", "label": "Last Order", "align": "left", "format": "month"},
            {"key": "status", "label": "Status", "align": "left", "format": "status"},
        ],
        "rows": table.to_dict(orient="records"),
    }

@router.get("/distribution_opportunity")
def get_distribution_opportunity_stores(
    org_id: str = Query(...),
    chain: str = Query(...),
    sku: str = Query(...),
    channel: str = Query(...),
):
    features_df = load_org_tables(org_id)

    df = features_df.copy()

    table = distribution_opportunity_store_detail_table(
        df=df,
        chain=chain,
        sku=sku,
        channel=channel,
    )

    if table.empty:
        return {
            "title": f"Opportunity stores for {sku} in {chain}",
            "subtitle": "No opportunity stores found.",
            "columns": [],
            "rows": [],
        }

    cleaned = clean_for_json(table)
    result = cleaned.to_dict(orient="records")

    return {
        "title": f"Opportunity stores for {sku} in {chain}",
        "subtitle": (
            f"Stores in {chain} that buy the brand, "
            f"but do not currently carry {sku}."
        ),
        "columns": [
            {"key": "coded_customer", "label": "Customer", "align": "left"},            {"key": "street_address", "label": "Address", "align": "left"},
            {"key": "city", "label": "City", "align": "left"},
            {"key": "state", "label": "State", "align": "left"},
            {"key": "zip", "label": "ZIP", "align": "left"},
            {"key": "carried_skus", "label": "Carried SKUs", "align": "left", "format": "sku_pills"},
            {"key": "brand_units", "label": "Brand Units", "align": "right", "format": "number"},
            {"key": "first_month_purchased", "label": "First Order", "align": "left", "format": "month"},
            {"key": "last_month_purchased", "label": "Last Order", "align": "left", "format": "month"},
            {"key": "brand_reorders", "label": "Reorders", "align": "left", "format": "month"},
            {"key": "status", "label": "Status", "align": "left", "format": "status"},
            ],
        "rows": result,
    }

@router.get("/failure-to-launch")
def get_failure_to_launch_insight(
    org_id: str = Query(...),
    filters: dict = Depends(get_filters),
):
    features_df = load_org_tables(org_id)
    df = filter_table(features_df, **filters)

    insight = build_failure_to_launch_new_store_risk_insight(
        df,
        filters=filters,
    )

    return insight or {}


@router.get("/channel-momentum")
def get_channel_momentum_insight(
    org_id: str = Query(...),
    filters: dict = Depends(get_filters),
):
    features_df = load_org_tables(org_id)
    df = filter_table(features_df, **filters)

    insight = build_overperforming_channel_momentum_insight(
        df,
        filters=filters,
    )

    return insight or {}

@router.get("/dropoff_sku_risk")
def get_dropoff_sku_risk_stores(
    org_id: str = Query(...),
    sku: str = Query(...),
):
    features_df = load_org_tables(org_id)

    detail_table = build_dropoff_sku_risk_table(
        features_df
    )

    analyzed = analyze_dropoff_sku_risk(
        detail_table,
        limit=10,
    )

    if analyzed is None or analyzed.empty:
        return {
            "title": f"Stores that dropped {sku}",
            "subtitle": "No affected stores found.",
            "columns": [],
            "rows": [],
        }

    # The store-list helper uses the first SKU in analyzed_table,
    # so explicitly isolate the SKU from the clicked insight.
    selected = analyzed[
        analyzed["sku"] == sku
    ].copy()

    if selected.empty:
        return {
            "title": f"Stores that dropped {sku}",
            "subtitle": "No affected stores found.",
            "columns": [],
            "rows": [],
        }

    table = create_dropoff_sku_risk_store_list(
        analyzed_table=selected,
        detail_table=detail_table,
    )

    cleaned = clean_for_json(table)

    return {
        "title": f"Stores that dropped {sku}",
        "subtitle": (
            f"Stores that previously purchased {sku}, "
            "have not purchased it in the latest 3 full months, "
            "but are still purchasing your brand."
        ),
        "columns": [
            {
                "key": "coded_customer",
                "label": "Customer",
                "align": "left",
            },
            {
                "key": "chain",
                "label": "Chain",
                "align": "left",
            },
            {
                "key": "dc",
                "label": "DC",
                "align": "left",
            },
            {
                "key": "state",
                "label": "State",
                "align": "left",
            },
            {
                "key": "prior_3m_sku_units",
                "label": "Prior 3M SKU Units",
                "align": "right",
                "format": "number",
            },
            {
                "key": "recent_3m_brand_units",
                "label": "Recent Brand Units",
                "align": "right",
                "format": "number",
            },
            {
                "key": "recent_brand_skus",
                "label": "Current SKUs",
                "align": "left",
                "format": "sku_pills",
            },
            {
                "key": "last_month_sku_purchased",
                "label": "Last SKU Order",
                "align": "left",
                "format": "month",
            },
        ],
        "rows": cleaned.to_dict(orient="records"),
    }

@router.get("/order_cadence_risk")
def get_order_cadence_risk_stores(
    org_id: str = Query(...),
):
    features_df = load_org_tables(org_id)

    table = build_order_cadence_risk_table(
        features_df
    )

    analyzed = analyze_order_cadence_risk(
        table
    )

    if analyzed is None or analyzed.empty:
        return {
            "title": "Missed replenishment stores",
            "subtitle": "No missed replenishment stores found.",
            "columns": [],
            "rows": [],
        }

    store_list = create_order_cadence_risk_store_list(
        analyzed
    )

    cleaned = clean_for_json(store_list)

    return {
        "title": "Missed replenishment stores",
        "subtitle": (
            "Stores that had been ordering consistently "
            "but did not receive their expected recent replenishment."
        ),
        "columns": [
            {
                "key": "coded_customer",
                "label": "Customer",
                "align": "left",
            },
            {
                "key": "dc",
                "label": "DC",
                "align": "left",
            },
            {
                "key": "avg_monthly_units_4m",
                "label": "Typical Monthly Units",
                "align": "right",
                "format": "number",
            },
            {
                "key": "months_purchased_last_4_prior",
                "label": "Prior 4M Orders",
                "align": "right",
                "format": "number",
            },
            {
                "key": "last_month_purchased",
                "label": "Last Order",
                "align": "left",
                "format": "month",
            },
            {
                "key": "sku_count",
                "label": "SKUs",
                "align": "right",
                "format": "number",
            },
            {
                "key": "carried_skus",
                "label": "Carried SKUs",
                "align": "left",
                "format": "sku_pills",
            },
        ],
        "rows": cleaned.to_dict(orient="records"),
    }
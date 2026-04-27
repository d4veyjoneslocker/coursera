from fastapi import APIRouter, Depends, Query
from typing import Optional, List

from backend.metrics.metric_tables import chain_insight_table, sku_insight_table, channel_reorder_insight_table
from backend.insights.chain_insights import build_chain_growth_insight
from backend.insights.sku_insights import build_sku_velocity_insight
from backend.insights.channel_insights import build_channel_reorder_driver_insight
from backend.insights.store_health_insights import build_chain_struggling_insight
from backend.filters.filters import get_filters  # assuming you already have this
from backend.filters.filter_table import filter_table
from backend.serving.api_helpers import clean_for_json  # or wherever this lives
from backend.data_pipeline.table_loader import load_org_tables


router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get("/overview")
def get_overview_insights(
    org_id: str = Query(...),
    filters: dict = Depends(get_filters),
):
    features_df = load_org_tables(org_id)
    df = filter_table(features_df, **filters)

    chain_df = chain_insight_table(df)
    sku_df = sku_insight_table(df)

    insights = []

    chain_growth = build_chain_growth_insight(chain_df)
    sku_velocity = build_sku_velocity_insight(sku_df)

    if chain_growth:
        insights.append(chain_growth)

    if sku_velocity:
        insights.append(sku_velocity)

    return insights

@router.get("/store-health")
def get_store_health_insights(
    org_id: str = Query(...),
    filters: dict = Depends(get_filters),
):
    features_df = load_org_tables(org_id)
    df = filter_table(features_df, **filters)

    insights = []

    # 1. Channel reorder driver
    channel_reorder_df = channel_reorder_insight_table(df, features_df)
    channel_reorder = build_channel_reorder_driver_insight(channel_reorder_df)

    if channel_reorder:
        insights.append(channel_reorder)

    # 2. Store health mix shift
    store_health_mix = build_chain_struggling_insight(df)

    if store_health_mix:
        insights.append(store_health_mix)

    return insights
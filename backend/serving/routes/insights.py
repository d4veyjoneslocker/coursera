from fastapi import APIRouter, Depends, Query
from typing import Optional, List
import time

from backend.metrics.metric_tables import chain_insight_table, sku_insight_table, channel_reorder_insight_table, chain_sku_velocity_gap_opportunity_table
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

    #velocity_gap = build_velocity_gap_opportunity_insight(chain_velocity_gap_df)

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

        # ✅ pass filters
        sku_voids = build_void_opportunity_insight(void_df, filters=filters)

        if sku_voids:
            insights.append(sku_voids)

    return insights

@router.get("/store-health")
def get_store_health_insights(
    org_id: str = Query(...),
    filters: dict = Depends(get_filters),
):
    features_df = load_org_tables(org_id)
    df = filter_table(features_df, **filters)

    insights = []

    TIME_FILTERS = {"year", "month", "month_year"}

    NON_TIME_FILTERS = {
        k: v for k, v in filters.items()
        if k not in TIME_FILTERS
    }

    df_all_time_same_filters = filter_table(features_df, **NON_TIME_FILTERS)

    channel_reorder_df = channel_reorder_insight_table(
        df,
        df_all_time_same_filters,
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
from fastapi import APIRouter, Depends, Query
from backend.filters.filters import get_filters, Filters
from backend.filters.filter_table import filter_table
from backend.data_pipeline.table_loader import load_org_tables, load_active_pods
from backend.serving.api_helpers import clean_for_json
from backend.insights.missed_replenishment_risk import build_order_cadence_risk_insight, build_order_cadence_risk_table, create_order_cadence_risk_store_list, analyze_order_cadence_risk
from backend.insights.failure_to_launch_new_store_risk import (
    build_failure_to_launch_new_store_risk_insight,
    build_failure_to_launch_new_store_risk_table,
    create_failure_to_launch_new_store_risk_store_list,
    get_failure_to_launch_new_store_risk_drilldown_config
)
from backend.insights.growing_region_momentum import (
    build_growing_region_momentum_insight,
    build_growing_region_momentum_table,
    analyze_growing_region_momentum,
    create_growing_region_momentum_store_list,
)
from backend.insights.overperforming_channel_momentum import (
    build_overperforming_channel_momentum_insight,
    build_overperforming_channel_momentum_table,
    analyze_overperforming_channel_momentum,
    create_overperforming_channel_momentum_store_list,
    get_overperforming_channel_momentum_drilldown_config
)
from backend.insights.dropoff_sku_risk import (
    build_dropoff_sku_risk_insight,
    build_dropoff_sku_risk_table,
    analyze_dropoff_sku_risk,
    create_dropoff_sku_risk_store_list,
)
from backend.insights.sales_change_driver import build_sales_change_driver_insight
from backend.insights.void_sku_opportunity import create_void_opportunity_store_list
from backend.insights.struggling_chain_risk import create_chain_struggling_store_list

from backend.deep_dive.digest_builder import build_weekly_digest

router = APIRouter(prefix="/insights_new", tags=["New Insights"])

@router.get("/order_cadence_risk")
def get_order_cadence_risk(
    org_id: str,
    filters: Filters = Depends(get_filters),
):
    df = load_org_tables(org_id)

    df_filtered = filter_table(df, **filters)

    insight = build_order_cadence_risk_insight(
        df=df_filtered,
        filters=filters,
    )

    return insight

@router.get("/order_cadence_risk/stores")
def get_order_cadence_risk_stores(
    org_id: str,
    filters: Filters = Depends(get_filters),
):
    df = load_org_tables(org_id)

    df_filtered = filter_table(df, **filters)

    table = build_order_cadence_risk_table(df_filtered)
    analyzed = analyze_order_cadence_risk(table)

    store_list = create_order_cadence_risk_store_list(analyzed)

    return {
        "title": "Missed Replenishment Stores",
        "subtitle": (
            "Stores that had been ordering consistently "
            "but missed an expected recent replenishment."
        ),
        "columns": [
            {
                "key": "coded_customer",
                "label": "Store",
            },
            {
                "key": "dc",
                "label": "DC",
            },
            {
                "key": "avg_monthly_units_4m",
                "label": "Avg Monthly Units",
            },
            {
                "key": "months_purchased_last_4_prior",
                "label": "Months Purchased",
            },
            {
                "key": "last_month_purchased",
                "label": "Last Purchased",
            },
            {
                "key": "sku_count",
                "label": "SKUs",
            },
            {
                "key": "carried_skus",
                "label": "Carried SKUs",
            },
        ],
        "rows": clean_for_json(store_list).to_dict("records"),
    }

@router.get("/failure_to_launch_new_store_risk")
def get_failure_to_launch_new_store_risk(
    org_id: str,
    filters: dict = Depends(get_filters),
):
    df = load_org_tables(org_id)

    df_filtered = filter_table(df, **filters)

    insight = build_failure_to_launch_new_store_risk_insight(
        df=df_filtered,
        filters=filters,
    )

    return insight

@router.get("/failure_to_launch_new_store_risk/stores")
def get_failure_to_launch_new_store_risk_stores(
    org_id: str,
    launch_cohort_id: str,
    filters: dict = Depends(get_filters),
):
    df = load_org_tables(org_id)

    df_filtered = filter_table(df, **filters)

    tables = build_failure_to_launch_new_store_risk_table(
        df=df_filtered,
    )

    store_list = create_failure_to_launch_new_store_risk_store_list(
        launch_events=tables["launch_events"],
        launch_cohort_id=launch_cohort_id,
    )

    config = get_failure_to_launch_new_store_risk_drilldown_config(
        launch_cohort_id=launch_cohort_id,
    )

    return {
        **config,
        "rows": clean_for_json(store_list).to_dict("records"),
    }


@router.get("/growing_region_momentum")
def get_growing_region_momentum(
    org_id: str,
    limit: int = Query(1, ge=1, le=10),
    filters: Filters = Depends(get_filters),
):
    df = load_org_tables(org_id)
    active_pods_df = load_active_pods(org_id)

    df_filtered = filter_table(df, **filters)
    active_pods_filtered = filter_table(active_pods_df, **filters)

    insight = build_growing_region_momentum_insight(
        df=df_filtered,
        active_pods_df=active_pods_filtered,
        filters=filters,
        limit=limit,
    )

    return insight


@router.get("/growing_region_momentum/stores")
def get_growing_region_momentum_stores(
    org_id: str,
    filters: Filters = Depends(get_filters),
):
    df = load_org_tables(org_id)
    active_pods_df = load_active_pods(org_id)

    df_filtered = filter_table(df, **filters)
    active_pods_filtered = filter_table(active_pods_df, **filters)

    table = build_growing_region_momentum_table(
        df=df_filtered,
        active_pods_df=active_pods_filtered,
    )

    analyzed = analyze_growing_region_momentum(table)

    result = clean_for_json(
        create_growing_region_momentum_store_list(
            df=df_filtered,
            analyzed_table=analyzed,
        )
    ).to_dict("records")

    return result

@router.get("/overperforming_channel_momentum")
def get_overperforming_channel_momentum(
    org_id: str,
    limit: int = Query(1, ge=1, le=10),
    filters: Filters = Depends(get_filters),
):
    df = load_org_tables(org_id)
    active_pods_df = load_active_pods(org_id)

    df_filtered = filter_table(df, **filters)
    active_pods_filtered = filter_table(active_pods_df, **filters)

    insight = build_overperforming_channel_momentum_insight(
        df=df_filtered,
        active_pods_df=active_pods_filtered,
        filters=filters,
        limit=limit,
    )

    return insight


@router.get("/overperforming_channel_momentum/stores")
def get_overperforming_channel_momentum_stores(
    org_id: str,
    filters: Filters = Depends(get_filters),
):
    df = load_org_tables(org_id)
    active_pods_df = load_active_pods(org_id)

    df_filtered = filter_table(df, **filters)
    active_pods_filtered = filter_table(active_pods_df, **filters)

    table = build_overperforming_channel_momentum_table(
        df=df_filtered,
        active_pods_df=active_pods_filtered,
    )

    analyzed = analyze_overperforming_channel_momentum(table)
    channel = analyzed.iloc[0]["channel"]

    store_list = create_overperforming_channel_momentum_store_list(
        df=df_filtered,
        analyzed_table=analyzed,
    )

    config = get_overperforming_channel_momentum_drilldown_config(
        channel=channel
    )

    return {
        **config,
        "rows": clean_for_json(store_list).to_dict("records"),
    }

@router.get("/dropoff_sku_risk")
def get_dropoff_sku_risk(
    org_id: str,
    limit: int = Query(1, ge
    =1, le=10),
    filters: Filters = Depends(get_filters),
):
    df = load_org_tables(org_id)

    df_filtered = filter_table(df, **filters)

    insight = build_dropoff_sku_risk_insight(
        df=df_filtered,
        filters=filters,
        limit=limit,
    )

    return insight


@router.get("/dropoff_sku_risk/stores")
def get_dropoff_sku_risk_stores(
    org_id: str,
    filters: Filters = Depends(get_filters),
):
    df = load_org_tables(org_id)

    df_filtered = filter_table(df, **filters)

    detail_table = build_dropoff_sku_risk_table(df_filtered)
    analyzed = analyze_dropoff_sku_risk(detail_table)

    store_list = create_dropoff_sku_risk_store_list(
        analyzed_table=analyzed,
        detail_table=detail_table,
    )

    sku = analyzed.iloc[0]["sku"] if not analyzed.empty else ""

    return {
        "title": f"Stores That Dropped {sku}",
        "subtitle": (
            f"Stores that previously purchased {sku} but are still "
            "actively purchasing other products from your brand."
        ),
        "columns": [
            {
                "key": "coded_customer",
                "label": "Store",
            },
            {
                "key": "chain",
                "label": "Chain",
            },
            {
                "key": "dc",
                "label": "DC",
            },
            {
                "key": "state",
                "label": "State",
            },
            {
                "key": "prior_3m_sku_units",
                "label": "Prior 3M Units",
            },
            {
                "key": "recent_3m_brand_units",
                "label": "Recent Brand Units",
            },
            {
                "key": "recent_brand_skus",
                "label": "Current SKUs",
            },
            {
                "key": "last_month_sku_purchased",
                "label": "Last Purchased",
            },
        ],
        "rows": clean_for_json(store_list).to_dict("records"),
    }

@router.get("/sales_change_driver")
def get_sales_change_driver(
    org_id: str,
    filters: Filters = Depends(get_filters),
):
    df = load_org_tables(org_id)
    active_pods_df = load_active_pods(org_id)

    df_filtered = filter_table(df, **filters)
    active_pods_filtered = filter_table(active_pods_df, **filters)

    insight = build_sales_change_driver_insight(
        df=df_filtered,
        df_full=df,
        active_pods_df=active_pods_filtered,
        filters=filters,
    )

    return insight

@router.get("/struggling_stores")
def struggling_stores(
    org_id: str = Query(...),
    chain: str = Query(...),
    filters: dict = Depends(get_filters),
):
    features_df = load_org_tables(org_id)
    active_pods_df = load_active_pods(org_id)

    df = filter_table(features_df, **filters)
    active_pods_df = filter_table(active_pods_df, **filters)

    table = create_chain_struggling_store_list(
        df=df,
        active_pods_df=active_pods_df,
        chain=chain,
    )

    table = clean_for_json(table)

    return table.to_dict(orient="records")


@router.get("/distribution_opportunity")
def distribution_opportunity(
    org_id: str = Query(...),
    chain: str = Query(...),
    sku: str = Query(...),
    channel: str = Query(...),
    filters: dict = Depends(get_filters),
):
    features_df = load_org_tables(org_id)

    df = filter_table(features_df, **filters)

    table = create_void_opportunity_store_list(
        df=df,
        chain=chain,
        sku=sku,
        channel=channel,
    )

    table = clean_for_json(table)

    return table.to_dict(orient="records")

@router.get("/weekly_digest")
def get_weekly_digest(org_id: str, filters: Filters = Depends(get_filters)):
    df_full = load_org_tables(org_id)
    active_pods_full = load_active_pods(org_id)

    df = filter_table(df_full, **filters)
    active_pods_df = filter_table(active_pods_full, **filters)

    digest = build_weekly_digest(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_df,
        active_pods_full=active_pods_full,
        filters=filters,
    )

    return digest
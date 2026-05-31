from fastapi import APIRouter, Depends, Query
from backend.filters.filters import get_filters, Filters
from backend.filters.filter_table import filter_table
from backend.data_pipeline.table_loader import load_org_tables
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
from backend.insights.sales_change_driver import (
    build_sales_change_driver_insight,
    build_sales_change_driver_table,
    analyze_sales_change_driver,
    normalize_sales_change_driver_data
)

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

    result = clean_for_json(create_order_cadence_risk_store_list(analyzed)).to_dict("records")

    return result

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

    df_filtered = filter_table(df, **filters)

    insight = build_growing_region_momentum_insight(
        df=df_filtered,
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

    df_filtered = filter_table(df, **filters)

    table = build_growing_region_momentum_table(df_filtered)
    analyzed = analyze_growing_region_momentum(table)

    result = clean_for_json(
        create_growing_region_momentum_store_list(
            df=df_filtered,
            analyzed_table=analyzed,
        )
    ).to_dict("records")

    return result

@router.get("/growing_region_momentum")
def get_growing_region_momentum(
    org_id: str,
    limit: int = Query(1, ge=1, le=10),
    filters: Filters = Depends(get_filters),
):
    df = load_org_tables(org_id)

    df_filtered = filter_table(df, **filters)

    insight = build_growing_region_momentum_insight(
        df=df_filtered,
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

    df_filtered = filter_table(df, **filters)

    table = build_growing_region_momentum_table(df_filtered)
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

    df_filtered = filter_table(df, **filters)

    insight = build_overperforming_channel_momentum_insight(
        df=df_filtered,
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

    df_filtered = filter_table(df, **filters)

    table = build_overperforming_channel_momentum_table(df_filtered)

    analyzed = analyze_overperforming_channel_momentum(table)
    channel = analyzed.iloc[0]["channel"]

    store_list = create_overperforming_channel_momentum_store_list(
        df=df_filtered,
        analyzed_table=analyzed,
    )

    config = get_overperforming_channel_momentum_drilldown_config(channel=channel)

    return {
        **config,
        "rows": clean_for_json(store_list).to_dict("records"),
    }

@router.get("/dropoff_sku_risk")
def get_dropoff_sku_risk(
    org_id: str,
    limit: int = Query(1, ge=1, le=10),
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

    result = clean_for_json(
        create_dropoff_sku_risk_store_list(
            analyzed_table=analyzed,
            detail_table=detail_table,
        )
    ).to_dict("records")

    return result

@router.get("/sales_change_driver")
def get_sales_change_driver(
    org_id: str,
    filters: Filters = Depends(get_filters),
):
    df = load_org_tables(org_id)

    df_filtered = filter_table(df, **filters)

    insight = build_sales_change_driver_insight(
        df=df_filtered,
        df_all_time=df,
        filters=filters,
        include_current_month=False,
    )

    return insight
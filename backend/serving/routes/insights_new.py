from fastapi import APIRouter, Depends, Query
from backend.filters.filters import get_filters, Filters
from backend.filters.filter_table import filter_table
from backend.data_pipeline.table_loader import load_org_tables
from backend.serving.api_helpers import clean_for_json
from backend.insights.missed_replenishment_risk import build_order_cadence_risk_insight, build_order_cadence_risk_table, create_order_cadence_risk_store_list, analyze_order_cadence_risk

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
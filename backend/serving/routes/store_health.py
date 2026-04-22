from fastapi import (FastAPI, APIRouter, Depends, Query)
from backend.filters.filter_table import filter_table
from backend.filters.filters import get_filters, generate_filter_api
from backend.data_pipeline.table_loader import load_org_tables
from backend.metrics.monthly_metric_calculators import calculate_monthly_buying_stores, calculate_monthly_reorder_rate
from backend.metrics.metric_tables import store_performance, kpi_monthly_table, status_counts_dict
from backend.metrics.metric_calculators import calculate_units
from backend.metrics.store_health_kpis import buying_kpis, reorder_kpis, count_channels
from backend.serving.api_helpers import clean_for_json, prep_monthly_graph, remove_time_filters, filter_table


router = APIRouter(prefix="/store_health", tags=["Store Health"])

#Filters

@router.get("/filters")
def get_filter_options(
    column_name: str,
    chain: list[str] | None = Query(None),
    distributor: list[str] | None = Query(None),
    dc: list[str] | None = Query(None),
    channel: list[str] | None = Query(None),
    state: list[str] | None = Query(None),
    status: list[str] | None = Query(None)
):

    filters = {
        "chain": chain,
        "distributor": distributor,
        "dc": dc,
        "channel": channel,
        "state": state,
        "status": status
    }
    features_df = load_org_tables("default_org")

    filters.pop(column_name, None)

    df = filter_table(features_df, **filters)

    return generate_filter_api(df, column_name)

#KPIs

@router.get("/kpis")
def kpis(filters: dict = Depends(get_filters)):
    features_df = load_org_tables("default_org")
    df = filter_table(features_df, **filters)

    non_time_filters=remove_time_filters(filters)
    df_all_time = filter_table(features_df, **non_time_filters)

    monthly_table = kpi_monthly_table(df, df_all_time)

    kpis = {
        "buying_kpis": buying_kpis(monthly_table, df),
        "reorder_kpis": reorder_kpis(monthly_table, df_all_time, df),
        "count_channel": count_channels(df)
    }

    return kpis


#BUYERS

@router.get("/buyers")
def buying_stores(filters: dict = Depends(get_filters)):
    features_df = load_org_tables("default_org")
    df = filter_table(features_df, **filters)

    result = calculate_monthly_buying_stores(df)

    result = prep_monthly_graph(result,"buying_stores")
    result = clean_for_json(result)

    return result.to_dict(orient="records")

#REORDERS

# CHANGE THIS TO USE NON_FEATURE DF FIRST AND THEN ADD FEATURES

@router.get("/reorders")
def reorders(filters: dict = Depends(get_filters)):
    features_df = load_org_tables("default_org")
    df = filter_table(features_df, **filters)

    non_time_filters=remove_time_filters(filters)
    df_all_time = filter_table(features_df, **non_time_filters)

    result = calculate_monthly_reorder_rate(df, df_all_time)

    result = prep_monthly_graph(result,"reorder_rate")
    result = clean_for_json(result)

    return result.to_dict(orient="records")

#CHANNELS

@router.get("/channels")
def channels(filters: dict = Depends(get_filters)):
    features_df = load_org_tables("default_org")
    df = filter_table(features_df, **filters)

    result = calculate_units(df, ["channel"]).sort_values("units", ascending=False)

    total_units = calculate_units(df)

    result["value"] = result["units"]/total_units
    result["name"] = result["channel"]
    
    result = result[["name","value"]]

    return result.to_dict(orient="records")

#STATUS TABLE
@router.get("/status")
def status(filters: dict = Depends(get_filters)):
    features_df = load_org_tables("default_org")
    df = filter_table(features_df, **filters)


    return status_counts_dict(df)


#STORE PERFORMANCE TABLE 

@router.get("/store_performance")
def store_performance_table(filters: dict = Depends(get_filters)):
    features_df = load_org_tables("default_org")
    df = filter_table(features_df, **filters)

    non_time_filters=remove_time_filters(filters)
    df_all_time = filter_table(features_df, **non_time_filters)

    result = store_performance(df, df_all_time)

    result = clean_for_json(result)

    return result.to_dict(orient="records")
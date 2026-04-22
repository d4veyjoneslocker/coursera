from fastapi import (FastAPI, APIRouter, Depends, Query)
from backend.filters.filter_table import filter_table
from backend.filters.filters import get_filters, generate_filter_api
from backend.metrics.metric_calculators import calculate_units
from backend.serving.api_helpers import clean_for_json, prep_monthly_graph, remove_time_filters, convert_selected_months, convert_selected_years
from backend.metrics.metric_tables import chain_table, kpi_monthly_table
from backend.metrics.overview_kpis import unit_kpis, buying_kpis, pod_kpis, vpo_kpis, count_channels, avg_skus_per_store
from backend.data_pipeline.table_loader import load_org_tables
from backend.metrics.monthly_metric_calculators import (
    calculate_monthly_units,
    calculate_monthly_active_pods,
    calculate_monthly_buying_stores,
    calculate_monthly_vpo
)

router = APIRouter(prefix="/overview", tags=["Overview"])



#@app.get("/date")
#def date():
#    report_date = raw_unfi_df["ReportRunDate"].max()[:10]

#    return report_date

@router.get("/filters")
def get_filter_options(
    column_name: str,
    chain: list[str] | None = Query(None),
    sku: list[str] | None = Query(None),
    distributor: list[str] | None = Query(None),
    dc: list[str] | None = Query(None),
    channel: list[str] | None = Query(None),
    year: list[str] | None = Query(None),
    month_year: list[str] | None = Query(None),
    state: list[str] | None = Query(None),
):
    features_df = load_org_tables("default_org")

    filters = {
        "chain": chain,
        "sku": sku,
        "distributor": distributor,
        "dc": dc,
        "channel": channel,
        "year": year,
        "month_year": month_year,
        "state": state,
    }

    filters.pop(column_name, None)

    df = filter_table(features_df, **filters)

    return generate_filter_api(df, column_name)

@router.get("/kpis")
def kpis(filters: dict = Depends(get_filters)):
    features_df = load_org_tables("default_org")
    df = filter_table(features_df, **filters)

    non_time_filters=remove_time_filters(filters)
    df_all_time = filter_table(features_df, **non_time_filters)

    selected_years = convert_selected_years(filters.get("year"))
    selected_months = convert_selected_months(filters.get("month_year"))

    monthly_table = kpi_monthly_table(df_all_time, df_all_time, selected_years=selected_years, selected_months=selected_months)

    kpis = {
        "unit_kpis": unit_kpis(monthly_table),
        "buying_kpis": buying_kpis(monthly_table, df),
        "pod_kpis": pod_kpis(monthly_table, df_all_time),
        "vpo_kpis": vpo_kpis(monthly_table, df_all_time),
        "avg_skus_per_store": avg_skus_per_store(df),
        "count_channel": count_channels(df)
    }

    return kpis


@router.get("/units")
def units(filters: dict = Depends(get_filters)):
    features_df = load_org_tables("default_org")

    df = filter_table(features_df, **filters)

    result = calculate_monthly_units(df)

    result = prep_monthly_graph(result,"units")
    result = clean_for_json(result)

    return result.to_dict(orient="records")


# Buyers by Month Bar Graph

@router.get("/buyers")
def buying_stores(filters: dict = Depends(get_filters)):
    features_df = load_org_tables("default_org")
    df = filter_table(features_df, **filters)

    result = calculate_monthly_buying_stores(df)

    result = prep_monthly_graph(result,"buying_stores")
    result = clean_for_json(result)

    return result.to_dict(orient="records")


# VPO by Month Bar Graph

@router.get("/velocity")
def velocity(filters: dict = Depends(get_filters)):
    features_df = load_org_tables("default_org")
    df = filter_table(features_df, **filters)

    selected_years = convert_selected_years(filters.get("year"))
    selected_months = convert_selected_months(filters.get("month_year"))

    non_time_filters = remove_time_filters(filters)

    all_time_df = filter_table(features_df, **non_time_filters)
    
    result = calculate_monthly_vpo(df, all_time_df, selected_years=selected_years, selected_months=selected_months)

    result = prep_monthly_graph(result,"vpo")
    result = clean_for_json(result)

    return result.to_dict(orient="records")


@router.get("/pods")
def pods_test(filters: dict = Depends(get_filters)):
    features_df = load_org_tables("default_org")
    df = filter_table(features_df, **filters)

    selected_years = convert_selected_years(filters.get("year"))
    selected_months = convert_selected_months(filters.get("month_year"))

    pod_filters = filters.copy()
    pod_filters.pop("year", None)
    pod_filters.pop("month", None)

    pod_df = filter_table(features_df, **pod_filters)

    result = calculate_monthly_active_pods(df, pod_df, selected_years=selected_years, selected_months=selected_months)

    result = prep_monthly_graph(result,"active_pods")
    result = clean_for_json(result)

    return result.to_dict(orient="records")



# SKU pie chart

@router.get("/skus")
def skus(filters: dict = Depends(get_filters)):
    features_df = load_org_tables("default_org")
    df = filter_table(features_df, **filters)

    result = calculate_units(df, "sku").sort_values("units", ascending=False)

    total_units = calculate_units(df)

    result["value"] = result["units"]/total_units
    result = result.rename(columns={"sku": "name"})
    
    result = result[["name", "value"]]

    return result.to_dict(orient="records")

# KPI Cards

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

@router.get("/chain_table")
def chain_table_api(filters: dict = Depends(get_filters)):
    features_df = load_org_tables("default_org")
    df = filter_table(features_df, **filters)

    result = chain_table(df)

    result = clean_for_json(result)

    return result.to_dict(orient="records")
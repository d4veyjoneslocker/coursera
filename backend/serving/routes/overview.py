from fastapi import (FastAPI, APIRouter, Depends)
from backend.filters.filter_table import filter_table
from backend.filters.filters import get_filters
from backend.tables import (combined_df, combined_w_features)
from backend.metrics.metric_calculators import calculate_units
from backend.serving.json_cleaner import clean_for_json
from backend.metrics.metric_tables import chain_table, kpi_monthly_table
from backend.metrics.overview_kpis import unit_kpis, buying_kpis, pod_kpis, vpo_kpis, count_channels, avg_skus_per_store
from backend.metrics.monthly_metric_calculators import (
    calculate_monthly_units,
    calculate_monthly_active_pods,
    calculate_monthly_buying_stores,
    calculate_monthly_vpo
)

router = APIRouter(prefix="/overview", tags=["Overview"])

def prep_monthly_graph(df, metric):
    df = df[["month_year", metric]]
    df = df.rename(columns={metric: "value"})

    return df

def remove_time_filters(filters):
    non_time_filters = filters.copy()
    non_time_filters.pop("year", None)
    non_time_filters.pop("month_year", None)

    return non_time_filters


#@app.get("/date")
#def date():
#    report_date = raw_unfi_df["ReportRunDate"].max()[:10]

#    return report_date


@router.get("/kpis")
def kpis(filters: dict = Depends(get_filters)):
    df = filter_table(combined_w_features, **filters)

    non_time_filters=remove_time_filters(filters)
    df_all_time = filter_table(combined_w_features, **non_time_filters)

    monthly_table = kpi_monthly_table(df, df_all_time)

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

    df = filter_table(combined_w_features, **filters)

    result = calculate_monthly_units(df)

    result = prep_monthly_graph(result,"units")
    result = clean_for_json(result)

    return result.to_dict(orient="records")


# Buyers by Month Bar Graph

@router.get("/buyers")
def buying_stores(filters: dict = Depends(get_filters)):
    df = filter_table(combined_w_features, **filters)

    result = calculate_monthly_buying_stores(df)

    result = prep_monthly_graph(result,"buying_stores")
    result = clean_for_json(result)

    return result.to_dict(orient="records")


# VPO by Month Bar Graph

@router.get("/velocity")
def velocity(filters: dict = Depends(get_filters)):

    df = filter_table(combined_w_features, **filters)

    non_time_filters = remove_time_filters(filters)

    all_time_df = filter_table(combined_w_features, **non_time_filters)
    
    result = calculate_monthly_vpo(df, all_time_df)

    result = prep_monthly_graph(result,"vpo")
    result = clean_for_json(result)

    return result.to_dict(orient="records")


@router.get("/pods")
def pods_test(filters: dict = Depends(get_filters)):

    df = filter_table(combined_w_features, **filters)

    pod_filters = filters.copy()
    pod_filters.pop("year", None)
    pod_filters.pop("month", None)

    pod_df = filter_table(combined_w_features, **pod_filters)

    result = calculate_monthly_active_pods(df, pod_df)

    result = prep_monthly_graph(result,"active_pods")
    result = clean_for_json(result)

    return result.to_dict(orient="records")



# SKU pie chart

@router.get("/skus")
def skus(filters: dict = Depends(get_filters)):

    df = filter_table(combined_w_features, **filters)

    result = calculate_units(df, "sku").sort_values("units", ascending=False)

    total_units = calculate_units(df)

    result["value"] = result["units"]/total_units
    result = result.rename(columns={"sku": "name"})
    
    result = result[["name", "value"]]

    return result.to_dict(orient="records")

# KPI Cards

@router.get("/channels")
def channels(filters: dict = Depends(get_filters)):
    df = filter_table(combined_w_features, **filters)

    result = calculate_units(df, ["channel"]).sort_values("units", ascending=False)

    total_units = calculate_units(df)

    result["value"] = result["units"]/total_units
    result["name"] = result["channel"]
    
    result = result[["name","value"]]

    return result.to_dict(orient="records")

@router.get("/chain_table")
def chain_table_api(filters: dict = Depends(get_filters)):

    df = filter_table(combined_w_features, **filters)

    result = chain_table(df)

    result = clean_for_json(result)

    return result.to_dict(orient="records")
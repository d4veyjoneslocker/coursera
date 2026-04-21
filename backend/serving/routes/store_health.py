from fastapi import (FastAPI, APIRouter, Depends)
from backend.filters.filter_table import filter_table
from backend.filters.filters import get_filters
from backend.tables import (combined_df, combined_w_features)
from backend.metrics.monthly_metric_calculators import calculate_monthly_buying_stores, calculate_monthly_reorder_rate
from backend.metrics.metric_tables import store_performance, kpi_monthly_table
from backend.metrics.metric_calculators import calculate_units
from backend.metrics.store_health_kpis import buying_kpis, reorder_kpis, count_channels
from backend.serving.json_cleaner import clean_for_json


router = APIRouter(prefix="/store_health", tags=["Store Health"])


def prep_monthly_graph(df, metric):
    df = df[["month_year", metric]]
    df = df.rename(columns={metric: "value"})

    return df

def remove_time_filters(filters):
    non_time_filters = filters.copy()
    non_time_filters.pop("year", None)
    non_time_filters.pop("month_year", None)

    return non_time_filters

#KPIs

@router.get("/kpis")
def kpis(filters: dict = Depends(get_filters)):
    df = filter_table(combined_w_features, **filters)

    non_time_filters=remove_time_filters(filters)
    df_all_time = filter_table(combined_w_features, **non_time_filters)

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
    df = filter_table(combined_w_features, **filters)

    result = calculate_monthly_buying_stores(df)

    result = prep_monthly_graph(result,"buying_stores")
    result = clean_for_json(result)

    return result.to_dict(orient="records")

#REORDERS

@router.get("/reorders")
def reorders(filters: dict = Depends(get_filters)):

    df = filter_table(combined_w_features, **filters)

    non_time_cols = remove_time_filters(filters)
    df_all_time = filter_table(combined_w_features, **non_time_cols)

    result = calculate_monthly_reorder_rate(df, df_all_time)

    result = prep_monthly_graph(result,"reorder_rate")
    result = clean_for_json(result)

    return result.to_dict(orient="records")

#CHANNELS

@router.get("/channels")
def channels(filters: dict = Depends(get_filters)):
    df = filter_table(combined_w_features, **filters)

    result = calculate_units(df, ["channel"]).sort_values("units", ascending=False)

    total_units = calculate_units(df)

    result["value"] = result["units"]/total_units
    result["name"] = result["channel"]
    
    result = result[["name","value"]]

    return result.to_dict(orient="records")

#STATUS TABLE
@router.get("/status")
def status(filters: dict = Depends(get_filters)):
    df = filter_table(combined_w_features, **filters)

    result = calculate_units(df, ["status"]).sort_values("units", ascending=False)

    total_units = calculate_units(df)

    result["value"] = result["units"]/total_units
    result["name"] = result["status"]
    
    result = result[["name","value"]]

    return result.to_dict(orient="records")


#STORE PERFORMANCE TABLE 

@router.get("/store_performance")
def store_performance_table(filters: dict = Depends(get_filters)):

    df = filter_table(combined_w_features, **filters)

    non_time_cols = remove_time_filters(filters)
    df_all_time = filter_table(combined_w_features, **non_time_cols)

    result = store_performance(df, df_all_time)

    result = clean_for_json(result)

    return result.to_dict(orient="records")
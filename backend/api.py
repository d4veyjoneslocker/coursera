
from fastapi import FastAPI
import numpy as np
import pandas as pd
import json
from serving.filter_table import filter_table
from fastapi.middleware.cors import CORSMiddleware
from filters.filters import monthly_filter
from filters.filters import Filters
from fastapi import Depends
from tables import combined_df
from tables import combined_w_features
from metrics.metrics import calculate_monthly_active_pods
from metrics.metrics import calculate_vpo
from fastapi import Query
from metrics.core_metrics import chain_table
from metrics.store_level_metrics import calculate_store_health_status
from metrics.store_level_metrics import calculate_reorder_stats
from metrics.store_level_metrics import calculate_store_vpo
from metrics.core_metrics import monthly_summary
from metrics.kpis import kpi_data
from metrics.growth_metrics import add_time_metrics_simple
from metrics.kpis import calculate_avg_skus_per_store
from metrics.kpis import count_channels


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",
                   "https://crisp-dashboard.vercel.app/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



def generate_filter_api(df, filter_name):
    column_name = filter_name

    if column_name not in df.columns:
        return []

    return (
        df[column_name]
        .dropna()
        .astype(str)
        .sort_values()
        .unique()
        .tolist()
    )

def get_filters(
    chain: list[str] | None = Query(None),
    channel: list[str] | None = Query(None),
    year: list[str] | None = Query(None),
    dc: list[str] | None = Query(None),
    distributor: list[str] | None = Query(None),
    month: list[str] | None = Query(None),
    state: list[str] | None = Query(None),
    sku: list[str] | None = Query(None),
):
    return {
        "chain": chain,
        "channel": channel,
        "year": year,
        "dc": dc,
        "distributor": distributor,
        "month": month,
        "state": state,
        "sku": sku,
    }

def get_non_time_filters(
    chain: list[str] | None = Query(None),
    channel: list[str] | None = Query(None),
    dc: list[str] | None = Query(None),
    distributor: list[str] | None = Query(None),
    state: list[str] | None = Query(None),
    sku: list[str] | None = Query(None),
):
    return {
        "chain": chain,
        "channel": channel,
        "dc": dc,
        "distributor": distributor,
        "state": state,
        "sku": sku,
    }

# I NEED TO CLEAN UP THE WHOLE FILTERING THING IN THE DEF UNITS SHIT -- LITERALLY JUST CLEAN UP THO, IT WORKS

def metric_by_month(df, metric):
    df = df.reset_index()

    df = df[["month_year", metric]].copy()

    df = (
        df.groupby("month_year", as_index=False)[metric]
        .sum()
        .rename(columns={metric: "value"})
        .sort_values("month_year")
    )

    df["month_year"] = df["month_year"].astype(str)
    return df.to_dict(orient="records")


# Units by Month Bar Graph

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/units")
def units(filters: dict = Depends(get_filters)):
    df = filter_table(combined_df, **filters)

    result = (
        df.groupby("month_year", as_index=False)
        .agg(value=("units", "sum"))
        .sort_values("month_year")
    )

    result["month_year"] = result["month_year"].astype(str)

    return result.to_dict(orient="records")



# Buyers by Month Bar Graph

@app.get("/buyers")
def buying_stores(filters: dict = Depends(get_filters)):
    df = filter_table(combined_df, **filters)

    result = (
        df.groupby("month_year", as_index=False)
        .agg(value=("coded_customer", "nunique"))
        .sort_values("month_year")
    )

    result["month_year"] = result["month_year"].astype(str)

    return result.to_dict(orient="records")


# VPO by Month Bar Graph

@app.get("/velocity")
def velocity(filters: dict = Depends(get_filters)):

    df = filter_table(combined_w_features, **filters)

    units_by_month = (
        df.groupby("month_year", as_index=False)
        .agg(units=("units", "sum"))
        .sort_values("month_year")
    )

    units_by_month["month_year"] = units_by_month["month_year"].astype(str)

    pod_filters = filters.copy()
    pod_filters.pop("year", None)
    pod_filters.pop("month", None)

    pod_df = filter_table(combined_w_features, **pod_filters)
    active_pods_by_month = calculate_monthly_active_pods(pod_df)

    active_pods_by_month["month_year"] = active_pods_by_month["month_year"].astype(str)

    active_pods_by_month = active_pods_by_month.rename(columns={"value": "active_pods"})

    result = units_by_month.merge(
        active_pods_by_month[["month_year", "active_pods"]],
        on="month_year",
        how="left"
    )

    result["value"] = result["units"]/result["active_pods"]/4
                             
    result = result[["month_year","value"]]

    return result.to_dict(orient="records")



# PODs by Month Bar Graph

@app.get("/pods")
def pods(filters: dict = Depends(get_filters)):

    df = filter_table(combined_w_features, **filters)

    visible_months = (
        df[["month_year"]]
        .drop_duplicates()
        .sort_values("month_year")
    )

    visible_months["month_year"] = visible_months["month_year"].astype(str)

    pod_filters = filters.copy()
    pod_filters.pop("year", None)
    pod_filters.pop("month", None)

    pod_df = filter_table(combined_w_features, **pod_filters)
    active_pods_by_month = calculate_monthly_active_pods(pod_df)

    active_pods_by_month["month_year"] = active_pods_by_month["month_year"].astype(str)

    result = visible_months.merge(
        active_pods_by_month[["month_year", "value"]],
        on="month_year",
        how="left"
    )
 
    result = result[["month_year","value"]]


    return result.to_dict(orient="records")

# SKU pie chart

@app.get("/skus")
def skus(filters: dict = Depends(get_filters)):
    df = filter_table(combined_df, **filters)

    result = (
        df.groupby("sku", as_index=False)
        .agg(units=("units", "sum"))
        .sort_values("units", ascending=False)
    )

    total_units = result["units"].sum()

    result["value"] = result["units"]/total_units
    result["name"] = result["sku"]
    
    result = result[["name","value"]]

    return result.to_dict(orient="records")

# KPI Cards

@app.get("/kpis")
def kpis(filters: dict = Depends(get_filters)):
    df = filter_table(combined_w_features, **filters)

    no_time_filters = filters.copy()
    no_time_filters.pop("year", None)
    no_time_filters.pop("month", None)

    df_clone = filter_table(combined_df, **no_time_filters)

    result = monthly_summary(df, df_clone)

    result = add_time_metrics_simple(result,["units"], ["buying_stores"], ["vpo"], ["active_pods","new_pods"])

    return {
        **kpi_data(result),
        **calculate_avg_skus_per_store(df),
        **count_channels(df)
    }


# Channel pie chart

@app.get("/channels")
def channels(filters: dict = Depends(get_filters)):
    df = filter_table(combined_df, **filters)

    result = (
        df.groupby("channel", as_index=False)
        .agg(units=("units", "sum"))
        .sort_values("units", ascending=False)
    )

    total_units = result["units"].sum()

    result["value"] = result["units"]/total_units
    result["name"] = result["channel"]
    
    result = result[["name","value"]]

    return result.to_dict(orient="records")

@app.get("/chain_table")
def chain_table_api(filters: dict = Depends(get_filters)):
    df = filter_table(combined_df, **filters)

    no_time_filters = filters.copy()
    no_time_filters.pop("year", None)
    no_time_filters.pop("month", None)

    df_clone = filter_table(combined_df, **no_time_filters)

    result = chain_table(df, df_clone)

    result = result.replace([np.inf, -np.inf], np.nan)
    result = result.astype(object).where(pd.notnull(result), None)
    result = result.sort_values("units", ascending=False)

    return result.to_dict(orient="records")


@app.get("/store_status")
def store_status(filters: dict = Depends(get_non_time_filters)):
    df = filter_table(combined_w_features, **filters)

    result = calculate_store_health_status(df)
    
    result = result.groupby(
        ["coded_customer",
        "first_month_purchased",
        "second_to_last_month_purchased",
        "last_month_purchased",
        "status"], dropna=False
        ).agg(
            units = ("units", "sum"),
            revenue = ("revenue", "sum")
        ).reset_index().sort_values("units", ascending=False)

    result["first_month_purchased"] = result["first_month_purchased"].astype(str)
    result["second_to_last_month_purchased"] = result["second_to_last_month_purchased"].astype(str)
    result["last_month_purchased"] = result["last_month_purchased"].astype(str)

    result = result.replace({np.nan: None}) 

    print (len(result))

    return result.to_dict(orient="records")

@app.get("/store_level_reorder")
def store_level_reorder(filters: dict = Depends(get_non_time_filters)):
    df = filter_table(combined_w_features, **filters)
    
    result = calculate_reorder_stats(df)
    vpo_result = calculate_store_vpo(df)
    health_result = calculate_store_health_status(df)

    result = result.merge(
        vpo_result[["coded_customer", "vpo", "active_pods", "volume"]],
        on="coded_customer",
        how="left"
    )

    result = result.merge(
        health_result[["coded_customer","first_month_purchased",
        "second_to_last_month_purchased",
        "last_month_purchased",
        "status"]],
        on="coded_customer",
        how="left"
    )

    result = result.astype(object).where(pd.notna(result), None)
    
    result["first_month_purchased"] = result["first_month_purchased"].astype(str)
    result["second_to_last_month_purchased"] = result["second_to_last_month_purchased"].astype(str)
    result["last_month_purchased"] = result["last_month_purchased"].astype(str)

    records = result.to_dict(orient="records")

    for row in records:
        for key, value in row.items():
            if pd.isna(value):
                row[key] = None

    return records

@app.get("/reorder_stats")
def reorder_stats(filters: dict = Depends(get_non_time_filters)):
    df = filter_table(combined_w_features, **filters)
    
    result = calculate_reorder_stats(df)
    vpo_result = calculate_store_vpo(df)
    health_result = calculate_store_health_status(df)

    result = result.merge(
        vpo_result[["coded_customer", "vpo", "active_pods", "volume"]],
        on="coded_customer",
        how="left"
    )

    result = result.merge(
        health_result[["coded_customer","first_month_purchased",
        "second_to_last_month_purchased",
        "last_month_purchased",
        "status"]],
        on="coded_customer",
        how="left"
    )

    healthy_count = (result["status"] == "Healthy").sum()
    struggling_count = (result["status"] == "Struggling").sum()
    revived_count = (result["status"] == "Revived").sum()
    inactive_count = (result["status"] == "Inactive").sum()
    new_count = (result["status"] == "New").sum()

    return {
    "Healthy": int(healthy_count),
    "Struggling": int(struggling_count),
    "Revived": int(revived_count),
    "Inactive": int(inactive_count),
    "New": int(new_count)
    }


    



# filter endpoints

@app.get("/filters/{column_name}")
def get_filter_options(
    column_name: str,
    chain: list[str] | None = Query(None),
    region: list[str] | None = Query(None),
    brand: list[str] | None = Query(None),
    flavor: list[str] | None = Query(None),
    pack_size: list[str] | None = Query(None),
    segment: list[str] | None = Query(None),
    sku: list[str] | None = Query(None),
    month_year: list[str] | None = Query(None),
):

    filters = {
        "chain": chain,
        "region": region,
        "brand": brand,
        "flavor": flavor,
        "pack_size": pack_size,
        "segment": segment,
        "sku": sku,
        "month_year": month_year,
    }

    filters.pop(column_name, None)

    df = filter_table(combined_w_features, **filters)

    return generate_filter_api(df, column_name)

import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port)
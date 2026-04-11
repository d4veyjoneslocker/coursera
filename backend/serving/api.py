
from fastapi import (FastAPI, Depends, Query)
from fastapi.responses import StreamingResponse
from io import BytesIO
import numpy as np
import pandas as pd
import json
from filters.filter_table import filter_table
from filters.filters import (generate_filter_api, get_filters, get_non_time_filters, Filters) 
from fastapi.middleware.cors import CORSMiddleware
from tables import (combined_df, combined_w_features)
from metrics.core_metrics import (monthly_summary, chain_table, active_store_rate)
from metrics.store_level_metrics import (
    calculate_store_health_status,
    calculate_reorder_stats,
    calculate_reorder_stats_monthly,
    calculate_store_vpo,
    )
from metrics.kpis import (kpi_data, store_health_kpis, count_channels, calculate_avg_skus_per_store, buying_kpis)
from metrics.growth_metrics import add_time_metrics_simple
from serving.json_cleaner import clean_for_json


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",
                   "https://crisp-dashboard.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def prep_monthly_graph(df, metric):
    df = df[["month_year", metric]]
    df = df.rename(columns={metric: "value"})

    return df



@app.get("/units")
def units(filters: dict = Depends(get_filters)):

    df = filter_table(combined_w_features, **filters)

    result = monthly_summary(df, df)

    result = prep_monthly_graph(result,"units")
    result = clean_for_json(result)

    return result.to_dict(orient="records")


# Buyers by Month Bar Graph

@app.get("/buyers")
def buying_stores(filters: dict = Depends(get_filters)):
    df = filter_table(combined_w_features, **filters)

    result = monthly_summary(df, df)

    result = prep_monthly_graph(result,"buying_stores")
    result = clean_for_json(result)

    return result.to_dict(orient="records")


# VPO by Month Bar Graph

@app.get("/velocity")
def velocity(filters: dict = Depends(get_filters)):

    df = filter_table(combined_w_features, **filters)

    pod_filters = filters.copy()
    pod_filters.pop("year", None)
    pod_filters.pop("month", None)

    pod_df = filter_table(combined_w_features, **pod_filters)
    
    result = monthly_summary(df, pod_df)

    result = prep_monthly_graph(result,"vpo")
    result = clean_for_json(result)

    return result.to_dict(orient="records")


@app.get("/pods")
def pods_test(filters: dict = Depends(get_filters)):

    df = filter_table(combined_w_features, **filters)

    pod_filters = filters.copy()
    pod_filters.pop("year", None)
    pod_filters.pop("month", None)

    pod_df = filter_table(combined_w_features, **pod_filters)

    result = monthly_summary(df, pod_df)

    result = prep_monthly_graph(result,"active_pods")
    result = clean_for_json(result)

    return result.to_dict(orient="records")



# SKU pie chart

@app.get("/skus")
def skus(filters: dict = Depends(get_filters)):

    df = filter_table(combined_w_features, **filters)

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

    df_clone = filter_table(combined_w_features, **no_time_filters)

    result = monthly_summary(df, df_clone)

    result = add_time_metrics_simple(result,["units", "new_pods"], ["buying_stores"], ["vpo"], ["active_pods"])

    return {
        **kpi_data(result),
        **calculate_avg_skus_per_store(df),
        **count_channels(df)
    }

@app.get("/kpis_store_health")
def kpis(filters: dict = Depends(get_filters)):
    df = filter_table(combined_w_features, **filters)

    no_time_filters = filters.copy()
    no_time_filters.pop("year", None)
    no_time_filters.pop("month", None)

    df_clone = filter_table(combined_w_features, **no_time_filters)

    result_buyers = monthly_summary(df, df_clone)
    result_buyers = add_time_metrics_simple(result_buyers, buyer_metrics=["buying_stores"])

    result_reorder = active_store_rate(df)
    result_reorder = add_time_metrics_simple(result_reorder, reorder_metrics=["reorder_rate"])

    return {
        **buying_kpis(result_buyers),
        **store_health_kpis(result_reorder),
        **count_channels(df)
    }


# Channel pie chart

@app.get("/channels")
def channels(filters: dict = Depends(get_filters)):
    df = filter_table(combined_w_features, **filters)

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
    df = filter_table(combined_w_features, **filters)

    no_time_filters = filters.copy()
    no_time_filters.pop("year", None)
    no_time_filters.pop("month", None)

    df_clone = filter_table(combined_w_features, **no_time_filters)

    result = chain_table(df, df_clone)

    result = result.sort_values("units", ascending=False)

    result = clean_for_json(result)

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

    result = clean_for_json(result)

    return result.to_dict(orient="records")

@app.get("/store_level_reorder")
def store_level_reorder(filters: dict = Depends(get_non_time_filters)):

    df = filter_table(combined_w_features, **filters)

    result = calculate_reorder_stats(df)
    vpo_result = calculate_store_vpo(df)

    result = result.merge(
        vpo_result[["coded_customer", "vpo", "active_pods", "volume"]],
        on="coded_customer",
        how="left"
    )
    
    result = clean_for_json(result)

    return result.to_dict(orient="records")


@app.get("/reorder_stats")
def reorder_stats(filters: dict = Depends(get_non_time_filters)):
    df = filter_table(combined_w_features, **filters)
    
    result = calculate_reorder_stats(df)

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

@app.get("/reorder_graph")
def reorder_graph(filters: dict = Depends(get_non_time_filters)):
    df = filter_table(combined_w_features, **filters)

    result = calculate_reorder_stats_monthly(df)

    result = result.sort_values("month_year")
    result = result.iloc[1:]

    result = result.rename(columns={"reorder_rate": "value"})

    result = clean_for_json(result)
    
    return result.to_dict(orient="records")

@app.get("/active_stores")
def active_stores(filters: dict = Depends(get_non_time_filters)):
    df = filter_table(combined_w_features, **filters)
    result = active_store_rate(df)

    result = add_time_metrics_simple(result, reorder_metrics=["reorder_rate"])

    result = clean_for_json(result)
    
    return result.to_dict(orient="records")



@app.get("/store_list")
def store_list():

    df = combined_df

    result = df.groupby(["coded_customer"]).agg({
        "chain": "first",
        "store_number": "first",
        "street_address": "first",
        "city": "first",
        "state": "first",
        "zip": "first"
    }).reset_index()

    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        result.to_excel(writer, index=False, sheet_name="Store List")

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=store_list.xlsx"}
    )
   



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
    status: list[str] | None = Query(None)
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
        "status": status
    }

    filters.pop(column_name, None)

    df = filter_table(combined_w_features, **filters)

    return generate_filter_api(df, column_name)

import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port)
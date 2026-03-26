
from fastapi import FastAPI
import pandas as pd
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


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

monthly_summary = pd.read_parquet("monthly_summary.parquet")

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

@app.get("/units")
def units(
    chain: list[str] | None = Query(None),
    channel: list[str] | None = Query(None),
    year: list[str] | None = Query(None),
):

    df = filter_table(
        monthly_summary,
        chain=chain,
        channel=channel,
        year=year,
    )

    print("rows after filter:", len(df))

    return metric_by_month(df, "units")


# Buyers by Month Bar Graph

@app.get("/buyers")
def buying_stores(
    chain: list[str] | None = Query(None),
    channel: list[str] | None = Query(None),
    year: list[str] | None = Query(None),
):
    df = filter_table(
        combined_df,
        chain=chain,
        channel=channel,
        year=year,)

    result = (
        df.groupby("month_year", as_index=False)
        .agg(value=("coded_customer", "nunique"))
        .sort_values("month_year")
    )

    result["month_year"] = result["month_year"].astype(str)

    return result.to_dict(orient="records")


# VPO by Month Bar Graph

@app.get("/velocity")
def velocity(
    chain: list[str] | None = Query(None),
    channel: list[str] | None = Query(None),
    year: list[str] | None = Query(None),
):

    df = filter_table(combined_w_features,
        chain=chain,
        channel=channel,
        year=year,)

    units_by_month = (
        df.groupby("month_year", as_index=False)
        .agg(units=("units", "sum"))
        .sort_values("month_year")
    )

    units_by_month["month_year"] = units_by_month["month_year"].astype(str)

    pod_filters = {
    "chain": chain,
    "channel": channel
    }

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
def pods(
    chain: list[str] | None = Query(None),
    channel: list[str] | None = Query(None),
    year: list[str] | None = Query(None)
):

    df = filter_table(combined_w_features,
        chain=chain,
        channel=channel,
        year=year,)

    visible_months = (
        df[["month_year"]]
        .drop_duplicates()
        .sort_values("month_year")
    )

    visible_months["month_year"] = visible_months["month_year"].astype(str)

    pod_filters = {
    "chain": chain,
    "channel": channel
    }

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

# filter endpoints

@app.get("/filters/chains")
def get_chains():
    chains = (
        combined_w_features["chain"]
        #.dropna()
        .astype(str)
        .sort_values()
        .unique()
        .tolist()
    )

    return chains

@app.get("/filters/channels")
def get_channels():
    channels = (
        combined_w_features["channel"]
        #.dropna()
        .fillna("NO CHANNEL ASSIGNED")
        .astype(str)
        .sort_values()
        .unique()
        .tolist()
    )

    return channels

@app.get("/filters/years")
def get_years():
    years = (
        combined_w_features["year"]
        #.dropna()
        .astype(str)
        .sort_values()
        .unique()
        .tolist()
    )

    return years
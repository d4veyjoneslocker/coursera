from pydantic import BaseModel
from fastapi import Query

monthly_filter = [
    "chain",
    "state",
    "channel",
    "sku",
    "distributor",
    "dc",
    "year",
    "month",
    "status"
]

non_time_filter = [
    "chain",
    "state",
    "channel",
    "sku",
    "distributor",
    "dc",
    "status"
]


class Filters(BaseModel):
    chain: list[str] | None = None
    state: list[str] | None = None
    channel: list[str] | None = None
    sku: list[str] | None = None
    distributor: list[str] | None = None
    dc: list[str] | None = None
    year: list[str] | None = None
    month: list[str] | None = None
    status: list[str] | None = None

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
    status: list[str] | None = Query(None)
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
        "status": status
    }

def get_non_time_filters(
    chain: list[str] | None = Query(None),
    channel: list[str] | None = Query(None),
    dc: list[str] | None = Query(None),
    distributor: list[str] | None = Query(None),
    state: list[str] | None = Query(None),
    sku: list[str] | None = Query(None),
    status: list[str] | None = Query(None)
):
    return {
        "chain": chain,
        "channel": channel,
        "dc": dc,
        "distributor": distributor,
        "state": state,
        "sku": sku,
        "status": status
    }
from pydantic import BaseModel

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
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
]

class Filters(BaseModel):
    chain: str | None = None
    state: str | None = None
    channel: str | None = None
    sku: str | None = None
    distributor: str | None = None
    dc: str | None = None
    year: int | None = None
    month: int | None = None
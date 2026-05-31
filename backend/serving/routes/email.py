import os
import pandas as pd
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Depends
from backend.deep_dive.digest_builder import build_weekly_digest
from backend.data_pipeline.table_loader import load_org_tables
from backend.filters.filters import get_filters
from backend.deep_dive.deep_dive_kpis import build_deep_dive_kpis
from backend.serving.api_helpers import clean_for_json
from backend.metrics.metric_calculators import calculate_vpo

router = APIRouter(prefix="/email", tags=["Email"])


@router.get("/weekly-digest")
def get_weekly_digest(
    org_id: str = Query(...),
    filters: dict = Depends(get_filters),
):
    features_df = load_org_tables(org_id)

    digest = build_weekly_digest(features_df)

    return digest

@router.get("/deep-dive-snapshot")
def get_deep_dive_snapshot(
    org_id: str = Query(...),
    filters: dict = Depends(get_filters),
):
    features_df = load_org_tables(org_id)

    if features_df is None or features_df.empty:
        raise HTTPException(status_code=404, detail="No data found")

    snapshot = build_deep_dive_kpis(features_df)

    return snapshot

@router.get("/sku_rankings")
def get_sku_rankings(
    org_id: str,
    ):
    df = load_org_tables(org_id)

    last_full_month = df["month_year"].max()
    current = df[df["month_year"] == last_full_month].copy()

    table = (
    current.groupby("sku", as_index=False)
        .agg(
            units=("units", "sum"),
            active_stores=("coded_customer", "nunique"),
        )
    )

    total_units = table["units"].sum()

    table["unit_share"] = (
        table["units"] / total_units
    )

    table["vpo"] = (table["units"] / (table["active_stores"] / 4)) / 5 

    table = table.sort_values(
        "units",
        ascending=False,
    )

    table["rank"] = range(1, len(table) + 1)

    return {
        "title": "SKU Rankings",
        "subtitle": f"SKU performance ranked by units in {last_full_month}.",
        "columns": [
            {"key": "rank", "label": "Rank", "align": "right", "format": "number", "width": "80px"},
            {"key": "sku", "label": "SKU", "align": "left", "width": "100px"},
            {"key": "units", "label": "Units", "align": "right", "format": "number", "width": "160px"},
            {"key": "active_stores", "label": "Active Stores", "align": "right", "format": "number", "width": "170px"},
            {"key": "vpo", "label": "VPO", "align": "right", "format": "decimal", "width": "120px"},
            {"key": "unit_share", "label": "Unit Share", "align": "right", "format": "percent", "width": "140px"},
        ],
        "table_width": "max-w-4xl",
        "rows": clean_for_json(table).to_dict("records"),
    }
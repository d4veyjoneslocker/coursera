import os
import pandas as pd
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Depends
from backend.deep_dive.digest_builder import build_weekly_digest
from backend.data_pipeline.table_loader import load_org_tables, load_active_pods
from backend.filters.filters import get_filters
from backend.serving.api_helpers import clean_for_json
from backend.metrics.metric_callers import calculate_metric

router = APIRouter(prefix="/email", tags=["Email"])


@router.get("/weekly-digest")
def get_weekly_digest(
    org_id: str = Query(...),
    filters: dict = Depends(get_filters),
):
    features_df = load_org_tables(org_id)
    active_pods_df = load_active_pods(org_id)

    digest = build_weekly_digest(
        features_df,
        active_pods_df,
    )

    return digest


@router.get("/sku_rankings")
def get_sku_rankings(
    org_id: str,
):
    df = load_org_tables(org_id)
    active_pods_df = load_active_pods(org_id)

    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    active_pods_df["month_year"] = pd.PeriodIndex(
        active_pods_df["month_year"],
        freq="M",
    )

    current_month = pd.Timestamp.today().to_period("M")
    df = df[df["month_year"] != current_month].copy()

    last_full_month = df["month_year"].max()

    current = df[
        df["month_year"] == last_full_month
    ].copy()

    current_active_pods = active_pods_df[
        active_pods_df["month_year"] == last_full_month
    ].copy()

    table = (
        current.groupby("sku", as_index=False)
        .agg(
            units=("units", "sum"),
            active_stores=("coded_customer", "nunique"),
        )
    )

    velocity = calculate_metric(
        metric_name="velocity",
        df_filtered=current,
        active_pods_df=current_active_pods,
        group_cols=["sku"],
    ).rename(columns={"value": "vpo"})

    table = table.merge(
        velocity,
        on="sku",
        how="left",
    )

    total_units = table["units"].sum()

    table["unit_share"] = (
        table["units"] / total_units
    )

    table = table.sort_values(
        "units",
        ascending=False,
    )

    table["rank"] = range(1, len(table) + 1)

    return {
        "title": f"SKU Rankings - {last_full_month}",
        "subtitle": f"SKU performance ranked by units sold in {last_full_month}.",
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


@router.get("/new_store_distribution/stores")
def get_new_store_distribution_stores(
    org_id: str,
    sku: str,
):
    df = load_org_tables(org_id).copy()
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")

    current_month = pd.Timestamp.today().to_period("M")
    df = df[df["month_year"] != current_month].copy()

    last_full_month = df["month_year"].max()

    current = df[
        (df["month_year"] == last_full_month)
        & (df["sku"] == sku)
        & (df["units"] > 0)
    ].copy()

    historical = df[
        (df["month_year"] < last_full_month)
        & (df["sku"] == sku)
        & (df["units"] > 0)
    ][["sku", "coded_customer"]].drop_duplicates()

    historical["seen_before"] = True

    result = current.merge(
        historical,
        on=["sku", "coded_customer"],
        how="left",
    )

    result = result[result["seen_before"].isna()].copy()

    columns = [
        "chain",
        "coded_customer",
        "store_number",
        "street_address",
        "city",
        "state",
        "zip",
        "channel",
        "sku",
        "first_month_purchased",
        "units",
    ]

    existing_cols = [col for col in columns if col in result.columns]

    result = result[existing_cols].sort_values(
        ["chain", "state", "coded_customer"],
        ascending=[True, True, True],
    )

    return {
        "title": f"New Buying Stores - {sku}",
        "subtitle": f"Stores that bought {sku} for the first time in {last_full_month}.",
        "columns": [
            {"key": "chain", "label": "Chain", "align": "left", "width": "160px"},
            {"key": "coded_customer", "label": "Customer", "align": "left", "width": "180px"},
            {"key": "store_number", "label": "Store #", "align": "left", "width": "110px"},
            {"key": "city", "label": "City", "align": "left", "width": "140px"},
            {"key": "state", "label": "State", "align": "left", "width": "80px"},
            {"key": "zip", "label": "ZIP", "align": "left", "width": "100px"},
            {"key": "channel", "label": "Channel", "align": "left", "width": "140px"},
            {"key": "sku", "label": "SKU", "align": "left", "width": "120px"},
            {"key": "first_month_purchased", "label": "First Month", "align": "left", "format": "month", "width": "140px"},
            {"key": "units", "label": "Latest Units", "align": "right", "format": "number", "width": "130px"},
        ],
        "table_width": "max-w-7xl",
        "rows": clean_for_json(result).to_dict("records"),
    }


@router.get("/sku_state_expansion/stores")
def get_sku_state_expansion_stores(
    org_id: str,
    sku: str,
):
    df = load_org_tables(org_id).copy()
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")

    current_month = pd.Timestamp.today().to_period("M")
    df = df[df["month_year"] != current_month].copy()

    last_full_month = df["month_year"].max()

    current = df[
        (df["month_year"] == last_full_month)
        & (df["sku"] == sku)
        & (df["units"] > 0)
        & (df["state"].notna())
    ].copy()

    historical = df[
        (df["month_year"] < last_full_month)
        & (df["sku"] == sku)
        & (df["units"] > 0)
        & (df["state"].notna())
    ].copy()

    historical_states = set(historical["state"].dropna().astype(str))

    result = current[
        ~current["state"].astype(str).isin(historical_states)
    ].copy()

    columns = [
        "chain",
        "coded_customer",
        "store_number",
        "street_address",
        "city",
        "state",
        "zip",
        "sku",
        "first_month_purchased",
        "units",
    ]

    existing_cols = [col for col in columns if col in result.columns]

    result = result[existing_cols].sort_values(
        ["state", "chain", "coded_customer"],
        ascending=[True, True, True],
    )

    return {
        "title": f"New State Distribution - {sku}",
        "subtitle": f"Stores where {sku} appeared in states with no prior purchase history before {last_full_month}.",
        "columns": [
            {"key": "chain", "label": "Chain", "align": "left", "width": "160px"},
            {"key": "coded_customer", "label": "Customer", "align": "left", "width": "180px"},
            {"key": "store_number", "label": "Store #", "align": "left", "width": "110px"},
            {"key": "city", "label": "City", "align": "left", "width": "140px"},
            {"key": "state", "label": "State", "align": "left", "width": "80px"},
            {"key": "zip", "label": "ZIP", "align": "left", "width": "100px"},
            {"key": "sku", "label": "SKU", "align": "left", "width": "120px"},
            {"key": "first_month_purchased", "label": "First Month", "align": "left", "format": "month", "width": "140px"},
            {"key": "units", "label": "Latest Units", "align": "right", "format": "number", "width": "130px"},
        ],
        "table_width": "max-w-7xl",
        "rows": clean_for_json(result).to_dict("records"),
    }
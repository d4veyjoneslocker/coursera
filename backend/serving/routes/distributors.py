import os
import pandas as pd
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query

from backend.data_pipeline.unfi_pipeline import refresh_unfi_processed_data
from backend.data_pipeline.generate_tables import save_base_tables
from backend.data_pipeline.table_loader import clear_table_cache

router = APIRouter(prefix="/distributors", tags=["Distributors"])


@router.get("/kehe/status")
def get_data_status(org_id: str = Query(...)):
    features_path = Path(f"backend/data/{org_id}/features_df.parquet")

    if not features_path.exists():
        return {
            "status": "no_data",
            "data_through": None,
            "last_updated": None,
            "is_stale": True,
        }

    df = pd.read_parquet(features_path)

    if df.empty or "month_year" not in df.columns:
        return {
            "status": "no_data",
            "data_through": None,
            "last_updated": None,
            "is_stale": True,
        }

    months = pd.Series(df["month_year"]).astype(str)
    latest_month = months.max()

    last_modified = datetime.fromtimestamp(features_path.stat().st_mtime)

    current_month = pd.Timestamp.today().to_period("M")
    data_month = pd.Period(latest_month, freq="M")
    is_stale = data_month < current_month

    return {
        "status": "ready",
        "data_through": latest_month,
        "last_updated": last_modified.strftime("%b %d, %Y %I:%M %p"),
        "is_stale": is_stale,
    }


@router.post("/unfi/refresh")
def refresh_unfi(org_id: str = Query(...)):
    unfi_cred = {
        "account_id": os.getenv("UNFI_ACCOUNT_ID"),
        "connector_id": os.getenv("UNFI_CONNECTOR_ID"),
        "username": os.getenv("UNFI_USERNAME"),
        "password": os.getenv("UNFI_PASSWORD"),
    }

    if not all(unfi_cred.values()):
        raise HTTPException(status_code=500, detail="Missing UNFI credentials")

    refresh_unfi_processed_data(org_id=org_id)

    save_base_tables(
        output_dir=f"backend/data/{org_id}",
        org_id=org_id,
    )

    clear_table_cache(org_id)

    return {"status": "success", "message": "UNFI refreshed"}
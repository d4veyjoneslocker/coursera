import os
import pandas as pd
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query

from backend.data_pipeline.unfi_pipeline import refresh_unfi_processed_data
from backend.data_pipeline.generate_tables import save_base_tables
from backend.data_pipeline.table_loader import clear_table_cache, load_org_tables
from backend.storage.local_cleanup import delete_local_org_data

router = APIRouter(prefix="/distributors", tags=["Distributors"])


@router.get("/kehe/status")
def get_data_status(org_id: str = Query(...)):
    try:
        df = load_org_tables(org_id)
    except Exception as e:
        print("STATUS LOAD ERROR:", repr(e))
        return {
            "status": "no_data",
            "data_through": None,
            "last_updated": None,
            "is_stale": True,
        }

    if df.empty or "month_year" not in df.columns:
        return {
            "status": "no_data",
            "data_through": None,
            "last_updated": None,
            "is_stale": True,
        }

    months = pd.Series(df["month_year"]).astype(str)
    latest_month = months.max()

    current_month = pd.Timestamp.today().to_period("M")
    data_month = pd.Period(latest_month, freq="M")
    is_stale = data_month < current_month

    return {
        "status": "ready",
        "data_through": latest_month,
        "last_updated": None,
        "is_stale": is_stale,
    }


@router.post("/unfi/refresh")
def refresh_unfi(org_id: str = Query(...)):
    try:
        refresh_unfi_processed_data(org_id=org_id)

        save_base_tables(
            output_dir=f"backend/data/{org_id}",
            org_id=org_id,
        )

        clear_table_cache(org_id)
        delete_local_org_data(org_id)


        return {
            "status": "success",
            "message": "UNFI refreshed",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"UNFI refresh failed: {str(e)}",
        )
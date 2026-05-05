import os
import pandas as pd
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Depends
from backend.email.digest_builder import build_weekly_digest
from backend.data_pipeline.table_loader import load_org_tables
from backend.filters.filters import get_filters

router = APIRouter(prefix="/email", tags=["Email"])


@router.get("/weekly-digest")
def get_weekly_digest(
    org_id: str = Query(...),
    filters: dict = Depends(get_filters),
):
    features_df = load_org_tables(org_id)

    digest = build_weekly_digest(features_df)

    return digest
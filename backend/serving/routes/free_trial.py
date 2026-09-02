import math

import numpy as np
from fastapi import APIRouter, Query

from backend.free_trial.run_insights import run_available_insights
from backend.data_pipeline.table_loader import load_org_tables


router = APIRouter(
    prefix="/free-trial",
    tags=["free-trial"],
)


def clean_payload(value):
    if isinstance(value, dict):
        return {
            key: clean_payload(val)
            for key, val in value.items()
        }

    if isinstance(value, list):
        return [
            clean_payload(item)
            for item in value
        ]

    if isinstance(value, (float, np.floating)) and math.isnan(value):
        return None

    return value


@router.get("/insights")
def get_free_trial_insights(
    org_id: str = Query(...),
):
    df = load_org_tables(org_id)

    df_all_time = df.copy()

    available_months = (
        df[["year", "month"]]
        .drop_duplicates()
        .shape[0]
    )

    insights = run_available_insights(
        df=df,
        df_all_time=df_all_time,
        available_months=available_months,
        filters=None,
    )

    top_findings = insights[:5]

    return {
        "available_months": available_months,
        "top_findings": clean_payload(top_findings),
        "additional_findings_count": max(len(insights) - 5, 0),
    }
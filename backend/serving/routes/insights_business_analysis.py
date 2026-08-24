import pandas as pd
import numpy as np

from fastapi import APIRouter, HTTPException, Depends, Query

from backend.insights.build_business_analysis import build_business_analysis, build_business_signals, build_business_stories, organize_business_stories, build_business_synthesis, build_business_narrative
from backend.context.build_business_context import detect_retailer_launches
from backend.data_pipeline.table_loader import load_org_tables
from backend.serving.api_helpers import clean_for_json
from backend.insights.insights_helper import get_last_full_month

from backend.insights.build_business_explanation_tree import build_business_explanation_tree
from backend.metrics.features import calculate_store_sku_lifecycle

from backend.filters.filter_table import filter_table
from backend.filters.filters import get_filters, generate_filter_api


router = APIRouter(
    prefix="/business-analysis",
    tags=["Business Analysis"],
)

@router.get("/filters")
def get_filter_options(
    column_name: str,
    org_id: str = Query(...),
    chain: list[str] | None = Query(None),
    sku: list[str] | None = Query(None),
    distributor: list[str] | None = Query(None),
    dc: list[str] | None = Query(None),
    channel: list[str] | None = Query(None),
    year: list[str] | None = Query(None),
    month_year: list[str] | None = Query(None),
    state: list[str] | None = Query(None),
):
    features_df = load_org_tables(org_id)

    filters = {
        "chain": chain,
        "sku": sku,
        "distributor": distributor,
        "dc": dc,
        "channel": channel,
        "year": year,
        "month_year": month_year,
        "state": state,
    }

    filters.pop(column_name, None)

    df = filter_table(features_df, **filters)
    options = generate_filter_api(df, column_name)

    if column_name == "month_year":
        current_month = pd.Timestamp.today().to_period("M").strftime("%Y-%m")
        options = [opt for opt in options if opt != current_month]

    return options

def clean_object_for_json(value):
    if isinstance(value, dict):
        return {
            key: clean_object_for_json(val)
            for key, val in value.items()
        }

    if isinstance(value, list):
        return [
            clean_object_for_json(val)
            for val in value
        ]

    if isinstance(value, float):
        if pd.isna(value) or np.isinf(value):
            return None

    return value

@router.get("/")
def get_business_analysis(
    org_id: str,
    filters: dict = Depends(get_filters),
    top_n_retailers: int = 10,
    top_n_states: int = 5,
):
    try:
        features_df = load_org_tables(
            org_id=org_id,
        )

        df = filter_table(
            features_df,
            **filters,
        )

        print("FILTERS RECEIVED:", filters)
        print("ROWS BEFORE:", len(features_df))
        print("ROWS AFTER:", len(df))
        print(
            "STATES AFTER FILTER:",
            df["state"].dropna().unique().tolist()
        )

        if df is None or df.empty:
            raise HTTPException(
                status_code=404,
                detail="No data found for the selected filters.",
            )

        analysis = build_business_analysis(
            df=df,
            top_n_retailers=top_n_retailers,
            top_n_states=top_n_states,
        )

        signals = build_business_signals(analysis)
        stories = build_business_stories(
            df=df,
            analysis=analysis,
            signals=signals,
        )
        organized_stories = organize_business_stories(stories)
        context = detect_retailer_launches(df)
        synthesis = build_business_synthesis(organized_stories)
        narrative = build_business_narrative(synthesis)


        result = {}

        for key, value in analysis.items():
            if isinstance(value, pd.DataFrame):
                df_out = clean_for_json(
                    value.copy()
                )

                result[key] = df_out.to_dict(
                    orient="records"
                )
            else:
                result[key] = value

        signals = clean_object_for_json(signals)
        stories = clean_object_for_json(stories)
        organized_stories = clean_object_for_json(organized_stories)
        synthesis = clean_object_for_json(synthesis)
        context = clean_object_for_json(context)
        narrative = clean_object_for_json(narrative)

        return {
            "analysis": result,
            "signals": signals,
            "stories": organized_stories,
            "context": context,
            "synthesis": synthesis,
            "narrative": narrative
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Business analysis failed: {str(e)}",
        )

@router.get("/tree")
def get_business_explanation_tree(
    org_id: str,
    filters: dict = Depends(get_filters),
):
    try:
        features_df = load_org_tables(org_id=org_id)

        df = filter_table(
            features_df,
            **filters,
        )

        if df is None or df.empty:
            raise HTTPException(
                status_code=404,
                detail="No data found for the selected filters.",
            )

        current_end = get_last_full_month()
        current_start = current_end - 2

        prior_end = current_start - 1
        prior_start = prior_end - 2

        # Build lifecycle from full history, not user-filtered history
        features_as_of = features_df[
            features_df["month_year"] <= current_end
        ].copy()

        lifecycle_table = calculate_store_sku_lifecycle(
            features_as_of,
            current_start=current_start,
            prior_start=prior_start,
        )

        # Analysis dataframe can still respect user filters
        df_as_of = df[
            df["month_year"] <= current_end
        ].copy()

        df_as_of = df_as_of.merge(
            lifecycle_table[
                ["pod_helper", "sku_lifecycle"]
            ].drop_duplicates(),
            on="pod_helper",
            how="left",
        )

        context = detect_retailer_launches(df_as_of)

        tree = build_business_explanation_tree(
            df=df_as_of,
            current_start=current_start,
            current_end=current_end,
            prior_start=prior_start,
            prior_end=prior_end,
            context_records=context,
        )

        tree = clean_object_for_json(tree)

        return {
            "current_period": {
                "start": str(current_start),
                "end": str(current_end),
            },
            "prior_period": {
                "start": str(prior_start),
                "end": str(prior_end),
            },
            "explanation_tree": tree,
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Business explanation tree failed: {str(e)}",
        )
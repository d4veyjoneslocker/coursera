from fastapi import APIRouter, Depends, Query

from backend.insights.business_review.business_review import run_business_review
from backend.insights.business_review.compose_business_review import compose_business_review
from backend.data_pipeline.table_loader import load_org_tables, load_active_pods
from backend.serving.api_helpers import clean_object_for_json


router = APIRouter()


@router.get("/business-review")
def get_business_review(
    period: str,
    year: int,
    comparison: str = "PY",
        org_id: str = Query(...),
):
    features_df = load_org_tables(org_id)
    active_pods_df = load_active_pods(org_id)

    # ---------------------------------------------------------
    # Main review
    # Example: H1 2026 vs H1 2025
    # ---------------------------------------------------------

    main = run_business_review(
        features_df=features_df,
        active_pods_df=active_pods_df,
        period=period,
        year=year,
        comparison=comparison,
    )

    # ---------------------------------------------------------
    # Within-period review
    # Example: Q2 2026 vs Q1 2026 for an H1 review
    # ---------------------------------------------------------

    within_period = None

    if period.upper() == "H1":
        within_period = run_business_review(
            features_df=features_df,
            active_pods_df=active_pods_df,
            period="Q2",
            year=year,
            comparison="PP",
        )

    elif period.upper() == "H2":
        within_period = run_business_review(
            features_df=features_df,
            active_pods_df=active_pods_df,
            period="Q4",
            year=year,
            comparison="PP",
        )

    # ---------------------------------------------------------
    # Compose the single frontend-ready Business Review
    # ---------------------------------------------------------

    composed_review = compose_business_review(
        review=main["review"],
        narrative_tree=main["narrative_tree"],
        df=main["df_narrative"],
        active_pods_df=active_pods_df,
        current_period=main["current_period"],
        prior_period=main["prior_period"],
        within_period=within_period,
    )

    # ---------------------------------------------------------
    # JSON serialization happens once, here at the API boundary
    # ---------------------------------------------------------

    return clean_object_for_json(composed_review)
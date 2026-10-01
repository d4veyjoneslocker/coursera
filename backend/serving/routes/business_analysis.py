import pandas as pd
import numpy as np
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Depends, Query

from backend.context.build_business_context import detect_retailer_launches
from backend.data_pipeline.table_loader import load_org_tables, load_active_pods
from backend.insights.insights_helper import get_last_full_month
from backend.serving.api_helpers import clean_object_for_json

from backend.insights.business_narrative.build_business_explanation_tree import build_business_explanation_tree
from backend.insights.business_narrative.select_tree_branches import build_shown_nodes
from backend.insights.business_narrative.narrate_business_explanation import narrate_shown_node, NarrativeInputs
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
    features_df = load_org_tables(
    org_id=org_id,
)


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

    df = filter_table(
        features_df,
        **filters,
    )

    options = generate_filter_api(
        df,
        column_name,
    )

    if column_name == "month_year":
        current_month = (
            pd.Timestamp.today()
            .to_period("M")
            .strftime("%Y-%m")
        )

        options = [
            opt
            for opt in options
            if opt != current_month
        ]

    return options



@router.get("/tree")
def get_business_explanation_tree(
    org_id: str,
    filters: dict = Depends(get_filters),
):
    try:
        # ---------------------------------------------------------
        # Load data
        # ---------------------------------------------------------

        features_df = load_org_tables(
            org_id=org_id,
        )

        active_pods_df = load_active_pods(
            org_id=org_id,
        )

        # ---------------------------------------------------------
        # Apply non-time filters
        #
        # Keep full history because the explanation tree needs
        # both the current and comparison periods.
        # ---------------------------------------------------------

        non_time_filters = {
            key: value
            for key, value in filters.items()
            if key not in {"year", "month_year"}
        }

        df = filter_table(
            features_df,
            **non_time_filters,
        )

        active_pods_filtered = filter_table(
            active_pods_df,
            **non_time_filters,
        )

        if df is None or df.empty:
            raise HTTPException(
                status_code=404,
                detail="No data found for the selected filters.",
            )

        # ---------------------------------------------------------
        # Comparison periods
        # ---------------------------------------------------------

        current_end = get_last_full_month()
        current_start = current_end - 2

        prior_end = current_start - 1
        prior_start = prior_end - 2

        # ---------------------------------------------------------
        # Lifecycle
        # ---------------------------------------------------------

        features_as_of = features_df[
            features_df["month_year"] <= current_end
        ].copy()

        lifecycle_table = calculate_store_sku_lifecycle(
            features_as_of,
            current_start=current_start,
            prior_start=prior_start,
        )

        # ---------------------------------------------------------
        # Analysis dataframe
        # ---------------------------------------------------------

        df_as_of = df[
            df["month_year"] <= current_end
        ].copy()

        df_as_of = df_as_of.merge(
            lifecycle_table[
                [
                    "pod_helper",
                    "sku_lifecycle",
                ]
            ].drop_duplicates(),
            on="pod_helper",
            how="left",
        )

        # ---------------------------------------------------------
        # Business context
        # ---------------------------------------------------------

        context = detect_retailer_launches(
            df_as_of,
        )

        # ---------------------------------------------------------
        # Explanation tree
        # ---------------------------------------------------------

        tree = build_business_explanation_tree(
            df=df_as_of,
            active_pods_df=active_pods_filtered,
            current_start=current_start,
            current_end=current_end,
            prior_start=prior_start,
            prior_end=prior_end,
            context_records=context,
        )

        # ---------------------------------------------------------
        # Surfacing
        # ---------------------------------------------------------

        shown_nodes = build_shown_nodes(
            tree,
        )

        # ---------------------------------------------------------
        # Shared narrative inputs
        #
        # Created once and shared by the entire recursive
        # enrichment/classification/narration process.
        # ---------------------------------------------------------

        inputs = NarrativeInputs(
            df=df_as_of,
            current_start=current_start,
            current_end=current_end,
            prior_start=prior_start,
            prior_end=prior_end,
        )

        # ---------------------------------------------------------
        # Enrichment → classification → narration
        # ---------------------------------------------------------

        narrative_tree = []

        for shown_node in shown_nodes:
            narrative_node = narrate_shown_node(
                shown_node=shown_node,
                inputs=inputs,
            )

            narrative_tree.append(
                narrative_node
            )

        # ---------------------------------------------------------
        # JSON serialization
        # ---------------------------------------------------------

        narrative_tree = clean_object_for_json(
            [
                asdict(node)
                for node in narrative_tree
            ]
        )

        # ---------------------------------------------------------
        # Response
        # ---------------------------------------------------------

        return {
            "current_period": {
                "start": str(current_start),
                "end": str(current_end),
            },
            "prior_period": {
                "start": str(prior_start),
                "end": str(prior_end),
            },
            "narrative_tree": narrative_tree,
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                "Business explanation tree failed: "
                f"{str(e)}"
            ),
        )
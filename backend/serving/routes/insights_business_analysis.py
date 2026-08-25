import pandas as pd
import numpy as np
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Depends, Query

from backend.context.build_business_context import detect_retailer_launches
from backend.data_pipeline.table_loader import load_org_tables
from backend.serving.api_helpers import clean_for_json
from backend.insights.insights_helper import get_last_full_month

from backend.insights.business_narrative.build_business_explanation_tree import build_business_explanation_tree
from backend.insights.business_narrative.select_tree_branches import build_shown_nodes
from backend.metrics.features import calculate_store_sku_lifecycle
from backend.insights.business_narrative.narrate_business_explanation import narrate_shown_node

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

        mature = next(


        child for child in tree.children
            if child.driver_type == "mature"
        )

        print(
            "BEFORE SHOWN:",
            mature.rate_current,
            mature.rate_prior,
            mature.rate_change,
        )

        for child in mature.children:
            print(
                child.scope,
                child.rate_current,
                child.rate_prior,
                child.rate_change,
            )


        all_nodes = []

        def collect_nodes(node):
            all_nodes.append(node)

            for child in node.children:
                collect_nodes(child)

        collect_nodes(tree)

        shown_nodes = build_shown_nodes(tree)

        narrative_tree = []

        for shown_node in shown_nodes:
            narrative_node = narrate_shown_node(
                shown_node=shown_node,
            )

            narrative_tree.append(narrative_node)


        explanation_tree = clean_object_for_json(tree.to_dict())
        narrative_tree = clean_object_for_json([asdict(node) for node in narrative_tree])


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
            detail=f"Business explanation tree failed: {str(e)}",
        )
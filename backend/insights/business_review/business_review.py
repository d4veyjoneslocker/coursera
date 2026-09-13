from dataclasses import asdict, is_dataclass

from backend.context.build_business_context import detect_retailer_launches
from backend.metrics.features import calculate_store_sku_lifecycle
from backend.metrics.metric_helpers import resolve_period_comparison

from backend.insights.business_narrative.build_business_explanation_tree import build_business_explanation_tree
from backend.insights.business_narrative.select_tree_branches import build_shown_nodes
from backend.insights.business_narrative.narrate_business_explanation import (
    narrate_shown_node,
    NarrativeInputs,
)

from backend.metrics.metric_comparisons import compare_metric
from backend.insights.business_review.business_review_helpers import (
    metric_summary,
    dataframe_to_records,
)


def build_business_review(
    df,
    df_full,
    period,
    year,
    comparison,
):
    common_args = {
        "df": df,
        "df_full": df_full,
        "period": period,
        "year": year,
        "comparison": comparison,
    }

    # Overall business metrics
    business = {
        "units": metric_summary(
            compare_metric(
                **common_args,
                metric="units",
                group_cols=[],
            )
        ),
        "buying_stores": metric_summary(
            compare_metric(
                **common_args,
                metric="buying_stores",
                group_cols=[],
            )
        ),
        "active_pods": metric_summary(
            compare_metric(
                **common_args,
                metric="active_pods",
                group_cols=[],
            )
        ),
        "velocity": metric_summary(
            compare_metric(
                **common_args,
                metric="velocity",
                group_cols=[],
            )
        ),
        "reorder_rate": metric_summary(
            compare_metric(
                **common_args,
                metric="reorder_rate",
                group_cols=[],
            )
        ),
    }

    # Chain-level metrics
    chains = {
        "units": compare_metric(
            **common_args,
            metric="units",
            group_cols=["chain"],
        ),
        "active_pods": compare_metric(
            **common_args,
            metric="active_pods",
            group_cols=["chain"],
        ),
        "velocity": compare_metric(
            **common_args,
            metric="velocity",
            group_cols=["chain"],
        ),
        "reorder_rate": compare_metric(
            **common_args,
            metric="reorder_rate",
            group_cols=["chain"],
        ),
    }

    # SKU-level metrics
    skus = {
        "units": compare_metric(
            **common_args,
            metric="units",
            group_cols=["sku"],
        ),
        "velocity": compare_metric(
            **common_args,
            metric="velocity",
            group_cols=["sku"],
        ),
    }

    return {
        "period": period,
        "year": year,
        "comparison": comparison,
        "business": business,

        "chains": {
            key: dataframe_to_records(value)
            for key, value in chains.items()
        },

        "skus": {
            key: dataframe_to_records(value)
            for key, value in skus.items()
        },
    }

def run_business_review(
    features_df,
    period,
    year,
    comparison,
):
    current_period, prior_period = resolve_period_comparison(
        period=period,
        year=year,
        comparison=comparison,
    )

    current_start = current_period["start"]
    current_end = current_period["end"]
    prior_start = prior_period["start"]
    prior_end = prior_period["end"]

    review = build_business_review(
        df=features_df,
        df_full=features_df,
        period=period,
        year=year,
        comparison=comparison,
    )

    features_as_of = features_df[
        features_df["month_year"] <= current_end
    ].copy()

    lifecycle_table = calculate_store_sku_lifecycle(
        features_as_of,
        current_start=current_start,
        prior_start=prior_start,
        current_end=current_end,
    )

    df_narrative = features_as_of.merge(
        lifecycle_table[
            ["pod_helper", "sku_lifecycle"]
        ].drop_duplicates(),
        on="pod_helper",
        how="left",
    )

    context = detect_retailer_launches(
        df_narrative
    )

    tree = build_business_explanation_tree(
        df=df_narrative,
        current_start=current_start,
        current_end=current_end,
        prior_start=prior_start,
        prior_end=prior_end,
        context_records=context,
    )

    shown_nodes = build_shown_nodes(tree)

    inputs = NarrativeInputs(
        df=df_narrative,
        current_start=current_start,
        current_end=current_end,
        prior_start=prior_start,
        prior_end=prior_end,
    )

    narrative_tree = []

    for shown_node in shown_nodes:
        narrative_node = narrate_shown_node(
            shown_node=shown_node,
            inputs=inputs,
        )

        narrative_tree.append(
            narrative_node
        )

        narrative_tree = [
            asdict(node) if is_dataclass(node) else node
            for node in narrative_tree
        ]
        
    return {
        "current_period": current_period,
        "prior_period": prior_period,
        "review": review,
        "narrative_tree": narrative_tree,
        "df_narrative": df_narrative,
    }
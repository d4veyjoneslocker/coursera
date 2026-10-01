import math
from typing import Any

import numpy as np

from backend.insights.missed_replenishment_risk import build_order_cadence_risk_insight
from backend.insights.failure_to_launch_new_store_risk import build_failure_to_launch_new_store_risk_insight
from backend.insights.growing_region_momentum import build_growing_region_momentum_insight
from backend.insights.overperforming_channel_momentum import build_overperforming_channel_momentum_insight
from backend.insights.dropoff_sku_risk import build_dropoff_sku_risk_insight
from backend.insights.sales_change_driver import build_sales_change_driver_insight
from backend.insights.void_sku_opportunity import build_void_opportunity_insight
from backend.insights.struggling_chain_risk import build_chain_struggling_insight


def make_json_safe(value: Any) -> Any:
    """
    Recursively convert values into JSON-safe Python types.

    Converts:
    - NaN and positive/negative infinity to None
    - NumPy scalar values to native Python values
    - Nested dictionaries, lists, and tuples recursively
    """
    if isinstance(value, dict):
        return {key: make_json_safe(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [make_json_safe(item) for item in value]

    if isinstance(value, np.generic):
        value = value.item()

    if isinstance(value, float) and not math.isfinite(value):
        return None

    return value


def flatten_insights(items):
    flattened = []

    for item in items:
        if item is None:
            continue

        if isinstance(item, list):
            flattened.extend(insight for insight in item if isinstance(insight, dict))
        elif isinstance(item, dict):
            flattened.append(item)

    return flattened


def sort_insights(insights):
    return sorted(flatten_insights(insights), key=lambda insight: insight.get("priority", 999))


def build_weekly_digest(df, df_full, active_pods_df, active_pods_full, filters=None):

    filters = filters or {}

    insights = flatten_insights(
        [
            # WHAT CHANGED
            build_sales_change_driver_insight(
                df=df,
                df_full=df_full,
                active_pods_df=active_pods_full,
                filters=filters,
            ),

            # OPPORTUNITIES
            build_void_opportunity_insight(
                df=df,
                df_all_time=df_full,
                active_pods_df=active_pods_full,
            ),
            build_growing_region_momentum_insight(
                df=df,
                active_pods_df=active_pods_full,
                filters=filters,
            ),
            build_overperforming_channel_momentum_insight(
                df=df,
                active_pods_df=active_pods_full,
                filters=filters,
            ),

            # AT RISK
            build_chain_struggling_insight(
                df=df,
                df_all_time=df_full,
                active_pods_df=active_pods_full,
                filters=filters,
            ),
            build_failure_to_launch_new_store_risk_insight(df=df, filters=filters),
            build_dropoff_sku_risk_insight(df=df, filters=filters),
            build_order_cadence_risk_insight(df=df, filters=filters),
        ]
    )

    sections = [
        {
            "key": "what_changed",
            "title": "What Changed",
            "description": "Structural shifts across the business this month.",
            "insights": sort_insights(
                [insight for insight in insights if insight.get("section") == "what_changed"]
            )[:4],
        },
        {
            "key": "opportunities",
            "title": "Opportunities",
            "description": "Areas where the data points to additional growth.",
            "insights": sort_insights(
                [insight for insight in insights if insight.get("section") == "opportunities"]
            )[:3],
        },
        {
            "key": "at_risk",
            "title": "At Risk",
            "description": "Watchouts that may deserve follow-up.",
            "insights": sort_insights(
                [insight for insight in insights if insight.get("section") == "at_risk"]
            )[:4],
        },
    ]

    digest = {
        "subject": "SKUba Deep Dive",
        "preview_text": "The trends, opportunities, and risks shaping the business beneath the surface.",
        "sections": sections,
    }

    return make_json_safe(digest)


def build_demo_what_changed():
    return [
        {
            "type": "state_change",
            "parts": [
                {"type": "sku_chip", "value": "SKU A"},
                {"type": "text", "value": " became the #1 SKU by monthly units for the first time."},
            ],
            "drilldown": {
                "label": "View SKU rankings",
                "href": "/insights/sku_rankings",
            },
        },
        {
            "type": "state_change",
            "parts": [
                {"type": "chain_chip", "value": "Whole Foods"},
                {"type": "text", "value": " added 17 new stores carrying SKU B this month."},
            ],
            "drilldown": {
                "label": "View new stores",
                "href": "/insights/new_distribution",
            },
        },
        {
            "type": "state_change",
            "parts": [
                {"type": "state_chip", "value": "Florida"},
                {"type": "text", "value": " became your highest-velocity state."},
            ],
            "drilldown": {
                "label": "View state rankings",
                "href": "/insights/state_rankings",
            },
        },
    ]
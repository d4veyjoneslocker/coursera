from backend.metrics.metric_tables import chain_insight_table, sku_insight_table, top_sales_month_insight_table, chain_sku_velocity_gap_opportunity_table
from backend.insights.chain_insights import build_chain_growth_insight, build_chain_decline_insight
from backend.insights.struggling_chain_risk import build_chain_struggling_insight
from backend.insights.void_sku_opportunity import build_void_opportunity_insight
#from backend.insights.sales_insights import build_top_sales_month_insight, build_top_reorder_rate_month_insight
from backend.insights.failure_to_launch_new_store_risk import build_failure_to_launch_new_store_risk_insight
from backend.insights.overperforming_channel_momentum import build_overperforming_channel_momentum_insight
from backend.insights.build_what_changed import build_what_changed


def sort_insights(insights):
    return sorted(
        [i for i in insights if isinstance(i, dict)],
        key=lambda x: x.get("priority", 999),
    )


def build_weekly_digest(features_df):
    df = features_df.copy()
    df_all_time = features_df.copy()

    what_changed = build_what_changed(df)

    what_changed = sort_insights(what_changed)

    chain_df = chain_insight_table(df)

    opportunities = sort_insights([
        build_void_opportunity_insight(df, df_all_time),
        build_overperforming_channel_momentum_insight(df),
    ])

    at_risk = sort_insights([
        build_chain_struggling_insight(
            df=df,
            df_all_time=df_all_time,
        ),
        build_failure_to_launch_new_store_risk_insight(
            df=df,
        ),
        build_chain_decline_insight(chain_df),
    ])

    return {
        "subject": "SKUba Deep Dive — May",
        "preview_text": "The trends, opportunities, and risks shaping the business beneath the surface.",
        "sections": [
            {
                "key": "what_changed",
                "title": "What Changed",
                "description": "Structural shifts across the business this month.",
                "insights": what_changed[:4],
            },
            {
                "key": "opportunities",
                "title": "Opportunities",
                "description": "Areas where the data points to additional growth.",
                "insights": opportunities[:3],
            },
            {
                "key": "at_risk",
                "title": "At Risk",
                "description": "Watchouts that may deserve follow-up.",
                "insights": at_risk[:3],
            },
        ],
    }

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
from backend.filters.filter_table import filter_table
from backend.metrics.metric_tables import (
    chain_insight_table,
    sku_insight_table,
    top_sales_month_insight_table,
)
from backend.insights.chain_insights import build_chain_growth_insight, build_chain_decline_insight
from backend.insights.store_health_insights import build_chain_struggling_insight
from backend.insights.sku_insights import build_sku_velocity_insight, build_void_opportunity_insight
from backend.insights.sales_insights import (
    build_top_sales_month_insight,
    build_top_reorder_rate_month_insight,
)


def sort_insights(insights):
    return sorted(
        [i for i in insights if i],
        key=lambda x: x.get("priority", 999),
    )


def build_weekly_digest(features_df):
    filters = {}

    df = features_df.copy()
    df_all_time = features_df.copy()

    chain_df = chain_insight_table(df)
    sku_df = sku_insight_table(df)
    top_month_df = top_sales_month_insight_table(df, df_all_time)

    what_working = sort_insights([
        build_top_sales_month_insight(top_month_df),
        build_top_reorder_rate_month_insight(top_month_df),
        build_chain_growth_insight(chain_df, filters=filters),
        build_sku_velocity_insight(sku_df, filters=filters),
    ])

    opportunities = sort_insights([
        build_void_opportunity_insight(df_all_time, filters=filters),
    ])

    at_risk = sort_insights([
        build_chain_struggling_insight(df, filters=filters),
        build_chain_decline_insight(chain_df, filters=filters),
    ])

    return {
        "subject": "Your weekly SKUba digest",
        "preview_text": "What’s working, what to chase, and what’s at risk.",
        "sections": [
            {
                "key": "whats_working",
                "title": "What’s Working",
                "description": "Momentum worth protecting or doubling down on.",
                "insights": what_working[:2],
            },
            {
                "key": "opportunities",
                "title": "Opportunities",
                "description": "Areas where the data points to additional growth.",
                "insights": opportunities[:2],
            },
            {
                "key": "at_risk",
                "title": "At Risk",
                "description": "Watchouts that may deserve follow-up.",
                "insights": at_risk[:2],
            },
        ],
    }
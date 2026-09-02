import backend.insights as insight
from backend.insights.insights_metadata import INSIGHT_REQUIREMENTS


INSIGHT_RUNNERS = {
    "chain_struggling": {
        "function": insight.build_chain_struggling_insight,
        "args": ["df", "df_all_time", "filters"],
    },

    "dropoff_sku": {
        "function": insight.build_dropoff_sku_risk_insight,
        "args": ["df", "filters"],
    },

    "order_cadence": {
        "function": insight.build_order_cadence_risk_insight,
        "args": ["df", "filters"],
    },

    "failure_to_launch": {
        "function": insight.build_failure_to_launch_new_store_risk_insight,
        "args": ["df", "filters"],
    },

    "distribution_opportunity": {
        "function": insight.build_void_opportunity_insight,
        "args": ["df", "df_all_time"],
    },
}


def get_available_insights(available_months: int) -> list[str]:
    return [
        insight_name
        for insight_name, requirements in INSIGHT_REQUIREMENTS.items()
        if available_months >= requirements["min_history_months"]
    ]

def run_available_insights(
    df,
    df_all_time,
    available_months: int,
    filters=None,
):
    context = {
        "df": df,
        "df_all_time": df_all_time,
        "filters": filters,
    }

    available_insights = get_available_insights(available_months)

    results = []

    for insight_name in available_insights:
        runner = INSIGHT_RUNNERS.get(insight_name)

        if runner is None:
            continue

        kwargs = {
            arg: context[arg]
            for arg in runner["args"]
        }

        result = runner["function"](**kwargs)

        if result is not None:
            if isinstance(result, list):
                results.extend(result)
            else:
                results.append(result)

    return results
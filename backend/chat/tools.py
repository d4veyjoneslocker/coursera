import pandas as pd

from .schemas import MetricRequest
from backend.metrics.metric_callers import METRIC_CALCULATORS, calculate_metric, compare_metric
from backend.filters.filter_table import filter_table, resolve_entity_value
from backend.data_pipeline.table_loader import load_org_tables, load_fill_rate_df, load_active_pods
from backend.metrics.metric_helpers import resolve_period, resolve_period_comparison, filter_to_period, resolve_default_comparison_period
from .chat_helpers import format_metric_display
from backend.insights.insights_helper import safe_float


def prepare_metric_request(
    request: MetricRequest,
    df,
    active_pods_df,
):
    metric_definition = METRIC_CALCULATORS.get(request.metric)

    available_distributors = metric_definition.get("available_distributors")

    if (
        available_distributors
        and request.distributor
        and request.distributor.upper() not in available_distributors
    ):
        raise ValueError(
            f"{metric_definition['display_name']} is only available for "
            f"{', '.join(available_distributors)}."
        )

    if metric_definition is None:
        raise ValueError(f"Unsupported metric: {request.metric}")

    period_name = request.period or "L3M"

    period = resolve_period(
        period=period_name,
    )
    
    resolved_chain = resolve_entity_value(
        df,
        "chain",
        request.chain,
    )

    filters = {
        "distributor": resolve_entity_value(
            df,
            "distributor",
            request.distributor,
        ),
        "chain": resolved_chain,
        "sku": resolve_entity_value(
            df,
            "sku",
            request.sku,
        ),
        "dc": resolve_entity_value(
            df,
            "dc",
            request.dc,
        ),
    }

    df_filtered = filter_table(
        df,
        **filters,
    )

    active_pods_filtered = filter_table(
        active_pods_df,
        **filters,
    )

    df_filtered = filter_to_period(
        df_filtered,
        period["start"],
        period["end"],
    )

    active_pods_filtered = filter_to_period(
        active_pods_filtered,
        period["start"],
        period["end"],
    )
    
    group_cols = (
        [request.group_by]
        if request.group_by
        else []
    )

    if not df_filtered.empty:
        print(df_filtered["month_year"].value_counts().sort_index())

    return {
        "df_filtered": df_filtered,
        "active_pods_df": active_pods_filtered,
        "group_cols": group_cols,
        "filters": filters,
        "period": period,
        "metric_definition": metric_definition,
    }


def get_metric(
    org_id: str,
    request: MetricRequest,
):
    active_pods_df = load_active_pods(org_id)

    if request.metric in {"fill_rate", "order_velocity"}:
        df = load_fill_rate_df(org_id)
    else:
        df = load_org_tables(org_id)

    prepared = prepare_metric_request(
        request=request,
        df=df,
        active_pods_df=active_pods_df,
    )

    result = calculate_metric(
        metric_name=request.metric,
        df_filtered=prepared["df_filtered"],
        active_pods_df=prepared["active_pods_df"],
        group_cols=prepared["group_cols"],
    )

    metric_definition = prepared["metric_definition"]

    value = (
        safe_float(result["value"].iloc[0])
        if not result.empty
        else None
    )

    display = format_metric_display(
        value,
        metric_definition["formatter"],
    )

    return {
        "status": "success",
        "metric": request.metric,
        "display_name": metric_definition["display_name"],
        "value": value,
        "display": display,
        "formatter": metric_definition["formatter"],
        "period": {
            "label": prepared["period"]["label"],
            "start": str(prepared["period"]["start"]),
            "end": str(prepared["period"]["end"]),
        },
        "filters": prepared["filters"],
        "group_by": request.group_by,
        "description": metric_definition["description"],
        "caveats": metric_definition["caveats"],
        "interpretation": metric_definition["interpretation"],
        "change_type": metric_definition.get("change_type", "percent"),
        "available_distributors": metric_definition.get("available_distributors"),
        "additive": metric_definition.get("additive"),
    }

def rank_metric(
    org_id: str,
    request: MetricRequest,
):
    active_pods_df = load_active_pods(org_id)

    if request.metric in {"fill_rate", "order_velocity"}:
        df = load_fill_rate_df(org_id)
    else:
        df = load_org_tables(org_id)

    prepared = prepare_metric_request(
        request=request,
        df=df,
        active_pods_df=active_pods_df,
    )

    if not request.group_by:
        raise ValueError("Ranking requires a group_by field.")

    result = calculate_metric(
        metric_name=request.metric,
        df_filtered=prepared["df_filtered"],
        active_pods_df=prepared["active_pods_df"],
        group_cols=[request.group_by],
    )

    result = result.dropna(subset=[request.group_by])

    metric_definition = prepared["metric_definition"]

    directionality = (
        metric_definition
        .get("interpretation", {})
        .get("directionality", "neutral")
    )

    if request.ranking_intent == "highest":
        ascending = False

    elif request.ranking_intent == "lowest":
        ascending = True

    elif request.ranking_intent == "best":
        if directionality == "higher_better":
            ascending = False
        elif directionality == "lower_better":
            ascending = True
        else:
            raise ValueError(
                f"Cannot determine what 'best' means for "
                f"{metric_definition['display_name']}."
            )

    elif request.ranking_intent == "worst":
        if directionality == "higher_better":
            ascending = True
        elif directionality == "lower_better":
            ascending = False
        else:
            raise ValueError(
                f"Cannot determine what 'worst' means for "
                f"{metric_definition['display_name']}."
            )

    else:
        # temporary fallback while transitioning
        ascending = request.sort_direction == "ascending"
    limit = request.limit or 10

    result = (
        result
        .sort_values("value", ascending=ascending)
        .head(limit)
    )

    rows = []

    for _, row in result.iterrows():
        value = safe_float(row["value"])

        rows.append({
            request.group_by: row[request.group_by],
            "value": value,
            "display": format_metric_display(
                value,
                metric_definition["formatter"],
            ),
        })

    resolved_sort_direction = (
        "ascending" if ascending else "descending"
    )

    return {
        "status": "success",
        "type": "ranking",
        "metric": request.metric,
        "display_name": metric_definition["display_name"],
        "group_by": request.group_by,
        "ranking_intent": request.ranking_intent,
        "sort_direction": resolved_sort_direction,
        "period": {
            "label": prepared["period"]["label"],
            "start": str(prepared["period"]["start"]),
            "end": str(prepared["period"]["end"]),
        },
        "filters": prepared["filters"],
        "rows": rows,
    }

def compare_metric_tool(
    org_id: str,
    request: MetricRequest,
):
    metric_definition = METRIC_CALCULATORS.get(request.metric)

    if metric_definition is None:
        raise ValueError(f"Unsupported metric: {request.metric}")

    comparison_type = request.comparison_type or "PP"

    active_pods_df = load_active_pods(org_id)

    if request.metric in {"fill_rate", "order_velocity"}:
        df = load_fill_rate_df(org_id)
    else:
        df = load_org_tables(org_id)

    # ---------------------------------------------
    # AVAILABILITY VALIDATION
    # ---------------------------------------------

    available_distributors = metric_definition.get(
        "available_distributors"
    )

    if (
        available_distributors
        and request.distributor
        and request.distributor.upper() not in available_distributors
    ):
        raise ValueError(
            f"{metric_definition['display_name']} is only available for "
            f"{', '.join(available_distributors)}."
        )

    # ---------------------------------------------
    # RESOLVE ENTITY VALUES
    # ---------------------------------------------

    filters = {
        "distributor": resolve_entity_value(
            df,
            "distributor",
            request.distributor,
        ),
        "chain": resolve_entity_value(
            df,
            "chain",
            request.chain,
        ),
        "sku": resolve_entity_value(
            df,
            "sku",
            request.sku,
        ),
        "dc": resolve_entity_value(
            df,
            "dc",
            request.dc,
        ),
    }

    # ---------------------------------------------
    # APPLY ENTITY FILTERS ONLY
    # do NOT filter periods here
    # ---------------------------------------------

    df_filtered = filter_table(
        df,
        **filters,
    )

    active_pods_filtered = filter_table(
        active_pods_df,
        **filters,
    )

    if request.period:
        period = request.period
    else:
        period = resolve_default_comparison_period(
            df=df_filtered,
            comparison_type=comparison_type,
        )

    group_cols = (
        [request.group_by]
        if request.group_by
        else []
    )

    current_period, comparison_period = resolve_period_comparison(
        period=period,
        year=request.year,
        comparison=comparison_type,
    )

    # ---------------------------------------------
    # RUN EXISTING COMPARISON ENGINE
    # ---------------------------------------------

    result = compare_metric(
        df=df_filtered,
        df_full=df_filtered,
        active_pods_df=active_pods_filtered,
        metric_name=request.metric,
        period=period,
        year=request.year,
        comparison=comparison_type,
        group_cols=group_cols,
    )

    if result.empty:
        return {
            "status": "success",
            "type": "comparison",
            "metric": request.metric,
            "display_name": metric_definition["display_name"],
            "comparison_type": comparison_type,
            "current_period": {
                "label": current_period["label"],
                "start": str(current_period["start"]),
                "end": str(current_period["end"]),
            },
            "comparison_period": {
                "label": comparison_period["label"],
                "start": str(comparison_period["start"]),
                "end": str(comparison_period["end"]),
            },
            "period": period,
            "filters": filters,
            "group_by": request.group_by,
            "change_direction": request.change_direction,
            "ranking_intent": request.ranking_intent,
            "empty_reason": "no_data",
            "rows": [],
        }

    # ---------------------------------------------
    # FORMAT CHANGE
    # ---------------------------------------------

    change_type = metric_definition.get(
        "change_type",
        "percent",
    )

    rows = []

    for _, row in result.iterrows():
        current_value = safe_float(
            row["value_current"]
        )

        comparison_value = safe_float(
            row["value_comparison"]
        )

        abs_change = safe_float(
            row["abs_change"]
        )

        pct_change_value = safe_float(
            row["pct_change"]
        )

        if change_type == "points":
            change = abs_change

            change_display = (
                None
                if change is None
                else f"{change * 100:+.1f} pts"
            )

        else:
            change = pct_change_value

            change_display = (
                None
                if change is None
                else f"{change:+.1%}"
            )

        output_row = {
            "current_value": current_value,
            "current_display": format_metric_display(
                current_value,
                metric_definition["formatter"],
            ),
            "comparison_value": comparison_value,
            "comparison_display": format_metric_display(
                comparison_value,
                metric_definition["formatter"],
            ),
            "abs_change": abs_change,
            "pct_change": pct_change_value,
            "change": change,
            "change_display": change_display,
            "comparison_eligible": bool(
                row["comparison_eligible"]
            ),
        }

        if request.group_by:
            output_row[request.group_by] = row[
                request.group_by
            ]

        rows.append(output_row)


    # AFTER the loop is finished, sort/filter/limit
    # Filter grouped comparison rows
    empty_reason = None

    if request.group_by:
        # Rows with an actual group value
        valid_group_rows = [
            row
            for row in rows
            if pd.notna(row.get(request.group_by))
        ]

        # Rows where the comparison is actually valid
        eligible_rows = [
            row
            for row in valid_group_rows
            if row["change"] is not None
            and row["comparison_eligible"]
        ]

        filtered_rows = eligible_rows

        # Apply the user's requested direction of change
        if request.change_direction == "improved":
            filtered_rows = [
                row
                for row in eligible_rows
                if row["change"] >= 0.001
            ]

        elif request.change_direction == "declined":
            filtered_rows = [
                row
                for row in eligible_rows
                if row["change"] <= -0.001
            ]

        elif request.change_direction == "flat":
            filtered_rows = [
                row
                for row in eligible_rows
                if abs(row["change"]) < 0.001
            ]

        # Determine WHY nothing remains
        if not valid_group_rows:
            empty_reason = "no_valid_groups"

        elif not eligible_rows:
            empty_reason = "no_eligible_comparisons"

        elif (
            request.change_direction
            and not filtered_rows
        ):
            empty_reason = "no_matching_change_direction"

        rows = filtered_rows

        # Rank only if requested
        if request.ranking_intent:
            if request.ranking_intent in {"highest", "best"}:
                reverse = True
            elif request.ranking_intent in {"lowest", "worst"}:
                reverse = False
            else:
                reverse = True

            rows = sorted(
                rows,
                key=lambda row: row["change"],
                reverse=reverse,
            )

            limit = request.limit or 10
            rows = rows[:limit]

    return {
        "status": "success",
        "type": "comparison",
        "metric": request.metric,
        "display_name": metric_definition["display_name"],
        "change_type": change_type,
        "change_direction": request.change_direction,
        "comparison_type": comparison_type,
                    "current_period": {
                "label": current_period["label"],
                "start": str(current_period["start"]),
                "end": str(current_period["end"]),
            },
            "comparison_period": {
                "label": comparison_period["label"],
                "start": str(comparison_period["start"]),
                "end": str(comparison_period["end"]),
            },
        "period": period,
        "filters": filters,
        "group_by": request.group_by,
        "description": metric_definition.get("description"),
        "caveats": metric_definition.get("caveats"),
        "interpretation": metric_definition.get("interpretation"),
        "ranking_intent": request.ranking_intent,
        "empty_reason": empty_reason,
        "rows": rows,
    }

def get_clarification_options(
    org_id: str,
    request: MetricRequest,
):
    field = request.clarification_field
    
    if field == "metric":
        return [
            definition["display_name"]
            for definition in METRIC_CALCULATORS.values()
        ]

    if field == "chain":
        # return actual chains for org
        ...

    if field == "sku":
        # return actual SKUs for org
        ...

    if field == "dc":
        # return actual DCs for org
        ...

    return None


def main():
    test_requests = [
        MetricRequest(
            metric="fill_rate",
            period="L1M",
            chain="SPROUTS",
        ),
        MetricRequest(
            metric="fill_rate",
            period="L3M",
            chain="SPROUTS",
        ),
        MetricRequest(
            metric="units",
            period="L1M",
            chain="SPROUTS",
        ),
        MetricRequest(
            metric="active_pods",
            period="L1M",
            distributor="KEHE",
        ),
        MetricRequest(
            metric="velocity",
            period="L3M",
            chain="SPROUTS",
        ),
    ]

    for request in test_requests:
        print("\n" + "=" * 70)
        print("TESTING:")
        print(request)

        result = get_metric(
            org_id="67a96381-5014-4a9b-bfe8-a14e6da5affe",
            request=request,
        )

        print("\nRESULT:")
        print(result)


if __name__ == "__main__":
    main()
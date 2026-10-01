import time

import pandas as pd

from fastapi import APIRouter, Depends, Query

from backend.filters.filter_table import filter_table
from backend.filters.filters import get_filters, generate_filter_api

from backend.metrics.metric_calculators import calculate_units
from backend.metrics.metric_tables import chain_table

from backend.data_pipeline.table_loader import (
    load_org_tables,
    load_active_pods,
    load_fill_rate_df,
)

from backend.metrics.fill_rate.metrics import fill_rate_metrics
from backend.metrics.kpis.build_kpis import build_kpis

from backend.serving.api_helpers import (
    clean_for_json,
    prep_monthly_graph,
    remove_time_filters,
    convert_selected_months,
    ChartMetric,
    ChartView,
    build_expanded_chart,
    clean_object_for_json,
)


router = APIRouter(prefix="/overview", tags=["Overview"])


def log_timing(name: str, start: float):
    elapsed = time.perf_counter() - start
    print(f"⏱️ {name}: {elapsed:.3f}s")


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


@router.get("/kpis")
def kpis(org_id: str = Query(...), filters: dict = Depends(get_filters)):
    start = time.perf_counter()

    features_df = load_org_tables(org_id)
    active_pods_full = load_active_pods(org_id)

    # User's exact filtered selection, including time filters
    df = filter_table(features_df, **filters)

    # Same business filters, but retain full history for comparisons
    non_time_filters = remove_time_filters(filters)

    df_full = filter_table(
        features_df,
        **non_time_filters,
    )

    active_pods_full = filter_table(
        active_pods_full,
        **non_time_filters,
    )

    # Historical metric universe stops at the selected endpoint.
    # Without an explicit time filter, stop at the latest actual sales month.
    selected_months = convert_selected_months(
        filters.get("month_year")
    )

    if selected_months:
        end_month = max(
            pd.Period(month, freq="M")
            for month in selected_months
        )
        active_pods_cutoff = end_month
    else:
        end_month = None
        active_pods_cutoff = df["month_year"].max()

    active_pods_df = active_pods_full[
        active_pods_full["month_year"] <= active_pods_cutoff
    ].copy()

    result = build_kpis(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_df,
        active_pods_full=active_pods_full,
        end_month=end_month,
    )

    result = clean_object_for_json(result)

    log_timing("KPIS", start)

    return result


@router.get("/fill_rate")
def fill_rate(org_id: str = Query(...), filters: dict = Depends(get_filters)):
    start = time.perf_counter()

    fill_rate_df = load_fill_rate_df(org_id)

    fill_rate_filters = {
        key: value
        for key, value in filters.items()
        if key in fill_rate_df.columns
    }

    df = filter_table(fill_rate_df, **fill_rate_filters)

    result = fill_rate_metrics(df, grain=["month_year"])

    result = result[["month_year", "fill_rate"]]

    result = prep_monthly_graph(result, "fill_rate")
    result = clean_for_json(result)

    log_timing("FILL RATE", start)

    return result.to_dict(orient="records")


@router.get("/skus")
def skus(org_id: str = Query(...), filters: dict = Depends(get_filters)):
    start = time.perf_counter()

    features_df = load_org_tables(org_id)
    df = filter_table(features_df, **filters)

    result = calculate_units(
        df,
        "sku",
    ).sort_values(
        "units",
        ascending=False,
    )

    total_units = calculate_units(df)

    result["value"] = result["units"] / total_units
    result = result.rename(columns={"sku": "name"})
    result = result[["name", "value"]]

    log_timing("SKUS", start)

    return result.to_dict(orient="records")


@router.get("/channels")
def channels(org_id: str = Query(...), filters: dict = Depends(get_filters)):
    start = time.perf_counter()

    features_df = load_org_tables(org_id)
    df = filter_table(features_df, **filters)

    result = calculate_units(
        df,
        ["channel"],
    ).sort_values(
        "units",
        ascending=False,
    )

    total_units = calculate_units(df)

    result["value"] = result["units"] / total_units
    result["name"] = result["channel"]
    result = result[["name", "value"]]

    log_timing("CHANNELS", start)

    return result.to_dict(orient="records")


@router.get("/chain_table")
def chain_table_api(org_id: str = Query(...), filters: dict = Depends(get_filters)):
    start = time.perf_counter()

    features_df = load_org_tables(org_id)
    active_pods_full = load_active_pods(org_id)

    # User's exact filtered selection, including time filters
    df = filter_table(
        features_df,
        **filters,
    )

    # Same business filters, but retain full history for comparisons
    non_time_filters = remove_time_filters(filters)

    df_full = filter_table(
        features_df,
        **non_time_filters,
    )

    active_pods_full = filter_table(
        active_pods_full,
        **non_time_filters,
    )

    # Historical metric universe stops at the selected endpoint.
    # Without an explicit time filter, stop at the latest actual sales month.
    selected_months = convert_selected_months(
        filters.get("month_year")
    )

    if selected_months:
        end_month = max(
            pd.Period(month, freq="M")
            for month in selected_months
        )
        active_pods_cutoff = end_month
    else:
        end_month = None
        active_pods_cutoff = df["month_year"].max()

    active_pods_df = active_pods_full[
        active_pods_full["month_year"] <= active_pods_cutoff
    ].copy()

    result = chain_table(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_df,
        active_pods_full=active_pods_full,
        end_month=end_month,
    )

    result = clean_for_json(result)

    log_timing("CHAIN TABLE", start)

    return result.to_dict(orient="records")


@router.get("/chart")
def expanded_chart(
    org_id: str = Query(...),
    metric: ChartMetric = Query(...),
    view: ChartView = Query("default"),
    filters: dict = Depends(get_filters),
):
    features_df = load_org_tables(org_id)
    active_pods_df = load_active_pods(org_id)

    fill_rate_df = (
        load_fill_rate_df(org_id)
        if metric == "fill_rate"
        else None
    )

    result = build_expanded_chart(
        features_df=features_df,
        active_pods_df=active_pods_df,
        metric=metric,
        view=view,
        filters=filters,
        fill_rate_df=fill_rate_df,
    )

    return result
# New buyers that didn't reorder after the first 2 months
# Grouped by chain
# Compare how many stores did reorder
# Identify load-in quantities
# See if stores that did reorder had certain qualities vs stores that didn't

import pandas as pd

from backend.insights.insights_helper import get_last_full_month, format_float, format_number, build_filter_context, format_pct, safe_float


def _build_launch_event_table(
    df: pd.DataFrame,
    reorder_opportunity_months: int = 2,
) -> pd.DataFrame:
    """
    One row per chain x store x sku launch event.

    Source of truth for:
    - launch month
    - initial load-in
    - reorder behavior within the reorder window
    - at-risk flag
    """
    last_full_month = get_last_full_month()

    grain = ["chain", "coded_customer", "sku"]

    monthly = (
        df.groupby(grain + ["month_year"], as_index=False)
        .agg(
            units=("units", "sum"),
            revenue=("revenue", "sum"),
            store_number=("store_number", "first"),
            street_address=("street_address", "first"),
            city=("city", "first"),
            state=("state", "first"),
            zip=("zip", "first"),
            channel=("channel", "first"),
        )
    )

    first_purchase = (
        monthly[monthly["units"] > 0]
        .groupby(grain, as_index=False)
        .agg(launch_month=("month_year", "min"))
    )

    table = monthly.merge(first_purchase, on=grain, how="left")

    # Determines months since launch and calculates it as an int
    table["months_after_launch"] = (table["month_year"] - table["launch_month"]).apply(lambda x: x.n)

    launch_load = (
        table[table["months_after_launch"] == 0]
        .copy()
        .rename(
            columns={
                "units": "initial_units",
                "revenue": "initial_revenue",
            }
        )
    )

    reorder_window = table[
        table["months_after_launch"].between(
            1,
            reorder_opportunity_months,
        )
    ].copy()

    reorder_summary = (
        reorder_window.groupby(grain, as_index=False)
        .agg(
            reorder_units_in_window=("units", "sum"),
            reorder_revenue_in_window=("revenue", "sum"),
            reorder_months_in_window=("month_year", "nunique"),
            first_reorder_month=("month_year", "min"),
        )
    )

    result = launch_load.merge(reorder_summary, on=grain, how="left")

    result["reorder_units_in_window"] = result["reorder_units_in_window"].fillna(0)
    result["reorder_revenue_in_window"] = result["reorder_revenue_in_window"].fillna(0)
    result["reorder_months_in_window"] = (result["reorder_months_in_window"].fillna(0).astype(int))

    result["reordered_within_window"] = result["reorder_units_in_window"] > 0

    result["reorder_window_end_month"] = (result["launch_month"] + reorder_opportunity_months)

    result["surface_month"] = result["reorder_window_end_month"] + 1

    result["is_reorder_eval_eligible"] = (
        result["reorder_window_end_month"] <= last_full_month
    )

    result["at_risk_no_reorder"] = (
        result["is_reorder_eval_eligible"]
        & ~result["reordered_within_window"]
    )

    result["launch_cohort_id"] = (
        result["chain"].astype(str)
        + "|"
        + result["launch_month"].astype(str)
    )

    columns = [
        "launch_cohort_id",
        "chain",
        "coded_customer",
        "sku",
        "launch_month",
        "surface_month",
        "reorder_window_end_month",
        "initial_units",
        "initial_revenue",
        "reordered_within_window",
        "at_risk_no_reorder",
        "is_reorder_eval_eligible",
        "reorder_units_in_window",
        "reorder_revenue_in_window",
        "reorder_months_in_window",
        "first_reorder_month",
        "store_number",
        "street_address",
        "city",
        "state",
        "zip",
        "channel",
    ]

    return result[[col for col in columns if col in result.columns]]


def _build_launch_sku_breakdown(
    launch_events: pd.DataFrame,
) -> pd.DataFrame:
    """
    One row per chain x launch cohort x sku.

    Used to compare SKU-level reorder behavior and load-in differences.
    """
    eligible = launch_events[launch_events["is_reorder_eval_eligible"]].copy()

    if eligible.empty:
        return pd.DataFrame()

    grain = ["launch_cohort_id", "chain", "launch_month", "surface_month", "sku"]

    breakdown = (
        eligible.groupby(grain, as_index=False)
        .agg(
            launched_stores=("coded_customer", "nunique"),
            at_risk_stores=("at_risk_no_reorder", "sum"),
            reordered_stores=("reordered_within_window", "sum"),
            avg_initial_units=("initial_units", "mean"),
            avg_initial_units_at_risk=(
                "initial_units",
                lambda s: s[eligible.loc[s.index, "at_risk_no_reorder"]].mean(),
            ),
            avg_initial_units_reordered=(
                "initial_units",
                lambda s: s[eligible.loc[s.index, "reordered_within_window"]].mean(),
            )
        )
    )

    breakdown["at_risk_rate"] = (
        breakdown["at_risk_stores"] / breakdown["launched_stores"]
    )

    breakdown["reorder_rate"] = (
        breakdown["reordered_stores"] / breakdown["launched_stores"]
    )

    breakdown["avg_initial_units_gap"] = (
        breakdown["avg_initial_units_at_risk"]
        - breakdown["avg_initial_units_reordered"]
    )

    return breakdown


def _build_launch_cohort_summary(
    launch_events: pd.DataFrame,
) -> pd.DataFrame:
    """
    One row per chain x launch cohort.

    Used as the primary analysis table for deciding whether
    a launch follow-up insight should surface.
    """
    eligible = launch_events[launch_events["is_reorder_eval_eligible"]].copy()

    if eligible.empty:
        return pd.DataFrame()

    grain = ["launch_cohort_id", "chain", "launch_month", "surface_month"]

    summary = (
        eligible.groupby(grain, as_index=False)
        .agg(
            launched_stores=("coded_customer", "nunique"),
            launched_skus=("sku", "nunique"),
            launched_placements=("coded_customer", "count"),

            at_risk_placements=("at_risk_no_reorder", "sum"),
            reordered_placements=("reordered_within_window", "sum"),

            avg_initial_units=("initial_units", "mean"),
            avg_initial_units_at_risk=(
                "initial_units",
                lambda s: s[eligible.loc[s.index, "at_risk_no_reorder"]].mean(),
            ),
            avg_initial_units_reordered=(
                "initial_units",
                lambda s: s[eligible.loc[s.index, "reordered_within_window"]].mean(),
            ),
        )
    )

    summary["at_risk_rate"] = (summary["at_risk_placements"] / summary["launched_placements"])
    summary["reorder_rate"] = (summary["reordered_placements"] / summary["launched_placements"])
    summary["avg_initial_units_gap"] = (summary["avg_initial_units_at_risk"] - summary["avg_initial_units_reordered"])

    return summary


def build_failure_to_launch_new_store_risk_table(
    df: pd.DataFrame,
    reorder_opportunity_months: int = 2,
) -> dict[str, pd.DataFrame]:

    #Builds all analysis-ready tables for the failure-to-launch insight.

    launch_events = _build_launch_event_table(df=df, reorder_opportunity_months=reorder_opportunity_months)

    sku_breakdown = _build_launch_sku_breakdown(launch_events=launch_events)

    cohort_summary = _build_launch_cohort_summary(launch_events=launch_events)

    return {
        "cohort_summary": cohort_summary,
        "sku_breakdown": sku_breakdown,
        "launch_events": launch_events,
    }

def analyze_failure_to_launch_new_store_risk(
    table: pd.DataFrame,
    limit: int = 2,
    min_at_risk_placements: int = 3,
    min_at_risk_rate: float = 0.25,
) -> pd.DataFrame | None:
    """
    Applies insight criteria and selects launch cohorts that need follow-up.

    Expects the cohort_summary table from build_failure_to_launch_new_store_risk_table().
    """
    if table is None or table.empty:
        return None

    table = table.copy()

    required_cols = [
        "launch_cohort_id",
        "chain",
        "launch_month",
        "surface_month",
        "launched_stores",
        "launched_skus",
        "launched_placements",
        "at_risk_placements",
        "reordered_placements",
        "at_risk_rate",
        "reorder_rate",
    ]

    missing_cols = [col for col in required_cols if col not in table.columns]

    if missing_cols:
        return None

    current_month = pd.Timestamp.today().to_period("M")

    table = table[
        table["chain"].notna()
        & ~table["chain"].eq("CONFIDENTIAL")
    ].copy()

    table = table[
        (table["surface_month"] == current_month)
        & (table["launched_placements"] > 0)
        & (table["at_risk_placements"] >= min_at_risk_placements)
        & (table["at_risk_rate"] >= min_at_risk_rate)
    ].copy()

    if table.empty:
        return None

    table = table.sort_values(
        ["at_risk_placements", "at_risk_rate", "launched_placements"],
        ascending=[False, False, False],
    )

    return table.head(limit)

def normalize_failure_to_launch_new_store_risk_data(
    table: pd.DataFrame,
    sku_breakdown: pd.DataFrame | None = None,
) -> list[dict] | dict | None:
    """
    Normalizes analyzed failure-to-launch rows into structured insight-ready data objects.
    """
    if table is None or table.empty:
        return None

    results = []

    for _, row in table.iterrows():
        launch_cohort_id = row["launch_cohort_id"]

        sku_rows = pd.DataFrame()

        if sku_breakdown is not None and not sku_breakdown.empty:
            sku_rows = sku_breakdown[
                sku_breakdown["launch_cohort_id"] == launch_cohort_id
            ].copy()

            sku_rows = sku_rows.sort_values(
                ["at_risk_stores", "at_risk_rate"],
                ascending=[False, False],
            )

        sku_breakdown_data = sku_rows.to_dict("records") if not sku_rows.empty else []

        result = {
            "launch_cohort_id": launch_cohort_id,
            "chain": row["chain"],
            "launch_month": row["launch_month"],
            "surface_month": row["surface_month"],

            "launched_stores": int(row["launched_stores"]),
            "launched_skus": int(row["launched_skus"]),
            "launched_placements": int(row["launched_placements"]),

            "at_risk_placements": int(row["at_risk_placements"]),
            "reordered_placements": int(row["reordered_placements"]),

            "at_risk_rate": float(row["at_risk_rate"]),
            "reorder_rate": float(row["reorder_rate"]),

            "avg_initial_units": row.get("avg_initial_units"),
            "avg_initial_units_at_risk": row.get("avg_initial_units_at_risk"),
            "avg_initial_units_reordered": safe_float(row.get("avg_initial_units_reordered")),
            "avg_initial_units_gap": safe_float(row.get("avg_initial_units_gap")),

            "sku_breakdown": sku_breakdown_data,

            "metrics": {
                "launched_stores": int(row["launched_stores"]),
                "launched_skus": int(row["launched_skus"]),
                "launched_placements": int(row["launched_placements"]),
                "at_risk_placements": int(row["at_risk_placements"]),
                "reordered_placements": int(row["reordered_placements"]),
                "at_risk_rate": float(row["at_risk_rate"]),
                "reorder_rate": float(row["reorder_rate"]),
                "avg_initial_units": row.get("avg_initial_units"),
                "avg_initial_units_at_risk": row.get("avg_initial_units_at_risk"),
                "avg_initial_units_reordered": safe_float(row.get("avg_initial_units_reordered")),
                "avg_initial_units_gap": safe_float(row.get("avg_initial_units_gap")),
            },

            "entities": {
                "chain": row["chain"],
                "launch_cohort_id": launch_cohort_id,
                "launch_month": row["launch_month"],
            },
        }

        results.append(result)

    if len(results) == 1:
        return results[0]

    return results

def describe_failure_to_launch_new_store_risk(data, filters=None):
    if data is None:
        return None

    chain = data["chain"]
    launch_month = data["launch_month"]

    launched_stores = data["launched_stores"]
    launched_skus = data["launched_skus"]
    launched_placements = data["launched_placements"]

    at_risk_placements = data["at_risk_placements"]
    at_risk_rate = data["at_risk_rate"]
    reorder_rate = data["reorder_rate"]

    avg_initial_units_at_risk = data.get("avg_initial_units_at_risk")
    avg_initial_units_reordered = data.get("avg_initial_units_reordered")
    avg_initial_units_gap = data.get("avg_initial_units_gap")

    sku_breakdown = data.get("sku_breakdown", [])

    context_str, context_parts = build_filter_context(filters, exclude_keys={"chain"})

    launch_month_display = (
        launch_month.to_timestamp().strftime("%B %Y")
        if hasattr(launch_month, "to_timestamp")
        else pd.to_datetime(launch_month).strftime("%B %Y")
    )

    at_risk_rate_fmt = format_pct(at_risk_rate)
    reorder_rate_fmt = format_pct(reorder_rate)

    launched_stores_fmt = format_number(launched_stores)
    launched_skus_fmt = format_number(launched_skus)
    launched_placements_fmt = format_number(launched_placements)
    at_risk_placements_fmt = format_number(at_risk_placements)

    avg_initial_units_at_risk_fmt = format_float(avg_initial_units_at_risk)
    avg_initial_units_reordered_fmt = format_float(avg_initial_units_reordered)

    headline = f"Recent {chain} launch may need follow-up."

    summary = (
        f"{at_risk_placements_fmt} of {launched_placements_fmt} placements from the "
        f"{launch_month_display} {chain} launch have not reordered after 2 full months."
    )

    parts = [
        {"type": "chip", "value": chain, "tone": "neutral"},
        {"type": "text", "value": " has "},
        {"type": "chip", "value": at_risk_placements_fmt, "tone": "negative"},
        {"type": "text", "value": f" of {launched_placements_fmt} launch placements that have not reordered"},
        *context_parts,
        {"type": "text", "value": "after 2 full months."},
    ]

    intro_block = {
        "type": "text",
        "value": (
            f"In the {launch_month_display} {chain} launch, "
            f"{launched_stores_fmt} stores received "
            f"{launched_placements_fmt} total placements spanning "
            f"{launched_skus_fmt} SKUs. "
            f"{at_risk_placements_fmt} placements, or {at_risk_rate_fmt}, "
            f"have not reordered after the first 2 full reorder opportunities."
        ),
    }

    action_block = {
        "type": "text",
        "value": (
            f"These are the stores most worth following up with now. They received an initial shipment, "
            f"but have not placed a second order within the expected launch window."
        ),
    }

    load_in_block = None

    include_load_in_block = (
        avg_initial_units_at_risk is not None
        and avg_initial_units_reordered is not None
        and pd.notna(avg_initial_units_at_risk)
        and pd.notna(avg_initial_units_reordered)
    )

    if include_load_in_block:
        load_in_block = {
            "type": "text",
            "value": (
                f"At-risk placements loaded in with {avg_initial_units_at_risk_fmt} units on average, "
                f"compared with {avg_initial_units_reordered_fmt} units for placements that did reorder."
            ),
        }

    sku_block = None

    if sku_breakdown:
        top_sku = sku_breakdown[0]

        top_sku_name = top_sku.get("sku")
        top_sku_at_risk = top_sku.get("at_risk_stores")
        top_sku_launched = top_sku.get("launched_stores")
        top_sku_rate = top_sku.get("at_risk_rate")
        top_sku_avg_at_risk = top_sku.get("avg_initial_units_at_risk")
        top_sku_avg_reordered = top_sku.get("avg_initial_units_reordered")

        if top_sku_name is not None and top_sku_at_risk is not None and top_sku_launched is not None:
            sku_block = {
                "type": "text",
                "value": (
                    f"{top_sku_name} is the biggest SKU-level watchout: "
                    f"{format_number(top_sku_at_risk)} of {format_number(top_sku_launched)} stores "
                    f"have not reordered."
                ),
            }

            if (
                top_sku_avg_at_risk is not None
                and top_sku_avg_reordered is not None
                and pd.notna(top_sku_avg_at_risk)
                and pd.notna(top_sku_avg_reordered)
            ):
                sku_block["value"] += (
                    f" At-risk stores loaded in with {format_float(top_sku_avg_at_risk)} units on average, "
                    f"compared with {format_float(top_sku_avg_reordered)} units for stores that reordered."
                )

    description = [
        intro_block,
        action_block,
        load_in_block,
        sku_block,
    ]

    description = [block for block in description if block is not None]

    key_points = [
        (
            f"{at_risk_placements_fmt} of {launched_placements_fmt} launch "
            f"placements from the {launch_month_display} cohort have not "
            f"reordered after 2 full months."
        ),
        (
            f"The launch included {launched_stores_fmt} stores, "
            f"{launched_skus_fmt} SKUs, and {launched_placements_fmt} "
            f"total placements."
        ),
    ]

    if include_load_in_block:
        key_points.append(
            (
                f"At-risk placements loaded in with "
                f"{avg_initial_units_at_risk_fmt} units on average, "
                f"compared with {avg_initial_units_reordered_fmt} units "
                f"for placements that did reorder."
            )
        )

    return {
        "headline": headline,
        "summary": summary,
        "parts": parts,
        "description": description,
        "key_points": key_points,
    }

def create_failure_to_launch_new_store_risk_store_list(
    launch_events: pd.DataFrame,
    launch_cohort_id: str,
) -> pd.DataFrame:
    """
    Returns at-risk launch placements for the selected launch cohort.

    Uses the launch_events table directly so the insight counts
    and drilldown remain perfectly aligned.
    """
    table = launch_events.copy()

    table = table[
        (table["launch_cohort_id"] == launch_cohort_id)
        & (table["at_risk_no_reorder"])
    ].copy()

    if table.empty:
        return table

    columns = [
        "chain",
        "coded_customer",
        "store_number",
        "street_address",
        "city",
        "state",
        "zip",
        "channel",
        "sku",
        "launch_month",
        "initial_units",
        "initial_revenue",
        "reorder_units_in_window",
        "reorder_revenue_in_window",
        "reorder_months_in_window",
        "first_reorder_month",
        "surface_month",
    ]

    existing_cols = [col for col in columns if col in table.columns]

    result = table[existing_cols].copy()

    return result.sort_values(
        ["initial_units", "chain", "sku"],
        ascending=[False, True, True],
    )

def get_failure_to_launch_new_store_risk_drilldown_config(
    launch_cohort_id: str,
) -> dict:
    return {
        "label": "View stores needing launch follow-up",
        "href": (
            f"/insights/failure_to_launch"
            f"?launch_cohort_id={launch_cohort_id}"
        ),
        "title": "Stores Needing Launch Follow-Up",
        "subtitle": (
            "Launch placements that received an initial shipment but have not "
            "reordered within the expected window."
        ),
        "columns": [
            {"key": "chain", "label": "Chain", "align": "left"},
            {"key": "coded_customer", "label": "Customer", "align": "left"},
            {"key": "store_number", "label": "Store #", "align": "left"},
            {"key": "street_address", "label": "Address", "align": "left"},
            {"key": "city", "label": "City", "align": "left"},
            {"key": "state", "label": "State", "align": "left"},
            {"key": "zip", "label": "ZIP", "align": "left"},
            {"key": "channel", "label": "Channel", "align": "left"},
            {"key": "sku", "label": "SKU", "align": "left"},
            {
                "key": "launch_month",
                "label": "Launch Month",
                "align": "left",
                "format": "month",
            },
            {
                "key": "initial_units",
                "label": "Initial Units",
                "align": "right",
                "format": "number",
            },
        ],
    }

def build_failure_to_launch_new_store_risk_insight(
    df: pd.DataFrame,
    filters=None,
):
    tables = build_failure_to_launch_new_store_risk_table(df=df)

    analyzed = analyze_failure_to_launch_new_store_risk(
        table=tables["cohort_summary"],
        limit=2,
    )

    data = normalize_failure_to_launch_new_store_risk_data(
        table=analyzed,
        sku_breakdown=tables["sku_breakdown"],
    )

    if data is None:
        return None

    data_list = data if isinstance(data, list) else [data]

    insights = []

    for item in data_list:
        description = describe_failure_to_launch_new_store_risk(
            data=item,
            filters=filters,
        )

        if description is None:
            continue

        launch_cohort_id = item["launch_cohort_id"]
        chain = item["chain"]

        insights.append({
            "type": "failure_to_launch_new_store_risk",
            "section": "at_risk",

            **description,

            "metrics": item["metrics"],
            "entities": item["entities"],

            "chain": chain,
            "launch_cohort_id": launch_cohort_id,
            "launch_month": item["launch_month"],

            "drilldown": get_failure_to_launch_new_store_risk_drilldown_config(
                launch_cohort_id=launch_cohort_id,
            ),
        })

    if not insights:
        return None

    return insights
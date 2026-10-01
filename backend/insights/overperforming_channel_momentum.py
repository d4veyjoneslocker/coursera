# Identifies channels (besides ECommerce) that are overperforming based on their share of stores

import pandas as pd

from backend.insights.insights_helper import build_filter_context, format_number, format_pct, get_last_full_month
from backend.metrics.metric_callers import compare_metric


CHANNEL_COL = "channel"
DEFAULT_LIMIT = 1

EXCLUDED_CHANNELS = {"E-COMMERCE"}

MIN_RECENT_UNITS = 25
MIN_UNIT_SHARE = 0.05
MIN_STORE_SHARE = 0.03
MIN_RETURN_ON_DISTRIBUTION_INDEX = 1.5
MIN_VELOCITY_OUTPERFORMANCE_PCT = 0.15
MIN_REORDER_RATE_FLOOR = 0.25
MIN_UNIT_SHARE_GAIN_TO_MENTION = 0.03

def build_overperforming_channel_momentum_table(
    df: pd.DataFrame,
    active_pods_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Builds one row per channel showing return on distribution:
    unit share vs store share, supported by 3m velocity and reorder behavior.

    Assumes names are already normalized before reaching the insight layer.
    """

    if df is None or df.empty or CHANNEL_COL not in df.columns:
        return pd.DataFrame()

    table = df[~df[CHANNEL_COL].isin(EXCLUDED_CHANNELS)].copy()

    if table.empty:
        return pd.DataFrame()

    active_pods_table = active_pods_df[
        ~active_pods_df[CHANNEL_COL].isin(EXCLUDED_CHANNELS)
    ].copy()

    units = compare_metric(
        df=table,
        df_full=table,
        active_pods_df=active_pods_table,
        metric_name="units",
        period="L3M",
        comparison="PP",
        group_cols=[CHANNEL_COL],
    )

    velocity = compare_metric(
        df=table,
        df_full=table,
        active_pods_df=active_pods_table,
        metric_name="velocity",
        period="L3M",
        comparison="PP",
        group_cols=[CHANNEL_COL],
    )

    reorder = compare_metric(
        df=table,
        df_full=table,
        active_pods_df=active_pods_table,
        metric_name="reorder_rate",
        period="L3M",
        comparison="PP",
        group_cols=[CHANNEL_COL],
    )

    stores = compare_metric(
        df=table,
        df_full=table,
        active_pods_df=active_pods_table,
        metric_name="buying_stores",
        period="L3M",
        comparison="PP",
        group_cols=[CHANNEL_COL],
    )

    result = units[
        [
            CHANNEL_COL,
            "value_current",
            "value_comparison",
            "pct_change",
            "abs_change",
        ]
    ].rename(
        columns={
            "value_current": "recent_3m_units",
            "value_comparison": "prior_3m_units",
            "pct_change": "unit_growth_pct",
            "abs_change": "unit_growth_abs",
        }
    )

    result = result.merge(
        velocity[
            [
                CHANNEL_COL,
                "value_current",
                "value_comparison",
                "pct_change",
                "abs_change",
            ]
        ].rename(
            columns={
                "value_current": "recent_3m_velocity",
                "value_comparison": "prior_3m_velocity",
                "pct_change": "velocity_growth_pct",
                "abs_change": "velocity_growth_abs",
            }
        ),
        on=CHANNEL_COL,
        how="outer",
    )

    result = result.merge(
        reorder[
            [
                CHANNEL_COL,
                "value_current",
                "value_comparison",
                "pct_change",
                "abs_change",
            ]
        ].rename(
            columns={
                "value_current": "recent_3m_reorder_rate",
                "value_comparison": "prior_3m_reorder_rate",
                "pct_change": "reorder_rate_growth_pct",
                "abs_change": "reorder_rate_growth_abs",
            }
        ),
        on=CHANNEL_COL,
        how="outer",
    )

    result = result.merge(
        stores[
            [
                CHANNEL_COL,
                "value_current",
                "value_comparison",
                "pct_change",
                "abs_change",
            ]
        ].rename(
            columns={
                "value_current": "recent_3m_stores",
                "value_comparison": "prior_3m_stores",
                "pct_change": "store_growth_pct",
                "abs_change": "store_growth_abs",
            }
        ),
        on=CHANNEL_COL,
        how="outer",
    )

    result = result.fillna(
        {
            "recent_3m_units": 0,
            "prior_3m_units": 0,
            "recent_3m_stores": 0,
            "prior_3m_stores": 0,
        }
    )

    total_units = compare_metric(
        df=table,
        df_full=table,
        active_pods_df=active_pods_table,
        metric_name="units",
        period="L3M",
        comparison="PP",
        group_cols=[],
    )

    total_velocity = compare_metric(
        df=table,
        df_full=table,
        active_pods_df=active_pods_table,
        metric_name="velocity",
        period="L3M",
        comparison="PP",
        group_cols=[],
    )

    total_reorder = compare_metric(
        df=table,
        df_full=table,
        active_pods_df=active_pods_table,
        metric_name="reorder_rate",
        period="L3M",
        comparison="PP",
        group_cols=[],
    )

    total_stores = compare_metric(
        df=table,
        df_full=table,
        active_pods_df=active_pods_table,
        metric_name="buying_stores",
        period="L3M",
        comparison="PP",
        group_cols=[],
    )

    total_recent_units = total_units["value_current"].iloc[0] if not total_units.empty else 0
    total_prior_units = total_units["value_comparison"].iloc[0] if not total_units.empty else 0
    total_recent_stores = total_stores["value_current"].iloc[0] if not total_stores.empty else 0
    total_prior_stores = total_stores["value_comparison"].iloc[0] if not total_stores.empty else 0
    total_recent_velocity = total_velocity["value_current"].iloc[0] if not total_velocity.empty else pd.NA
    total_recent_reorder_rate = total_reorder["value_current"].iloc[0] if not total_reorder.empty else pd.NA

    result["recent_unit_share"] = result["recent_3m_units"] / total_recent_units if total_recent_units else pd.NA
    result["prior_unit_share"] = result["prior_3m_units"] / total_prior_units if total_prior_units else pd.NA
    result["unit_share_change_abs"] = result["recent_unit_share"] - result["prior_unit_share"]

    result["recent_store_share"] = result["recent_3m_stores"] / total_recent_stores if total_recent_stores else pd.NA
    result["prior_store_share"] = result["prior_3m_stores"] / total_prior_stores if total_prior_stores else pd.NA
    result["store_share_change_abs"] = result["recent_store_share"] - result["prior_store_share"]

    result["return_on_distribution_index"] = result["recent_unit_share"] / result["recent_store_share"].replace(0, pd.NA)
    result["prior_return_on_distribution_index"] = result["prior_unit_share"] / result["prior_store_share"].replace(0, pd.NA)
    result["return_on_distribution_change_abs"] = result["return_on_distribution_index"] - result["prior_return_on_distribution_index"]

    result["total_recent_3m_velocity"] = total_recent_velocity
    result["total_recent_3m_reorder_rate"] = total_recent_reorder_rate

    result["velocity_outperformance_pct"] = (
        result["recent_3m_velocity"] / total_recent_velocity - 1
        if pd.notna(total_recent_velocity) and total_recent_velocity != 0
        else pd.NA
    )

    result["reorder_rate_outperformance_abs"] = (
        result["recent_3m_reorder_rate"] - total_recent_reorder_rate
        if pd.notna(total_recent_reorder_rate)
        else pd.NA
    )

    return result

def analyze_overperforming_channel_momentum(table: pd.DataFrame, limit: int = DEFAULT_LIMIT) -> pd.DataFrame | None:
    if table is None or table.empty:
        return None

    required_cols = [CHANNEL_COL, "recent_3m_units", "recent_unit_share", "recent_store_share", "return_on_distribution_index", "recent_3m_velocity", "velocity_outperformance_pct", "recent_3m_reorder_rate"]

    if any(col not in table.columns for col in required_cols):
        return None

    candidates = table[
        (table["recent_3m_units"].fillna(0) >= MIN_RECENT_UNITS)
        & (table["recent_unit_share"].fillna(0) >= MIN_UNIT_SHARE)
        & (table["recent_store_share"].fillna(0) >= MIN_STORE_SHARE)
        & (table["return_on_distribution_index"].fillna(0) >= MIN_RETURN_ON_DISTRIBUTION_INDEX)
        & (table["velocity_outperformance_pct"].fillna(0) >= MIN_VELOCITY_OUTPERFORMANCE_PCT)
        & (table["recent_3m_reorder_rate"].fillna(0) >= MIN_REORDER_RATE_FLOOR)
    ].copy()

    if candidates.empty:
        return None

    candidates["momentum_score"] = candidates["return_on_distribution_index"].fillna(0) + candidates["velocity_outperformance_pct"].fillna(0) + candidates["recent_unit_share"].fillna(0)

    return candidates.sort_values(["momentum_score", "return_on_distribution_index", "recent_3m_units"], ascending=[False, False, False]).head(limit)

def normalize_overperforming_channel_momentum_data(analyzed_table: pd.DataFrame) -> dict | None:
    if analyzed_table is None or analyzed_table.empty:
        return None

    items = []

    for _, row in analyzed_table.iterrows():
        item = {
            "channel": row.get(CHANNEL_COL),
            "recent_3m_units": row.get("recent_3m_units"),
            "prior_3m_units": row.get("prior_3m_units"),
            "unit_growth_abs": row.get("unit_growth_abs"),
            "unit_growth_pct": row.get("unit_growth_pct"),
            "recent_3m_velocity": row.get("recent_3m_velocity"),
            "prior_3m_velocity": row.get("prior_3m_velocity"),
            "velocity_growth_pct": row.get("velocity_growth_pct"),
            "velocity_outperformance_pct": row.get("velocity_outperformance_pct"),
            "recent_3m_reorder_rate": row.get("recent_3m_reorder_rate"),
            "prior_3m_reorder_rate": row.get("prior_3m_reorder_rate"),
            "reorder_rate_growth_abs": row.get("reorder_rate_growth_abs"),
            "reorder_rate_outperformance_abs": row.get("reorder_rate_outperformance_abs"),
            "recent_3m_stores": row.get("recent_3m_stores"),
            "prior_3m_stores": row.get("prior_3m_stores"),
            "recent_unit_share": row.get("recent_unit_share"),
            "prior_unit_share": row.get("prior_unit_share"),
            "unit_share_change_abs": row.get("unit_share_change_abs"),
            "recent_store_share": row.get("recent_store_share"),
            "prior_store_share": row.get("prior_store_share"),
            "store_share_change_abs": row.get("store_share_change_abs"),
            "return_on_distribution_index": row.get("return_on_distribution_index"),
            "prior_return_on_distribution_index": row.get("prior_return_on_distribution_index"),
            "return_on_distribution_change_abs": row.get("return_on_distribution_change_abs"),
        }

        item["metrics"] = {k: v for k, v in item.items() if k != "channel"}
        item["entities"] = {"channel": item["channel"]}
        items.append(item)

    return {"items": items, "metrics": items[0]["metrics"] if items else {}, "entities": items[0]["entities"] if items else {}}

def describe_overperforming_channel_momentum(data: dict | None, filters=None) -> dict | None:
    if data is None or not data.get("items"):
        return None

    item = data["items"][0]
    context_str, context_parts = build_filter_context(filters, exclude_keys={"channel"})

    channel = item["channel"]
    recent_units_fmt = format_number(item["recent_3m_units"])
    recent_store_share_fmt = format_pct(item["recent_store_share"])
    recent_unit_share_fmt = format_pct(item["recent_unit_share"])
    unit_share_change_fmt = format_pct(item["unit_share_change_abs"], decimals=1, signed=True)
    rod_index_fmt = f"{item['return_on_distribution_index']:.1f}x" if pd.notna(item.get("return_on_distribution_index")) else "-"
    velocity_outperformance_fmt = format_pct(item["velocity_outperformance_pct"], signed=True)
    reorder_rate_fmt = format_pct(item["recent_3m_reorder_rate"])

    headline = f"{channel} is producing outsized volume for its footprint."

    summary = f"{channel}{context_str} represents {recent_store_share_fmt} of recent buying stores but drives {recent_unit_share_fmt} of recent units, a {rod_index_fmt} return on distribution."

    parts = [
        {"type": "chip", "value": channel, "tone": "positive"},
        *context_parts,
        {"type": "text", "value": " represents "},
        {"type": "chip", "value": recent_store_share_fmt, "tone": "neutral"},
        {"type": "text", "value": " of recent buying stores but drives "},
        {"type": "chip", "value": recent_unit_share_fmt, "tone": "positive"},
        {"type": "text", "value": " of recent units."},
    ]

    description = [
        {"type": "text", "value": f"{channel} is showing strong return on distribution{context_str}. Over the last 3 full months, it drove {recent_units_fmt} units while representing only {recent_store_share_fmt} of recent buying stores."},
        {"type": "text", "value": f"The channel is producing {rod_index_fmt} its expected unit share based on store footprint, with velocity {velocity_outperformance_fmt} above the filtered business average and a recent reorder rate of {reorder_rate_fmt}."},
    ]

    if item.get("unit_share_change_abs") is not None and pd.notna(item["unit_share_change_abs"]) and item["unit_share_change_abs"] >= MIN_UNIT_SHARE_GAIN_TO_MENTION:
        description.append({"type": "text", "value": f"Its share of recent units also increased by {unit_share_change_fmt}, suggesting the channel is becoming more important to the business."})

    description.append({"type": "text", "value": "This is a channel worth prioritizing for expansion, retailer storytelling, or account focus because the current distribution is working harder than the average door."})

    key_points = [
        (
            f"{channel} represents {recent_store_share_fmt} of recent buying "
            f"stores but drives {recent_unit_share_fmt} of recent units."
        ),
        (
            f"The channel is producing {rod_index_fmt} its expected unit share "
            f"based on store footprint."
        ),
        (
            f"Velocity is running {velocity_outperformance_fmt} above the "
            f"filtered business average, with a recent reorder rate of "
            f"{reorder_rate_fmt}."
        ),
    ]

    if (
        item.get("unit_share_change_abs") is not None
        and pd.notna(item["unit_share_change_abs"])
        and item["unit_share_change_abs"] >= MIN_UNIT_SHARE_GAIN_TO_MENTION
    ):
        key_points.append(
            (
                f"Its share of recent units increased by "
                f"{unit_share_change_fmt}, suggesting the channel is becoming "
                f"more important to the business."
            )
        )

    return {"headline": headline, "summary": summary, "parts": parts, "description": description, "key_points": key_points}

def create_overperforming_channel_momentum_store_list(df: pd.DataFrame, analyzed_table: pd.DataFrame) -> pd.DataFrame:
    if analyzed_table is None or analyzed_table.empty:
        return pd.DataFrame()

    channel = analyzed_table.iloc[0][CHANNEL_COL]
    last_full_month = get_last_full_month()
    recent_months = [last_full_month - i for i in range(0, 3)]

    table = df[(df[CHANNEL_COL] == channel) & (df["month_year"].isin(recent_months))].copy()

    if table.empty:
        return pd.DataFrame()

    store_cols = [
    "coded_customer",
    "chain",
    "state",
]

    existing_store_cols = [
        col for col in store_cols
        if col in table.columns
    ]

    result = (
        table.groupby(existing_store_cols, as_index=False)
        .agg(
            recent_units=("units", "sum"),
            active_skus=("sku", "nunique"),
        )
    )

    top_skus = (
        table.groupby(existing_store_cols + ["sku"], as_index=False)
        .agg(sku_units=("units", "sum"))
        .sort_values("sku_units", ascending=False)
        .drop_duplicates(existing_store_cols)
        .rename(columns={"sku": "top_sku"})
    )

    result = result.merge(
        top_skus[
            existing_store_cols + ["top_sku"]
        ],
        on=existing_store_cols,
        how="left",
    )

    result = result.sort_values(
        "recent_units",
        ascending=False,
    )

    return result


def get_overperforming_channel_momentum_drilldown_config(channel: str):
    return {
        "label": "View stores in this channel",
        "href": "/insights/overperforming_channel_momentum",
        "title": f"Top Stores in {channel}",

        "subtitle": (
            f"Stores contributing most to recent outperformance in {channel}."
        ),

        "columns": [
            {
                "key": "coded_customer",
                "label": "Customer",
                "align": "left",
            },
            {
                "key": "chain",
                "label": "Chain",
                "align": "left",
            },
            {
                "key": "state",
                "label": "State",
                "align": "left",
            },
            {
                "key": "recent_units",
                "label": "L3M Units",
                "align": "right",
                "format": "number",
            },
            {
                "key": "active_skus",
                "label": "Active SKUs",
                "align": "right",
                "format": "number",
            },
            {
                "key": "top_sku",
                "label": "Top SKU",
                "align": "left",
            },
        ],
    }

def build_overperforming_channel_momentum_insight(
    df: pd.DataFrame,
    active_pods_df: pd.DataFrame,
    filters=None,
    limit: int = DEFAULT_LIMIT,
):
    table = build_overperforming_channel_momentum_table(
        df=df,
        active_pods_df=active_pods_df,
    )

    analyzed = analyze_overperforming_channel_momentum(table, limit=limit)
    data = normalize_overperforming_channel_momentum_data(analyzed)
    description = describe_overperforming_channel_momentum(data=data, filters=filters)

    if data is None or description is None:
        return None

    item = data["items"][0]

    return {
        "type": "overperforming_channel_momentum",
        "section": "where_to_double_down",
        **description,
        "metrics": item["metrics"],
        "entities": item["entities"],
        "drilldown": get_overperforming_channel_momentum_drilldown_config(
            channel=item["channel"]
        ),
    }
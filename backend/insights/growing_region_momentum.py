import pandas as pd

from backend.insights.insights_helper import build_filter_context, format_float, format_number, format_pct, get_last_full_month

# TODO: Replace these imports with your actual helper paths/names if different.
# These should be your existing app-standard metric functions.
from backend.metrics.monthly_metric_calculators import calculate_monthly_units
from backend.metrics.metric_growth_rates import add_abs_change_columns, add_additive_metric_3m, add_pct_change_columns, add_prior_month_columns, calculate_reorder_rate_3m, calculate_vpo_3m


REGION_COL = "state"
DEFAULT_LIMIT = 1

MIN_BUSINESS_SHARE_GAIN_TO_MENTION = 0.03
MIN_RECENT_BUSINESS_SHARE = 0.03
MIN_RECENT_UNITS = 25
MIN_UNIT_GROWTH_ABS = 25
MIN_UNIT_GROWTH_PCT = 0.15
MIN_VELOCITY_GROWTH_PCT = 0.05
MIN_REORDER_RATE_GROWTH_ABS = 0.02
MIN_UNIT_GROWTH_OUTPERFORMANCE_PCT = 0.05
MIN_VELOCITY_OUTPERFORMANCE_PCT = 0.03
MIN_REORDER_OUTPERFORMANCE_ABS = 0.01
MIN_DRIVER_SHARE = 0.50
MIN_DRIVER_UNIT_GROWTH = 25


def build_growing_region_momentum_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Builds one row per state for the latest full 3-month period vs the prior 3-month period.

    Assumes the dataframe has already been cleaned/normalized before it reaches the insight layer.
    Uses the existing l3m helper flow for units_3m, vpo_3m, and reorder_rate_3m comparisons.
    """

    if df is None or df.empty or REGION_COL not in df.columns:
        return pd.DataFrame()

    last_full_month = get_last_full_month()
    group_cols = [REGION_COL, "month_year"]
    total_group_cols = ["month_year"]

    units = calculate_monthly_units(df=df, group_cols=group_cols)
    units = add_additive_metric_3m(units, group_cols=group_cols, metric="units")
    units = add_prior_month_columns(units, group_cols=group_cols, metric="units", l3m=True)
    units = add_pct_change_columns(units, metric="units", l3m=True)
    units = add_abs_change_columns(units, metric="units", l3m=True)

    velocity = calculate_vpo_3m(df_filtered=df, df_full=df, group_cols=group_cols)
    velocity = add_prior_month_columns(velocity, group_cols=group_cols, metric="vpo", l3m=True)
    velocity = add_pct_change_columns(velocity, metric="vpo", l3m=True)
    velocity = add_abs_change_columns(velocity, metric="vpo", l3m=True)

    reorder = calculate_reorder_rate_3m(df_filtered=df, df_full=df, group_cols=group_cols)
    reorder = add_prior_month_columns(reorder, group_cols=group_cols, metric="reorder_rate", l3m=True)
    reorder = add_pct_change_columns(reorder, metric="reorder_rate", l3m=True)
    reorder = add_abs_change_columns(reorder, metric="reorder_rate", l3m=True)

    result = units[units["month_year"] == last_full_month][[REGION_COL, "units_3m", "units_l3m", "units_l3m_pct", "units_l3m_abs"]].rename(columns={"units_3m": "recent_3m_units", "units_l3m": "prior_3m_units", "units_l3m_pct": "unit_growth_pct", "units_l3m_abs": "unit_growth_abs"})
    result = result.merge(velocity[velocity["month_year"] == last_full_month][[REGION_COL, "vpo_3m", "vpo_l3m", "vpo_l3m_pct", "vpo_l3m_abs"]].rename(columns={"vpo_3m": "recent_3m_velocity", "vpo_l3m": "prior_3m_velocity", "vpo_l3m_pct": "velocity_growth_pct", "vpo_l3m_abs": "velocity_growth_abs"}), on=REGION_COL, how="outer")
    result = result.merge(reorder[reorder["month_year"] == last_full_month][[REGION_COL, "reorder_rate_3m", "reorder_rate_l3m", "reorder_rate_l3m_pct", "reorder_rate_l3m_abs"]].rename(columns={"reorder_rate_3m": "recent_3m_reorder_rate", "reorder_rate_l3m": "prior_3m_reorder_rate", "reorder_rate_l3m_pct": "reorder_rate_growth_pct", "reorder_rate_l3m_abs": "reorder_rate_growth_abs"}), on=REGION_COL, how="outer")
    result = result.fillna({"recent_3m_units": 0, "prior_3m_units": 0})

    total_units = calculate_monthly_units(df=df, group_cols=total_group_cols)
    total_units = add_additive_metric_3m(total_units, group_cols=total_group_cols, metric="units")
    total_units = add_prior_month_columns(total_units, group_cols=total_group_cols, metric="units", l3m=True)
    total_units = add_pct_change_columns(total_units, metric="units", l3m=True)

    total_velocity = calculate_vpo_3m(df_filtered=df, df_full=df, group_cols=total_group_cols)
    total_velocity = add_prior_month_columns(total_velocity, group_cols=total_group_cols, metric="vpo", l3m=True)
    total_velocity = add_pct_change_columns(total_velocity, metric="vpo", l3m=True)

    total_reorder = calculate_reorder_rate_3m(df_filtered=df, df_full=df, group_cols=total_group_cols)
    total_reorder = add_prior_month_columns(total_reorder, group_cols=total_group_cols, metric="reorder_rate", l3m=True)
    total_reorder = add_abs_change_columns(total_reorder, metric="reorder_rate", l3m=True)

    total_units_row = total_units[total_units["month_year"] == last_full_month]
    total_velocity_row = total_velocity[total_velocity["month_year"] == last_full_month]
    total_reorder_row = total_reorder[total_reorder["month_year"] == last_full_month]

    total_recent_units = total_units_row["units_3m"].iloc[0] if not total_units_row.empty else 0
    total_prior_units = total_units_row["units_l3m"].iloc[0] if not total_units_row.empty else 0
    total_unit_growth_pct = total_units_row["units_l3m_pct"].iloc[0] if not total_units_row.empty else pd.NA
    total_velocity_growth_pct = total_velocity_row["vpo_l3m_pct"].iloc[0] if not total_velocity_row.empty else pd.NA
    total_reorder_rate_growth_abs = total_reorder_row["reorder_rate_l3m_abs"].iloc[0] if not total_reorder_row.empty else pd.NA

    result["recent_business_share"] = result["recent_3m_units"] / total_recent_units if total_recent_units else pd.NA
    result["prior_business_share"] = result["prior_3m_units"] / total_prior_units if total_prior_units else pd.NA
    result["business_share_change_abs"] = result["recent_business_share"] - result["prior_business_share"]
    result["total_unit_growth_pct"] = total_unit_growth_pct
    result["total_velocity_growth_pct"] = total_velocity_growth_pct
    result["total_reorder_rate_growth_abs"] = total_reorder_rate_growth_abs
    result["unit_growth_outperformance_pct"] = result["unit_growth_pct"] - result["total_unit_growth_pct"]
    result["velocity_outperformance_pct"] = result["velocity_growth_pct"] - result["total_velocity_growth_pct"]
    result["reorder_rate_outperformance_abs"] = result["reorder_rate_growth_abs"] - result["total_reorder_rate_growth_abs"]

    return result


def analyze_growing_region_momentum(table: pd.DataFrame, limit: int = DEFAULT_LIMIT) -> pd.DataFrame | None:
    if table is None or table.empty:
        return None

    required_cols = [REGION_COL, "recent_3m_units", "unit_growth_abs", "unit_growth_pct", "recent_business_share", "velocity_growth_pct", "reorder_rate_growth_abs", "unit_growth_outperformance_pct", "velocity_outperformance_pct", "reorder_rate_outperformance_abs"]

    if any(col not in table.columns for col in required_cols):
        return None

    candidates = table[
        (table["recent_3m_units"].fillna(0) >= MIN_RECENT_UNITS)
        & (table["recent_business_share"].fillna(0) >= MIN_RECENT_BUSINESS_SHARE)
        & (table["unit_growth_abs"].fillna(0) >= MIN_UNIT_GROWTH_ABS)
        & (table["unit_growth_pct"].fillna(0) >= MIN_UNIT_GROWTH_PCT)
        & (table["velocity_growth_pct"].fillna(0) >= MIN_VELOCITY_GROWTH_PCT)
        & (table["reorder_rate_growth_abs"].fillna(0) >= MIN_REORDER_RATE_GROWTH_ABS)
        & (table["unit_growth_outperformance_pct"].fillna(0) >= MIN_UNIT_GROWTH_OUTPERFORMANCE_PCT)
        & (table["velocity_outperformance_pct"].fillna(0) >= MIN_VELOCITY_OUTPERFORMANCE_PCT)
        & (table["reorder_rate_outperformance_abs"].fillna(0) >= MIN_REORDER_OUTPERFORMANCE_ABS)
    ].copy()

    if candidates.empty:
        return None

    candidates["momentum_score"] = candidates["unit_growth_outperformance_pct"].fillna(0) + candidates["velocity_outperformance_pct"].fillna(0) + candidates["reorder_rate_outperformance_abs"].fillna(0) + candidates["recent_business_share"].fillna(0)

    return candidates.sort_values(["momentum_score", "unit_growth_abs", "recent_3m_units"], ascending=[False, False, False]).head(limit)


def normalize_growing_region_momentum_data(analyzed_table: pd.DataFrame, df: pd.DataFrame) -> dict | None:
    if analyzed_table is None or analyzed_table.empty:
        return None

    items = []

    for _, row in analyzed_table.iterrows():
        state = row[REGION_COL]
        state_df = df[df[REGION_COL] == state].copy()
        #state_table = build_growing_region_momentum_table(state_df)

        chain_driver = None
        sku_driver = None

        #if "chain" in state_df.columns:
        #    chain_table = create_growing_region_momentum_store_list(state_df, driver_col="chain")
        #    chain_table = chain_table[chain_table["unit_growth_abs"].fillna(0) >= MIN_DRIVER_UNIT_GROWTH].copy()
        #    if not chain_table.empty and chain_table.iloc[0]["growth_share"] >= MIN_DRIVER_SHARE:
        #        chain_driver = chain_table.iloc[0].to_dict()

        #if "sku" in state_df.columns:
        #    sku_table = create_growing_region_momentum_store_list(state_df, driver_col="sku")
        #    sku_table = sku_table[sku_table["unit_growth_abs"].fillna(0) >= MIN_DRIVER_UNIT_GROWTH].copy()
        #    if not sku_table.empty and sku_table.iloc[0]["growth_share"] >= MIN_DRIVER_SHARE:
        #        sku_driver = sku_table.iloc[0].to_dict()

        #growth_driver = "pods_and_velocity" if row.get("pod_growth_abs", 0) > 0 and row.get("velocity_growth_pct", 0) > 0 else "velocity" if row.get("velocity_growth_pct", 0) > 0 else "pods" if row.get("pod_growth_abs", 0) > 0 else "unit_growth"
        growth_driver = "velocity" if row.get("velocity_growth_pct", 0) > 0 else "unit_growth"

        item = {
            "state": state,
            "recent_3m_units": row.get("recent_3m_units"),
            "prior_3m_units": row.get("prior_3m_units"),
            "unit_growth_abs": row.get("unit_growth_abs"),
            "unit_growth_pct": row.get("unit_growth_pct"),
            "recent_business_share": row.get("recent_business_share"),
            "prior_business_share": row.get("prior_business_share"),
            "business_share_change_abs": row.get("business_share_change_abs"),
            #"recent_3m_pods": row.get("recent_3m_pods"),
            #"prior_3m_pods": row.get("prior_3m_pods"),
            #"pod_growth_abs": row.get("pod_growth_abs"),
            #"pod_growth_pct": row.get("pod_growth_pct"),
            "recent_3m_velocity": row.get("recent_3m_velocity"),
            "prior_3m_velocity": row.get("prior_3m_velocity"),
            "velocity_growth_pct": row.get("velocity_growth_pct"),
            "recent_3m_reorder_rate": row.get("recent_3m_reorder_rate"),
            "prior_3m_reorder_rate": row.get("prior_3m_reorder_rate"),
            "reorder_rate_growth_abs": row.get("reorder_rate_growth_abs"),
            "total_unit_growth_pct": row.get("total_unit_growth_pct"),
            "unit_growth_outperformance_pct": row.get("unit_growth_outperformance_pct"),
            "velocity_outperformance_pct": row.get("velocity_outperformance_pct"),
            "reorder_rate_outperformance_abs": row.get("reorder_rate_outperformance_abs"),
            "growth_driver": growth_driver,
            "top_chain_driver": chain_driver,
            "top_sku_driver": sku_driver,
        }

        item["metrics"] = {k: v for k, v in item.items() if k not in ["state", "growth_driver", "top_chain_driver", "top_sku_driver"]}
        item["entities"] = {"state": state, "chain": chain_driver.get("chain") if chain_driver else None, "sku": sku_driver.get("sku") if sku_driver else None}
        items.append(item)

    return {"items": items, "metrics": items[0]["metrics"] if items else {}, "entities": items[0]["entities"] if items else {}}



def describe_growing_region_momentum(data: dict | None, filters=None) -> dict | None:
    if data is None or not data.get("items"):
        return None

    item = data["items"][0]
    context_str, context_parts = build_filter_context(filters)

    state = item["state"]
    unit_growth_abs_fmt = format_number(item["unit_growth_abs"])
    recent_units_fmt = format_number(item["recent_3m_units"])
    prior_units_fmt = format_number(item["prior_3m_units"])
    unit_growth_pct_fmt = format_pct(item["unit_growth_pct"], signed=True)
    total_unit_growth_pct_fmt = format_pct(item["total_unit_growth_pct"], signed=True)
    unit_outperformance_fmt = format_pct(item["unit_growth_outperformance_pct"], signed=True)
    velocity_growth_pct_fmt = format_pct(item["velocity_growth_pct"], signed=True)
    reorder_growth_fmt = format_pct(item["reorder_rate_growth_abs"], decimals=1, signed=True)
    prior_share_fmt = format_pct(item["prior_business_share"])
    recent_share_fmt = format_pct(item["recent_business_share"])
    share_change_fmt = format_pct(item["business_share_change_abs"], decimals=1, signed=True)

    headline = f"{state} is gaining momentum."
    summary = f"{state}{context_str} grew by {unit_growth_abs_fmt} units ({unit_growth_pct_fmt}) over the prior 3 months, while velocity and reorder rate both improved."

    parts = [
        {"type": "chip", "value": state, "tone": "positive"},
        *context_parts,
        {"type": "text", "value": " grew by "},
        {"type": "chip", "value": unit_growth_abs_fmt, "tone": "positive"},
        {"type": "text", "value": " units ("},
        {"type": "chip", "value": unit_growth_pct_fmt, "tone": "positive"},
        {"type": "text", "value": ") over the prior 3 months, with velocity and reorder rate both improving."},
    ]

    outperformance_text = (
        f"The state is outperforming the broader filtered business: total units grew "
        f"{total_unit_growth_pct_fmt}, while {state} grew {unit_growth_pct_fmt}, "
        f"a gap of roughly {unit_outperformance_fmt}."
    )

    if (
        item.get("business_share_change_abs") is not None
        and pd.notna(item["business_share_change_abs"])
        and item["business_share_change_abs"] >= MIN_BUSINESS_SHARE_GAIN_TO_MENTION
    ):
        outperformance_text += (
            f" {state} also increased from {prior_share_fmt} to {recent_share_fmt} "
            f"of recent 3-month units, a {share_change_fmt} share gain."
        )
    else:
        outperformance_text += (
            f" {state} now represents about {recent_share_fmt} of recent 3-month units."
        )

    description = [
        {
            "type": "text",
            "value": f"{state} is emerging as a region to double down on{context_str}. Recent 3-month units increased from {prior_units_fmt} to {recent_units_fmt}, a gain of {unit_growth_abs_fmt} units ({unit_growth_pct_fmt}).",
        },
        {
            "type": "text",
            "value": outperformance_text,
        },
    ]

    #if item["growth_driver"] == "pods_and_velocity":
    #    description.append({"type": "text", "value": f"Growth is supported by both broader distribution and stronger velocity: active PODs increased by {format_number(item['pod_growth_abs'])} ({format_pct(item['pod_growth_pct'], signed=True)}), while velocity improved {velocity_growth_pct_fmt}."})
    if item["growth_driver"] == "velocity":
        description.append({"type": "text", "value": f"The gain appears primarily velocity-led, with velocity improving {velocity_growth_pct_fmt}."})
    #elif item["growth_driver"] == "pods":
    #    description.append({"type": "text", "value": f"The gain appears primarily distribution-led, with active PODs increasing by {format_number(item['pod_growth_abs'])} ({format_pct(item['pod_growth_pct'], signed=True)})."})

    description.append({"type": "text", "value": f"The growth is backed by healthier repeat behavior: reorder rate improved from {format_pct(item['prior_3m_reorder_rate'])} to {format_pct(item['recent_3m_reorder_rate'])} ({reorder_growth_fmt}), while velocity improved {velocity_growth_pct_fmt}."})

    if item.get("top_chain_driver"):
        description.append({"type": "text", "value": f"Growth is concentrated in {item['top_chain_driver']['chain']}, which contributed {format_number(item['top_chain_driver']['unit_growth_abs'])} units, or about {format_pct(item['top_chain_driver']['growth_share'])} of the state's positive unit gain."})

    if item.get("top_sku_driver"):
        description.append({"type": "text", "value": f"SKU-level growth is concentrated in {item['top_sku_driver']['sku']}, which contributed {format_number(item['top_sku_driver']['unit_growth_abs'])} units, or about {format_pct(item['top_sku_driver']['growth_share'])} of the state's positive unit gain."})

    description.append({"type": "text", "value": "This is a good region to review for repeatable expansion opportunities: identify the stores, chains, and SKUs creating the momentum, then look for nearby accounts where the same pattern can be extended."})

    return {"headline": headline, "summary": summary, "parts": parts, "description": description}


def create_growing_region_momentum_store_list(df: pd.DataFrame, analyzed_table: pd.DataFrame) -> pd.DataFrame:
    if analyzed_table is None or analyzed_table.empty:
        return pd.DataFrame()

    state = analyzed_table.iloc[0][REGION_COL]
    last_full_month = get_last_full_month()
    recent_months = [last_full_month - i for i in range(0, 3)]

    table = df[
        (df[REGION_COL] == state)
        & (df["month_year"].isin(recent_months))
    ].copy()

    if table.empty:
        return pd.DataFrame()

    store_cols = ["coded_customer", "chain", "dc", "city", "state"]
    existing_store_cols = [col for col in store_cols if col in table.columns]

    result = (
        table.groupby(existing_store_cols, as_index=False)
        .agg(recent_units=("units", "sum"))
        .sort_values("recent_units", ascending=False)
    )

    return result

def build_growing_region_momentum_insight(df: pd.DataFrame, filters=None, limit: int = DEFAULT_LIMIT):
    table = build_growing_region_momentum_table(df)
    analyzed = analyze_growing_region_momentum(table, limit=limit)
    data = normalize_growing_region_momentum_data(analyzed_table=analyzed, df=df)
    description = describe_growing_region_momentum(data=data, filters=filters)

    if data is None or description is None:
        return None

    item = data["items"][0]

    return {
        "type": "growing_region_momentum",
        "section": "where_to_double_down",
        **description,
        "metrics": item["metrics"],
        "entities": item["entities"],
        "drilldown": {"label": "View what's driving this region", "href": "/insights/growing_region_momentum"},
    }

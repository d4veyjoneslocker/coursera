import pandas as pd

from backend.insights.insights_helper import (
    build_filter_context,
    format_number,
    format_pct,
)

from backend.insights.diagnostics import (
    calculate_units_growth_decomposition_3m,
)


def _get_top_driver(
    df: pd.DataFrame,
    df_all_time: pd.DataFrame,
    group_col: str,
    impact_col: str,
    include_current_month: bool = False,
) -> dict | None:
    if group_col not in df.columns:
        return None

    table = calculate_units_growth_decomposition_3m(
        df_filtered=df,
        df_full=df_all_time,
        group_cols=[group_col, "month_year"],
        include_current_month=include_current_month,
    )

    if table is None or table.empty or impact_col not in table.columns:
        return None

    table = table[
        table[group_col].notna()
        & ~table[group_col].eq("CONFIDENTIAL")
        & table[impact_col].notna()
    ].copy()

    if table.empty:
        return None

    # Distribution-specific diagnostics
    if impact_col == "distribution_impact":
        table["pod_opportunity_change"] = (
            table["active_pods_current"]
            - table["active_pods_prior"]
        )

        total_pod_opportunity_change = (
            table["pod_opportunity_change"].sum()
        )

        table["share_of_pod_opportunity_change"] = (
            table["pod_opportunity_change"]
            / total_pod_opportunity_change
            if total_pod_opportunity_change != 0
            else None
        )

        table = table[
            table["pod_opportunity_change"].notna()
            & (table["pod_opportunity_change"] != 0)
        ].copy()

        if table.empty:
            return None

        row = table.sort_values(
            "pod_opportunity_change",
            key=lambda s: s.abs(),
            ascending=False,
        ).iloc[0]

        return row.to_dict()

    # Velocity-specific diagnostics
    table = table[
        table[impact_col].notna()
        & (table[impact_col] != 0)
    ].copy()

    if table.empty:
        return None

    row = table.sort_values(
        impact_col,
        key=lambda s: s.abs(),
        ascending=False,
    ).iloc[0]

    return row.to_dict()


def get_sales_change_driver_breakdown(
    df: pd.DataFrame,
    df_all_time: pd.DataFrame,
    include_current_month: bool = False,
    min_sku_share: float = 0.50,
    min_sku_pod_change: float = 10,
) -> dict:
    top_chain_distribution = _get_top_driver(
        df=df,
        df_all_time=df_all_time,
        group_col="chain",
        impact_col="distribution_impact",
        include_current_month=include_current_month,
    )

    top_chain_velocity = _get_top_driver(
        df=df,
        df_all_time=df_all_time,
        group_col="chain",
        impact_col="velocity_impact",
        include_current_month=include_current_month,
    )

    top_sku_distribution = _get_top_driver(
        df=df,
        df_all_time=df_all_time,
        group_col="sku",
        impact_col="distribution_impact",
        include_current_month=include_current_month,
    )

    include_sku_distribution = (
        top_sku_distribution is not None
        and abs(top_sku_distribution.get("pod_opportunity_change", 0))
        >= min_sku_pod_change
        and top_sku_distribution.get(
            "share_of_pod_opportunity_change",
            0,
        ) >= min_sku_share
    )

    return {
        "top_chain_distribution_driver": top_chain_distribution,
        "top_chain_velocity_driver": top_chain_velocity,
        "top_sku_distribution_driver": (
            top_sku_distribution if include_sku_distribution else None
        ),
    }


def build_sales_change_driver_table(
    df: pd.DataFrame,
    df_all_time: pd.DataFrame,
    include_current_month: bool = False,
) -> pd.DataFrame:
    return calculate_units_growth_decomposition_3m(
        df_filtered=df,
        df_full=df_all_time,
        group_cols=["month_year"],
        include_current_month=include_current_month,
    )


def analyze_sales_change_driver(
    table: pd.DataFrame,
    min_abs_unit_change: float = 1,
) -> pd.DataFrame | None:
    if table is None or table.empty:
        return None

    required_cols = [
        "units_current",
        "units_prior",
        "total_change",
        "distribution_share",
        "velocity_share",
        "primary_driver",
    ]

    if any(col not in table.columns for col in required_cols):
        return None

    table = table.copy()

    table = table[
        table["total_change"].notna()
        & (table["total_change"].abs() >= min_abs_unit_change)
    ].copy()

    if table.empty:
        return None

    return table.head(1)


def normalize_sales_change_driver_data(
    table: pd.DataFrame,
    df: pd.DataFrame,
    df_all_time: pd.DataFrame,
    include_current_month: bool = False,
) -> dict | None:
    if table is None or table.empty:
        return None

    row = table.iloc[0]

    total_change = row["total_change"]
    units_current = row["units_current"]
    units_prior = row["units_prior"]

    unit_change_pct = (
        total_change / units_prior
        if pd.notna(units_prior) and units_prior != 0
        else None
    )

    driver_breakdown = get_sales_change_driver_breakdown(
        df=df,
        df_all_time=df_all_time,
        include_current_month=include_current_month,
    )

    return {
        "units_current": units_current,
        "units_prior": units_prior,
        "total_change": total_change,
        "unit_change_pct": unit_change_pct,

        "active_pods_current": row.get("active_pods_current"),
        "active_pods_prior": row.get("active_pods_prior"),
        "vpo_current": row.get("vpo_current"),
        "vpo_prior": row.get("vpo_prior"),

        "distribution_impact": row.get("distribution_impact"),
        "velocity_impact": row.get("velocity_impact"),
        "distribution_share": row.get("distribution_share"),
        "velocity_share": row.get("velocity_share"),
        "primary_driver": row.get("primary_driver"),

        "driver_breakdown": driver_breakdown,

        "metrics": {
            **row.to_dict(),
            "driver_breakdown": driver_breakdown,
        },

        "entities": {},
    }


def describe_sales_change_driver(
    data: dict | None,
    filters=None,
) -> dict | None:
    if data is None:
        return None

    context_str, context_parts = build_filter_context(filters)

    units_current = data["units_current"]
    units_prior = data["units_prior"]
    total_change = data["total_change"]
    unit_change_pct = data["unit_change_pct"]

    distribution_share = data["distribution_share"]
    velocity_share = data["velocity_share"]
    primary_driver = data["primary_driver"]

    driver_breakdown = data.get("driver_breakdown") or {}

    top_chain_distribution = (
        driver_breakdown.get("top_chain_distribution_driver")
    )

    top_chain_velocity = (
        driver_breakdown.get("top_chain_velocity_driver")
    )

    top_sku_distribution = (
        driver_breakdown.get("top_sku_distribution_driver")
    )

    units_current_fmt = format_number(units_current)
    units_prior_fmt = format_number(units_prior)

    unit_change_pct_fmt = (
        format_pct(abs(unit_change_pct))
        if unit_change_pct is not None and pd.notna(unit_change_pct)
        else None
    )

    distribution_share_fmt = format_pct(abs(distribution_share))
    velocity_share_fmt = format_pct(abs(velocity_share))

    direction = "increased" if total_change > 0 else "declined"
    direction_noun = "growth" if total_change > 0 else "decline"
    tone = "positive" if total_change > 0 else "negative"

    primary_driver_label = (
        "active POD opportunities"
        if primary_driver == "distribution"
        else "VPO"
    )

    headline = f"Units {direction} vs the prior 3 months."

    if unit_change_pct_fmt:
        summary = (
            f"Units {direction} by {unit_change_pct_fmt}, "
            f"from {units_prior_fmt} to {units_current_fmt}. "
            f"The {direction_noun} was primarily driven by "
            f"{primary_driver_label}."
        )
    else:
        summary = (
            f"Units {direction} from {units_prior_fmt} "
            f"to {units_current_fmt}. "
            f"The {direction_noun} was primarily driven by "
            f"{primary_driver_label}."
        )

    parts = [
        {"type": "text", "value": "Units "},
        {"type": "chip", "value": direction, "tone": tone},
        {"type": "text", "value": " vs the prior 3 months"},
        *context_parts,
        {"type": "text", "value": "."},
    ]

    intro_value = (
        f"Units {direction} from {units_prior_fmt} in the prior "
        f"3-month period to {units_current_fmt} in the latest "
        f"3-month period."
    )

    if unit_change_pct_fmt:
        intro_value += (
            f" That is a {unit_change_pct_fmt} {direction_noun}."
        )

    driver_detail = ""

    if primary_driver == "distribution" and top_chain_distribution:
        chain = top_chain_distribution.get("chain")

        pod_change = top_chain_distribution.get(
            "pod_opportunity_change"
        )

        share = top_chain_distribution.get(
            "share_of_pod_opportunity_change"
        )

        if (
            chain is not None
            and pd.notna(pod_change)
            and pd.notna(share)
        ):
            driver_detail += (
                f" The largest chain-level distribution contributor "
                f"was {chain}, which added "
                f"{format_number(abs(pod_change))} active POD opportunities "
                f"and accounted for "
                f"{format_pct(abs(share))} of the total POD opportunity increase."
            )

        if top_sku_distribution:
            sku = top_sku_distribution.get("sku")

            sku_pod_change = top_sku_distribution.get(
                "pod_opportunity_change"
            )

            sku_share = top_sku_distribution.get(
                "share_of_pod_opportunity_change"
            )

            if (
                sku is not None
                and pd.notna(sku_pod_change)
                and pd.notna(sku_share)
            ):
                driver_detail += (
                    f" A meaningful SKU-level distribution driver "
                    f"was {sku}, which accounted for "
                    f"{format_pct(abs(sku_share))} of the total "
                    f"POD opportunity increase."
                )

    elif primary_driver == "velocity" and top_chain_velocity:
        chain = top_chain_velocity.get("chain")

        impact = top_chain_velocity.get("velocity_impact")

        if chain is not None and pd.notna(impact):
            driver_detail += (
                f" The largest chain-level VPO contributor "
                f"was {chain}, contributing about "
                f"{format_number(abs(impact))} units of VPO-driven impact."
            )

    driver_block = {
        "type": "text",
        "value": (
            f"The change was primarily driven by "
            f"{primary_driver_label}. "
            f"Active POD opportunities accounted for "
            f"{distribution_share_fmt} of the unit change, "
            f"while VPO accounted for "
            f"{velocity_share_fmt}."
            f"{driver_detail}"
        ),
    }

    description = [
        {"type": "text", "value": intro_value},
        driver_block,
    ]

    return {
        "headline": headline,
        "summary": summary,
        "parts": parts,
        "description": description,
    }


def build_sales_change_driver_insight(
    df: pd.DataFrame,
    df_all_time: pd.DataFrame,
    filters=None,
    include_current_month: bool = False,
):
    table = build_sales_change_driver_table(
        df=df,
        df_all_time=df_all_time,
        include_current_month=include_current_month,
    )

    analyzed = analyze_sales_change_driver(table=table)

    data = normalize_sales_change_driver_data(
        table=analyzed,
        df=df,
        df_all_time=df_all_time,
        include_current_month=include_current_month,
    )

    description = describe_sales_change_driver(
        data=data,
        filters=filters,
    )

    if data is None or description is None:
        return None

    return {
        "type": "sales_change_driver",
        "section": "what_changed",
        "priority": 10,

        **description,

        "metrics": data["metrics"],
        "entities": data["entities"],
    }
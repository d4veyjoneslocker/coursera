import pandas as pd

from backend.metrics.metric_helpers import clean_group_cols_new
from backend.metrics.metric_calculators import (
    calculate_units,
    calculate_active_pod_opportunities,
)


def fill_rate_metrics(
    df: pd.DataFrame,
    grain: list[str] | str | None = None,
) -> pd.DataFrame:
    """
    Calculate fill-rate metrics at any requested grain.

    Expected input columns:
        ordered_cases
        shipped_cases

    Example grains:
        None
        "chain"
        "sku"
        ["chain", "sku"]
        ["chain", "store"]
        ["month_year", "chain"]
        ["month_year", "chain", "sku"]

    Returns:
        ordered_cases
        shipped_cases
        unfilled_cases
        fill_rate
    """

    df = df.copy()

    # ---------------------------------------------------------
    # Normalize grain
    # ---------------------------------------------------------

    if grain is None:
        grain = []
    elif isinstance(grain, str):
        grain = [grain]

    # ---------------------------------------------------------
    # Validate
    # ---------------------------------------------------------

    required = {
        "ordered_cases",
        "shipped_cases",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    missing_grain = set(grain) - set(df.columns)

    if missing_grain:
        raise ValueError(
            f"Grain columns not found: {sorted(missing_grain)}"
        )

    # ---------------------------------------------------------
    # Aggregate
    # ---------------------------------------------------------

    if grain:
        result = (
            df.groupby(
                grain,
                dropna=False,
                as_index=False,
            )
            .agg(
                ordered_cases=("ordered_cases", "sum"),
                shipped_cases=("shipped_cases", "sum"),
            )
        )

    else:
        result = pd.DataFrame(
            {
                "ordered_cases": [df["ordered_cases"].sum()],
                "shipped_cases": [df["shipped_cases"].sum()],
            }
        )

    # ---------------------------------------------------------
    # Derived metrics
    # ---------------------------------------------------------

    result["unfilled_cases"] = (
        result["ordered_cases"]
        - result["shipped_cases"]
    )

    result["fill_rate"] = (
        result["shipped_cases"]
        / result["ordered_cases"]
    ).where(
        result["ordered_cases"] > 0
    )

    return result


def calculate_fill_rate(df, group_cols=None):
    group_cols = clean_group_cols_new(group_cols)

    if group_cols:
        result = (
            df.groupby(
                group_cols,
                as_index=False,
                dropna=False,
            )
            .agg(
                ordered_cases=("ordered_cases", "sum"),
                shipped_cases=("shipped_cases", "sum"),
            )
        )

        result["fill_rate"] = (
            result["shipped_cases"]
            / result["ordered_cases"].replace(0, pd.NA)
        )

        return result[group_cols + ["fill_rate"]]

    ordered_cases = df["ordered_cases"].sum()
    shipped_cases = df["shipped_cases"].sum()

    if ordered_cases == 0:
        return None

    return float(shipped_cases / ordered_cases)


def calculate_order_velocity(
    fill_rate_df,
    active_pods_df,
    group_cols=None,
):
    group_cols = clean_group_cols_new(group_cols)

    # Order VPO is only meaningful for PODs covered by
    # the fill-rate dataset.
    covered_active_pods = active_pods_df[
        active_pods_df["has_fill_rate_data"]
    ].copy()

    opportunities = calculate_active_pod_opportunities(
        active_pods_df=covered_active_pods,
        group_cols=group_cols,
    )

    # Reuse the canonical units calculator by temporarily
    # presenting ordered units as units.
    orders = fill_rate_df.rename(
        columns={"ordered_units": "units"}
    )

    units = calculate_units(
        orders,
        group_cols=group_cols,
    )

    if not group_cols:
        if opportunities == 0:
            return None

        return float(
            units
            / opportunities
            / 4
        )

    units = units.rename(
        columns={"units": "ordered_units"}
    )

    result = opportunities.merge(
        units,
        on=group_cols,
        how="left",
    )

    result["ordered_units"] = (
        result["ordered_units"]
        .fillna(0)
    )

    result["order_vpo"] = (
        result["ordered_units"]
        / result["active_pod_opportunities"].replace(0, pd.NA)
        / 4
    )

    return result[
        group_cols + ["order_vpo"]
    ]
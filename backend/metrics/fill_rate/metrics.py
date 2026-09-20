import pandas as pd


def fill_rate_metrics(
    df: pd.DataFrame,
    grain: list[str] | str | None = None,
) -> pd.DataFrame:
    """
    Calculate fill-rate metrics at any requested grain.

    Expected input columns:
        ordered
        shipped

    Example grains:
        None
        "chain"
        "sku"
        ["chain", "sku"]
        ["chain", "store"]
        ["month_year", "chain"]
        ["month_year", "chain", "sku"]

    Returns:
        cases_ordered
        cases_shipped
        cases_unfilled
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
    required = {"ordered", "shipped"}

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
                cases_ordered=("ordered", "sum"),
                cases_shipped=("shipped", "sum"),
            )
        )

    else:
        result = pd.DataFrame(
            {
                "cases_ordered": [df["ordered"].sum()],
                "cases_shipped": [df["shipped"].sum()],
            }
        )

    # ---------------------------------------------------------
    # Derived metrics
    # ---------------------------------------------------------
    result["cases_unfilled"] = (
        result["cases_ordered"]
        - result["cases_shipped"]
    )

    result["fill_rate"] = (
        result["cases_shipped"]
        / result["cases_ordered"]
    ).where(
        result["cases_ordered"] > 0
    )

    return result
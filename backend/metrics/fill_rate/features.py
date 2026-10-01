import pandas as pd


def build_fill_rate_features(
    kehe_fill_rate_df: pd.DataFrame,
    features_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build monthly KeHE fill-rate features and attach DC.

    Fill-rate input expected with:
        - month_year
        - chain
        - distributor
        - customer_name
        - chain_store_key
        - sku
        - ordered_cases
        - ordered_units
        - shipped_cases
        - shipped_units

    Output grain:
        month_year x chain x customer_name x chain_store_key x sku

    Features:
        - ordered_cases
        - ordered_units
        - shipped_cases
        - shipped_units
        - fill_rate
        - dc
    """

    df = kehe_fill_rate_df.copy()

    # ---------------------------------------------------------
    # Aggregate to monthly store x SKU grain
    # ---------------------------------------------------------
    features = (
        df.groupby(
            [
                "month_year",
                "chain",
                "distributor",
                "customer_name",
                "chain_store_key",
                "sku",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(
            ordered_cases=("ordered_cases", "sum"),
            ordered_units=("ordered_units", "sum"),
            shipped_cases=("shipped_cases", "sum"),
            shipped_units=("shipped_units", "sum"),
        )
    )

    features["fill_rate"] = (
        features["shipped_cases"] / features["ordered_cases"]
    ).where(features["ordered_cases"] > 0)

    # ---------------------------------------------------------
    # Build monthly store x SKU -> DC lookup
    # ---------------------------------------------------------
    store_dc_lookup = (
        features_df.loc[
            features_df["distributor"].eq("KEHE"),
            [
                "distributor",
                "month_year",
                "chain_store_key",
                "sku",
                "dc",
            ],
        ]
        .dropna(
            subset=[
                "chain_store_key",
                "dc",
            ]
        )
        .drop_duplicates()
    )

    # ---------------------------------------------------------
    # Validate one DC per month x store x SKU
    # ---------------------------------------------------------
    conflicts = (
        store_dc_lookup
        .groupby(
            [
                "distributor",
                "month_year",
                "chain_store_key",
                "sku",
            ],
            dropna=False,
        )["dc"]
        .nunique()
    )

    conflicts = conflicts[conflicts > 1]

    if not conflicts.empty:
        raise ValueError(
            "Multiple DCs found for the same "
            "distributor/month/store/SKU:\n"
            f"{conflicts.to_string()}"
        )

    # ---------------------------------------------------------
    # Match each fill-rate row to the most recent Full POD DC
    # for the same distributor x store x SKU.
    #
    # Exact month is used when available. Otherwise, use the
    # most recent prior Full POD month. Never look forward.
    # ---------------------------------------------------------

    left = features.copy()
    right = store_dc_lookup.copy()

    # merge_asof needs a sortable timestamp rather than Period
    left["_match_month"] = left["month_year"].dt.to_timestamp()
    right["_match_month"] = right["month_year"].dt.to_timestamp()

    # Preserve the original fill-rate row order
    left["_row_order"] = range(len(left))

    # merge_asof requires the date key to be sorted
    left = left.sort_values("_match_month")
    right = right.sort_values("_match_month")

    result = pd.merge_asof(
        left,
        right[
            [
                "distributor",
                "chain_store_key",
                "sku",
                "_match_month",
                "dc",
            ]
        ],
        on="_match_month",
        by=[
            "distributor",
            "chain_store_key",
            "sku",
        ],
        direction="backward",
        allow_exact_matches=True,
    )

    result = (
        result
        .sort_values("_row_order")
        .drop(
            columns=[
                "_match_month",
                "_row_order",
            ]
        )
        .reset_index(drop=True)
    )

    return result
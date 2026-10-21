import pandas as pd


def build_launch_tracking_table(
    active_pods_df: pd.DataFrame,
    fill_rate_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build monthly store x SKU launch tracking state.

    Grain:
        month_year x distributor x chain_store_key x sku
    """

    keys = [
        "month_year",
        "distributor",
        "chain_store_key",
        "sku",
    ]

    # Only stores with a valid chain_store_key
    table = active_pods_df[
        active_pods_df["chain_store_key"].notna()
    ][
        keys
        + [
            "pod_helper",
            "coded_customer",
            "chain",
            "dc",
            "channel",
            "state",
            "could_reorder",
        ]
    ].copy()

    # Launch month = first month this POD appears
    launch_months = (
        table
        .groupby("pod_helper", as_index=False)["month_year"]
        .min()
        .rename(columns={"month_year": "launch_month"})
    )

    table = table.merge(
        launch_months,
        on="pod_helper",
        how="left",
    )

    # Add fill-rate data
    fill = fill_rate_df[
        fill_rate_df["chain_store_key"].notna()
    ][
        keys
        + [
            "ordered_cases",
            "ordered_units",
            "shipped_cases",
            "shipped_units",
            "fill_rate",
        ]
    ].copy()

    table = table.merge(
        fill,
        on=keys,
        how="left",
    )

    # Order / reorder state comes from fill-rate data
    table["ordered"] = (table["ordered_cases"].gt(0))

    table["reorder_flag"] = (
        table["could_reorder"]
        & table["ordered"]
    )

    # Reorder fulfillment state
    table["reorder_unfulfilled"] = (
        table["reorder_flag"]
        & table["shipped_cases"].eq(0)
    )

    table["reorder_underfilled"] = (
        table["reorder_flag"]
        & table["shipped_cases"].gt(0)
        & table["shipped_cases"].lt(table["ordered_cases"])
    )

    table["reorder_fulfilled"] = (
        table["reorder_flag"]
        & table["shipped_cases"].ge(table["ordered_cases"])
    )

    table["unfulfilled_cases"] = (
        table["ordered_cases"]
        - table["shipped_cases"]
    ).clip(lower=0)

    table["unfulfilled_units"] = (
        table["ordered_units"]
        - table["shipped_units"]
    ).clip(lower=0)

    return (
        table
        .sort_values(
            [
                "month_year",
                "chain",
                "chain_store_key",
                "sku",
            ]
        )
        .reset_index(drop=True)
    )
import pandas as pd


def build_reorder_fulfillment_insight(
    launch_tracking_df: pd.DataFrame,
    launch_month,
    chain: str | None = None,
) -> dict:
    """
    Analyze reorder behavior for a recent launch and return every
    store that placed a reorder but received none of it.
    """

    launch_month = pd.Period(launch_month, freq="M")

    # ---------------------------------------------------------
    # Get placements from this launch
    # ---------------------------------------------------------

    launch_stores = launch_tracking_df[
        launch_tracking_df["launch_month"].eq(launch_month)
    ].copy()

    if chain is not None:
        launch_stores = launch_stores[
            launch_stores["chain"].eq(chain)
        ].copy()

    # ---------------------------------------------------------
    # Reorder rate
    # ---------------------------------------------------------

    placements = (
        launch_stores[
            [
                "chain_store_key",
                "sku",
                "reorder_flag",
            ]
        ]
        .drop_duplicates()
    )

    total_placements = len(placements)

    reordered_placements = (
        placements["reorder_flag"]
        .sum()
    )

    reorder_rate = (
        reordered_placements / total_placements
        if total_placements
        else 0
    )

    # ---------------------------------------------------------
    # Stores that appear not to have reordered, but actually
    # placed an order with KeHE and received nothing
    # ---------------------------------------------------------

    unfulfilled_reorders = launch_stores[
        (~launch_stores["reorder_flag"])
        & launch_stores["ordered_cases"].gt(0)
        & launch_stores["shipped_cases"].eq(0)
    ].copy()

    unfulfilled_reorders = (
        unfulfilled_reorders[
            [
                "month_year",
                "chain",
                "coded_customer",
                "chain_store_key",
                "sku",
                "dc",
                "state",
                "ordered_cases",
                "shipped_cases",
                "unfulfilled_cases",
                "fill_rate",
            ]
        ]
        .sort_values(
            [
                "chain",
                "sku",
                "ordered_cases",
            ],
            ascending=[
                True,
                True,
                False,
            ],
        )
        .reset_index(drop=True)
    )

    return {
        "launch_month": launch_month,
        "total_placements": total_placements,
        "reordered_placements": int(reordered_placements),
        "reorder_rate": reorder_rate,
        "unfulfilled_reorder_placements": len(
            unfulfilled_reorders
        ),
        "unfulfilled_reorders": unfulfilled_reorders,
    }

if __name__ == "__main__":
    from pathlib import Path

    from backend.insights.launch_tracking.launch_helpers import (
        build_launch_tracking_table,
    )

    org_id = "67a96381-5014-4a9b-bfe8-a14e6da5affe"

    data_dir = Path("backend/data") / org_id

    active_pods_df = pd.read_parquet(
        data_dir / "active_pods_df.parquet"
    )

    fill_rate_df = pd.read_parquet(
        data_dir / "fill_rate_df.parquet"
    )

    launch_tracking_df = build_launch_tracking_table(
        active_pods_df=active_pods_df,
        fill_rate_df=fill_rate_df,
    )

    launch_tracking_df.to_csv(
        data_dir / "launch_tracking.csv",
        index=False,
    )

    print(
        f"Saved {len(launch_tracking_df):,} rows to "
        f"{data_dir / 'launch_tracking.csv'}"
    )
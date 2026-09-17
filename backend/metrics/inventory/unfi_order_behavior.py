import numpy as np
import pandas as pd
from pathlib import Path

from backend.transforms.inventory.unfi import transform_unfi_purchase_orders


BASE_DIR = Path(__file__).resolve().parents[2]
ORG_ID = "default_org"

PO_PATH = (
    BASE_DIR
    / "data"
    / ORG_ID
    / "raw"
    / "inventory"
    / "unfi"
    / "Purchase Orders.csv"
)


def calculate_unfi_recent_order_behavior(
    purchase_orders: pd.DataFrame,
    recent_orders: int = 5,
    min_sku_intervals: int = 3,
) -> pd.DataFrame:
    """
    Summarize recent recurring UNFI PO behavior by DC × SKU.

    Quantity:
        Excludes the first observed PO, then uses up to the 5 most
        recent recurring PO quantities.

    Cadence:
        Measures prior PO received date -> current PO create date.

        The first observed cadence (PO #1 receipt -> PO #2 creation)
        is excluded because it may represent the transition from
        initial load-in to normal replenishment.

        Therefore cadence begins with:
            PO #2 receipt -> PO #3 creation

    Cadence hierarchy:
        3+ usable DC × SKU intervals -> DC × SKU median
        1-2 usable DC × SKU intervals -> DC median
        0 usable DC × SKU intervals -> UNFI median
    """

    df = purchase_orders.copy()

    df["po_create_date"] = pd.to_datetime(
        df["po_create_date"], errors="coerce"
    ).dt.normalize()

    df["received_date"] = pd.to_datetime(
        df["received_date"], errors="coerce"
    ).dt.normalize()

    df["order_cases"] = pd.to_numeric(
        df["original_quantity_cases"], errors="coerce"
    )

    df = df.dropna(
        subset=["dc", "sku", "po_create_date", "order_cases"]
    ).copy()

    # Sequence using ALL observed history.
    df = df.sort_values(
        ["dc", "sku", "po_create_date", "po_number"]
    ).copy()

    df["po_sequence_observed_history"] = (
        df.groupby(["dc", "sku"]).cumcount() + 1
    )

    # Attach prior PO receipt before filtering.
    df["prior_po_received_date"] = (
        df.groupby(["dc", "sku"])["received_date"].shift(1)
    )

    df["days_from_prior_delivery_to_order"] = (
        df["po_create_date"] - df["prior_po_received_date"]
    ).dt.days

    # -----------------------------
    # QUANTITY HISTORY
    # -----------------------------
    # Exclude PO #1, then take last N recurring orders.
    recurring_orders = df.loc[
        df["po_sequence_observed_history"] > 1
    ].copy()

    recent_quantity = (
        recurring_orders
        .groupby(["dc", "sku"], group_keys=False)
        .tail(recent_orders)
        .copy()
    )

    # -----------------------------
    # CADENCE HISTORY
    # -----------------------------
    # Exclude:
    # PO #1 itself
    # PO #1 receipt -> PO #2 creation
    #
    # First usable cadence is:
    # PO #2 receipt -> PO #3 creation
    recurring_cadence = df.loc[
        df["po_sequence_observed_history"] > 2
    ].copy()

    # Keep cadence associated with the same recent-order horizon.
    recent_cadence = (
        recurring_cadence
        .groupby(["dc", "sku"], group_keys=False)
        .tail(max(recent_orders - 1, 1))
        .copy()
    )

    recent_cadence = recent_cadence.dropna(
        subset=["days_from_prior_delivery_to_order"]
    ).copy()

    # -----------------------------
    # FALLBACK CADENCE BENCHMARKS
    # -----------------------------
    # These pools already exclude initial load-in behavior.

    dc_cadence = (
        recent_cadence
        .groupby("dc")["days_from_prior_delivery_to_order"]
        .median()
        .rename("dc_median_delivery_to_order_days")
    )

    unfi_cadence = (
        recent_cadence["days_from_prior_delivery_to_order"].median()
        if not recent_cadence.empty
        else np.nan
    )

    # -----------------------------
    # DC × SKU OUTPUT
    # -----------------------------
    rows = []

    for (dc, sku), quantity_group in recent_quantity.groupby(["dc", "sku"]):

        quantity_group = quantity_group.sort_values(
            "po_create_date"
        ).copy()

        cadence_group = recent_cadence.loc[
            (recent_cadence["dc"] == dc)
            & (recent_cadence["sku"] == sku)
        ].sort_values("po_create_date").copy()

        dates = quantity_group["po_create_date"].tolist()
        quantities = quantity_group["order_cases"].tolist()

        cadence_values = (
            cadence_group["days_from_prior_delivery_to_order"]
            .tolist()
        )

        sku_interval_count = len(cadence_values)

        sku_median_cadence = (
            np.median(cadence_values)
            if cadence_values
            else np.nan
        )

        dc_median_cadence = (
            dc_cadence.get(dc, np.nan)
        )

        if (
            sku_interval_count >= min_sku_intervals
            and pd.notna(sku_median_cadence)
        ):
            selected_cadence = sku_median_cadence
            cadence_source = "dc_sku_recent"

        elif pd.notna(dc_median_cadence):
            selected_cadence = dc_median_cadence
            cadence_source = "dc_recent"

        else:
            selected_cadence = unfi_cadence
            cadence_source = "unfi_recent"

        cadence_mean = (
            np.mean(cadence_values)
            if cadence_values
            else np.nan
        )

        cadence_std = (
            np.std(cadence_values, ddof=1)
            if len(cadence_values) > 1
            else np.nan
        )

        cadence_cv = (
            cadence_std / abs(cadence_mean)
            if pd.notna(cadence_mean)
            and cadence_mean != 0
            and pd.notna(cadence_std)
            else np.nan
        )

        quantity_mean = (
            np.mean(quantities)
            if quantities
            else np.nan
        )

        quantity_std = (
            np.std(quantities, ddof=1)
            if len(quantities) > 1
            else np.nan
        )

        quantity_cv = (
            quantity_std / quantity_mean
            if pd.notna(quantity_mean)
            and quantity_mean != 0
            and pd.notna(quantity_std)
            else np.nan
        )

        rows.append(
            {
                "dc": dc,
                "sku": sku,

                "recent_order_count": len(quantity_group),
                "recent_interval_count": sku_interval_count,

                "last_po_date": quantity_group["po_create_date"].max(),

                "recent_po_dates": dates,
                "recent_order_cases": quantities,
                "recent_delivery_to_order_days": cadence_values,

                "median_recent_order_cases": (
                    np.median(quantities)
                    if quantities
                    else np.nan
                ),

                "sku_median_delivery_to_order_days":
                    sku_median_cadence,

                "dc_median_delivery_to_order_days":
                    dc_median_cadence,

                "unfi_median_delivery_to_order_days":
                    unfi_cadence,

                "selected_delivery_to_order_days":
                    selected_cadence,

                "cadence_source":
                    cadence_source,

                "cadence_cv":
                    cadence_cv,

                "order_quantity_cv":
                    quantity_cv,
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values(["dc", "sku"])
        .reset_index(drop=True)
    )


def test_unfi_recent_order_behavior():

    print("\n=== UNFI RECENT ORDER BEHAVIOR TEST ===")

    raw = pd.read_csv(PO_PATH)

    purchase_orders = transform_unfi_purchase_orders(
        raw,
        org_id=ORG_ID,
    )

    behavior = calculate_unfi_recent_order_behavior(
        purchase_orders,
        recent_orders=5,
        min_sku_intervals=3,
    )

    print(f"\nPO rows: {len(purchase_orders):,}")
    print(f"DC × SKU combinations: {len(behavior):,}")

    print("\nRecent recurring order behavior:")
    print(
        behavior[
            [
                "dc",
                "sku",
                "recent_order_count",
                "recent_interval_count",
                "recent_order_cases",
                "recent_delivery_to_order_days",
                "median_recent_order_cases",
                "sku_median_delivery_to_order_days",
                "dc_median_delivery_to_order_days",
                "unfi_median_delivery_to_order_days",
                "selected_delivery_to_order_days",
                "cadence_source",
            ]
        ].to_string(index=False)
    )

    print("\nCadence source counts:")
    print(
        behavior["cadence_source"]
        .value_counts(dropna=False)
        .to_string()
    )

    print("\nSelected cadence summary:")
    print(
        behavior["selected_delivery_to_order_days"]
        .describe()
        .to_string()
    )

    print("\nOrder quantity summary:")
    print(
        behavior["median_recent_order_cases"]
        .describe()
        .to_string()
    )

    return behavior


if __name__ == "__main__":
    test_unfi_recent_order_behavior()
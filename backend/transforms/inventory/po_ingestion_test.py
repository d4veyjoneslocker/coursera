from pathlib import Path

import pandas as pd

from backend.transforms.inventory.unfi import (
    transform_unfi_purchase_orders,
    transform_unfi_projected_orders,
)
from backend.transforms.inventory.kehe import transform_kehe_order_projections


BASE_DIR = Path(__file__).resolve().parents[2]
ORG_DIR = BASE_DIR / "data" / "default_org"

UNFI_RAW_DIR = ORG_DIR / "raw" / "inventory" / "unfi"
KEHE_RAW_DIR = ORG_DIR / "raw" / "inventory" / "kehe"

OUTPUT_DIR = ORG_DIR / "processed" / "inventory"

ORG_ID = "default_org"


# =============================================================================
# UNFI PURCHASE ORDERS
# =============================================================================

def test_unfi_purchase_orders() -> pd.DataFrame:
    print("\n" + "=" * 80)
    print("UNFI PURCHASE ORDERS")
    print("=" * 80)

    path = UNFI_RAW_DIR / "Purchase Orders.csv"

    print(f"Path: {path}")
    print(f"Exists: {path.exists()}")

    raw = pd.read_csv(path)

    print(f"\nRaw rows: {len(raw):,}")
    print(f"Raw columns: {len(raw.columns):,}")

    transformed = transform_unfi_purchase_orders(raw, org_id=ORG_ID)

    print(f"\nTransformed rows: {len(transformed):,}")
    print(f"Transformed columns: {len(transformed.columns):,}")

    print("\nColumns:")
    print(transformed.columns.tolist())

    print("\nSample:")
    print(transformed.head(10).to_string(index=False))

    duplicate_count = transformed.duplicated(
        subset=["po_number", "dc", "upc"]
    ).sum()

    print("\nDuplicate PO × DC × UPC rows:")
    print(duplicate_count)

    print("\nPO status counts:")
    print(transformed["po_status"].value_counts(dropna=False))

    print("\nDC counts:")
    print(transformed["dc"].value_counts().sort_index())

    return transformed


# =============================================================================
# UNFI PROJECTED ORDERS
# =============================================================================

def test_unfi_projected_orders() -> pd.DataFrame:
    print("\n" + "=" * 80)
    print("UNFI PROJECTED ORDERS")
    print("=" * 80)

    path = UNFI_RAW_DIR / "Projected Orders Detail.csv"

    print(f"Path: {path}")
    print(f"Exists: {path.exists()}")

    raw = pd.read_csv(path)

    print(f"\nRaw rows: {len(raw):,}")
    print(f"Raw columns: {len(raw.columns):,}")

    transformed = transform_unfi_projected_orders(
        raw,
        org_id=ORG_ID,
    )

    print(f"\nTransformed rows: {len(transformed):,}")
    print(f"Transformed columns: {len(transformed.columns):,}")

    print("\nColumns:")
    print(transformed.columns.tolist())

    print("\nSample:")
    print(transformed.head(10).to_string(index=False))

    duplicate_count = transformed.duplicated(
        subset=["projected_order_date", "dc", "upc"]
    ).sum()

    print("\nDuplicate projected date × DC × UPC rows:")
    print(duplicate_count)

    print("\nDC counts:")
    print(transformed["dc"].value_counts().sort_index())

    print("\nProjected order date range:")
    print(
        transformed["projected_order_date"].min(),
        "→",
        transformed["projected_order_date"].max(),
    )

    print("\nProjected cases summary:")
    print(transformed["projected_order_cases"].describe())

    print("\nRows with projected orders > 0:")
    print((transformed["projected_order_cases"] > 0).sum())

    combo_summary = (
        transformed.groupby(["dc", "sku"])
        .agg(
            projected_events=(
                "projected_order_cases",
                lambda x: (x > 0).sum(),
            ),
            projected_cases=("projected_order_cases", "sum"),
        )
        .reset_index()
    )

    print("\nDC × SKU projection summary:")
    print(combo_summary.to_string(index=False))

    print(
        "\nDC-SKU combinations with at least one projected order:",
        (combo_summary["projected_events"] > 0).sum(),
    )

    print(
        "DC-SKU combinations with NO projected orders:",
        (combo_summary["projected_events"] == 0).sum(),
    )

    return transformed


# =============================================================================
# KEHE ORDER PROJECTIONS
# =============================================================================

def test_kehe_order_projections() -> pd.DataFrame:
    print("\n" + "=" * 80)
    print("KEHE ORDER PROJECTIONS")
    print("=" * 80)

    path = KEHE_RAW_DIR / "Order Projections Report.csv"

    print(f"Path: {path}")
    print(f"Exists: {path.exists()}")

    raw = pd.read_csv(path)

    print(f"\nRaw rows: {len(raw):,}")
    print(f"Raw columns: {len(raw.columns):,}")

    projection_as_of_date = "2026-09-14"

    transformed = transform_kehe_order_projections(
        raw,
        org_id=ORG_ID,
        projection_as_of_date=projection_as_of_date,
    )

    print(f"\nTransformed rows: {len(transformed):,}")
    print(f"Transformed columns: {len(transformed.columns):,}")

    print("\nColumns:")
    print(transformed.columns.tolist())

    print("\nSample:")
    print(transformed.head(10).to_string(index=False))

    duplicate_count = transformed.duplicated(
        subset=[
            "projection_as_of_date",
            "projected_order_date",
            "dc",
            "upc",
        ]
    ).sum()

    print("\nDuplicate snapshot × projected week × DC × UPC rows:")
    print(duplicate_count)

    print("\nDC counts:")
    print(transformed["dc"].value_counts().sort_index())

    print("\nProjected order date range:")
    print(
        transformed["projected_order_date"].min(),
        "→",
        transformed["projected_order_date"].max(),
    )

    print("\nProjected units summary:")
    print(transformed["projected_order_units"].describe())

    print("\nRows with projected orders > 0:")
    print((transformed["projected_order_units"] > 0).sum())

    combo_summary = (
        transformed.groupby(["dc", "sku"])
        .agg(
            projected_events=(
                "projected_order_units",
                lambda x: (x > 0).sum(),
            ),
            projected_units=("projected_order_units", "sum"),
        )
        .reset_index()
    )

    print("\nDC × SKU projection summary:")
    print(combo_summary.to_string(index=False))

    print(
        "\nDC-SKU combinations with at least one projected order:",
        (combo_summary["projected_events"] > 0).sum(),
    )

    print(
        "DC-SKU combinations with NO projected orders:",
        (combo_summary["projected_events"] == 0).sum(),
    )

    return transformed


# =============================================================================
# MAIN
# =============================================================================

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    unfi_purchase_orders = test_unfi_purchase_orders()
    unfi_projected_orders = test_unfi_projected_orders()
    kehe_order_projections = test_kehe_order_projections()

    unfi_purchase_orders.to_parquet(
        OUTPUT_DIR / "unfi_purchase_orders.parquet",
        index=False,
    )

    unfi_projected_orders.to_parquet(
        OUTPUT_DIR / "unfi_projected_orders.parquet",
        index=False,
    )

    kehe_order_projections.to_parquet(
        OUTPUT_DIR / "kehe_order_projections.parquet",
        index=False,
    )

    print("\n" + "=" * 80)
    print("OUTPUT FILES")
    print("=" * 80)

    print(OUTPUT_DIR / "unfi_purchase_orders.parquet")
    print(OUTPUT_DIR / "unfi_projected_orders.parquet")
    print(OUTPUT_DIR / "kehe_order_projections.parquet")


if __name__ == "__main__":
    main()
from pathlib import Path

import pandas as pd

from backend.transforms.inventory.kehe import (
    transform_kehe_inventory,
)
from backend.transforms.inventory.unfi import (
    transform_unfi_inventory,
)


ORG_ID = "default_org"

DATA_DIR = Path("backend/data") / ORG_ID

INVENTORY_RAW_DIR = (
    DATA_DIR
    / "raw"
    / "inventory"
)

KEHE_RAW_PATH = (
    INVENTORY_RAW_DIR
    / "kehe_inventory_inspection.csv"
)

UNFI_RAW_PATH = (
    INVENTORY_RAW_DIR
    / "unfi_inventory_inspection.csv"
)

OUTPUT_PATH = DATA_DIR / "inventory_combined.parquet"
OUTPUT_CSV_PATH = DATA_DIR / "inventory_combined.csv"


def main():

    # -----------------------------
    # Load local inventory files
    # -----------------------------
    print("Loading inventory files...")

    kehe_raw = pd.read_csv(KEHE_RAW_PATH)
    unfi_raw = pd.read_csv(UNFI_RAW_PATH)

    print(f"KeHE raw: {len(kehe_raw):,} rows")
    print(f"UNFI raw: {len(unfi_raw):,} rows")

    # -----------------------------
    # Transform each distributor
    # -----------------------------
    print("\nTransforming inventory...")

    kehe_clean = transform_kehe_inventory(
        kehe_raw,
        org_id=ORG_ID,
    )

    unfi_clean = transform_unfi_inventory(
        unfi_raw,
        org_id=ORG_ID,
    )

    print(f"KeHE transformed: {len(kehe_clean):,} rows")
    print(f"UNFI transformed: {len(unfi_clean):,} rows")

    # -----------------------------
    # Check schemas
    # -----------------------------
    print("\nKeHE columns:")
    print(kehe_clean.columns.tolist())

    print("\nUNFI columns:")
    print(unfi_clean.columns.tolist())

    kehe_only = set(kehe_clean.columns) - set(unfi_clean.columns)
    unfi_only = set(unfi_clean.columns) - set(kehe_clean.columns)

    if kehe_only:
        print("\n⚠️ Columns only in KeHE:")
        print(sorted(kehe_only))

    if unfi_only:
        print("\n⚠️ Columns only in UNFI:")
        print(sorted(unfi_only))

    if not kehe_only and not unfi_only:
        print("\n✅ KeHE and UNFI schemas match")

    # -----------------------------
    # Combine distributors
    # -----------------------------
    inventory = pd.concat(
        [kehe_clean, unfi_clean],
        ignore_index=True,
    )

    print(f"\nCombined inventory: {len(inventory):,} rows")

    # -----------------------------
    # Quick inspection
    # -----------------------------
    print("\nCombined columns:")
    print(inventory.columns.tolist())

    print("\nSample:")
    print(inventory.head())

    # -----------------------------
    # Save locally
    # -----------------------------
    # -----------------------------
# Save locally
# -----------------------------
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    inventory.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    inventory.to_csv(
        OUTPUT_CSV_PATH,
        index=False,
    )

    print("\n✅ Saved combined inventory to:")
    print(OUTPUT_PATH)
    print(OUTPUT_CSV_PATH)


if __name__ == "__main__":
    main()
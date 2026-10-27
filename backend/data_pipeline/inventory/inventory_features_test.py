from pathlib import Path
import pandas as pd

from backend.metrics.inventory.features import add_inventory_features


ORG_ID = "67a96381-5014-4a9b-bfe8-a14e6da5affe"
DATA_DIR = Path("backend/data") / ORG_ID

INVENTORY_PATH = DATA_DIR / "inventory_combined.parquet"
ACTIVE_PODS_PATH = DATA_DIR / "active_pods_df.parquet"
FEATURES_PATH = DATA_DIR / "processed" / "features_df.parquet"
OUTPUT_PATH = DATA_DIR / "inventory_features_test.csv"


def main():
    print("Loading data...")

    inventory_df = pd.read_parquet(INVENTORY_PATH)
    active_pods_df = pd.read_parquet(ACTIVE_PODS_PATH)
    features_df = pd.read_parquet(FEATURES_PATH)

    print(f"Inventory rows: {len(inventory_df):,}")
    print(f"Active POD rows: {len(active_pods_df):,}")
    print(f"Sales feature rows: {len(features_df):,}")

    print("\nAdding inventory features...")

    result = add_inventory_features(
        inventory_df,
        active_pods_df,
        features_df,
    )

    result.to_csv(OUTPUT_PATH, index=False)

    print(f"\n✅ Inventory features complete: {len(result):,} rows")
    print(f"Saved to: {OUTPUT_PATH}")

    print("\nSample:")
    print(
        result[
            [
                "distributor",
                "dc",
                "sku",
                "quantity_on_hand_units",
                "quantity_on_purchase_order_units",
                "dc_weekly_velocity",
                "calculated_weeks_on_hand",
                "is_out_of_stock",
                "is_low_inventory",
                "has_open_po",
                "provisional_store_count",
                "has_provisional_velocity",
            ]
        ].head(20)
    )


if __name__ == "__main__":
    main()
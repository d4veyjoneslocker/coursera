from pathlib import Path

BASE_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def get_inventory_file_paths(org_id: str, distributor: str):
    base = BASE_DATA_DIR / org_id

    return {
        "raw_new_month": base / "raw" / "inventory" / distributor / f"{distributor}_inventory_new.csv",
        "raw_master": base / "raw" / "inventory" / distributor / "raw_master.csv",
        "raw_master_previous": base / "raw" / "inventory" / distributor / "raw_master_previous.csv",

        "processed_current": base / "processed_sources" / f"{distributor}_inventory_processed.parquet",
        "processed_previous": base / "processed_sources" / f"{distributor}_inventory_processed_previous.parquet",

        "inventory_current": base / "processed" / "inventory_df.parquet",
    }
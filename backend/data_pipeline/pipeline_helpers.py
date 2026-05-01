from pathlib import Path
import pandas as pd
from backend.supabase.storage import download_file

BASE_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def get_source_file_paths(org_id: str, distributor):
    base = BASE_DATA_DIR / org_id

    return {
        # RAW LAYER
        "raw_new_month": base / "raw" / f"{distributor}_new_month.csv",
        "raw_master": base / "raw" / f"{distributor}_master.csv",
        "raw_master_previous": base / "raw" / f"{distributor}_master_previous.csv",

        # PROCESSED LAYER
        "processed_current": base / "processed" / f"{distributor}_current.parquet",
        "processed_previous": base / "processed" / f"{distributor}_previous.parquet",

        # ANALYTICS (unchanged)
        "analytics_current": base / "analytics" / "combined.parquet",
    }

from pathlib import Path
from backend.supabase.storage import download_file
import pandas as pd


def apply_sku_map(df: pd.DataFrame, org_id: str) -> pd.DataFrame:
    sku_map_path = Path(f"backend/data/{org_id}/maps/sku_name_map.csv")

    # -----------------------------
    # Ensure local copy exists
    # -----------------------------
    if not sku_map_path.exists():
        try:
            print("⬇️ Downloading SKU map from Supabase...")
            download_file(
                org_id=org_id,
                remote_path="maps/sku_name_map.csv",
                local_path=str(sku_map_path),
            )
        except Exception as e:
            print(f"⚠️ No SKU map found in Supabase. Skipping mapping. {repr(e)}")
            return df

    if not sku_map_path.exists():
        return df

    # -----------------------------
    # Read + clean map
    # -----------------------------
    sku_map = pd.read_csv(sku_map_path, encoding="utf-8-sig")

    # Clean column names
    sku_map.columns = sku_map.columns.str.strip().str.lower()

    if "raw_sku" not in sku_map.columns or "clean_sku" not in sku_map.columns:
        raise ValueError(f"Invalid columns in sku_map: {sku_map.columns.tolist()}")

    # Clean values
    sku_map["raw_sku"] = sku_map["raw_sku"].astype(str).str.strip()
    sku_map["clean_sku"] = sku_map["clean_sku"].astype(str).str.strip()

    df = df.copy()
    df["sku"] = df["sku"].astype(str).str.strip()

    # -----------------------------
    # Apply mapping
    # -----------------------------
    lookup = dict(zip(sku_map["raw_sku"], sku_map["clean_sku"]))

    before = df["sku"].copy()
    df["sku"] = df["sku"].replace(lookup)

    print(f"SKU map applied. Rows changed: {(before != df['sku']).sum()}")

    return df
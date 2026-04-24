from pathlib import Path

BASE_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


from pathlib import Path

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
import pandas as pd

def apply_sku_map(df: pd.DataFrame, org_id: str) -> pd.DataFrame:
    sku_map_path = Path(f"backend/data/{org_id}/maps/sku_map.csv")

    if not sku_map_path.exists():
        return df

    sku_map = pd.read_csv(sku_map_path)

    if "raw_sku" not in sku_map.columns or "clean_sku" not in sku_map.columns:
        raise ValueError("sku_map.csv must have 'raw_sku' and 'clean_sku' columns")

    lookup = dict(zip(sku_map["raw_sku"], sku_map["clean_sku"]))

    df = df.copy()
    df["sku"] = df["sku"].replace(lookup)

    return df
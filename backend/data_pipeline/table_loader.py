from pathlib import Path
from functools import lru_cache
import pandas as pd

DATA_ROOT = Path("backend/data")


@lru_cache(maxsize=32)
def load_org_tables(org_id: str = "default_org"):
    org_path = DATA_ROOT / org_id

    features_df_path = org_path / "features_df.parquet"

    if not features_df_path.exists():
        raise FileNotFoundError(f"Missing features_df for org: {org_id}")

    features_df = pd.read_parquet(features_df_path)

    print("LOADING FROM DISK")

    return features_df

def clear_table_cache():
    load_org_tables.cache_clear()
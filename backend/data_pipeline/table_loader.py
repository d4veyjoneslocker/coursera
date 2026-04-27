from pathlib import Path
import pandas as pd
import re
from backend.storage.supabase_storage import download_file

DATA_ROOT = Path("backend/data").resolve()

# 🔥 per-org cache
TABLE_CACHE: dict[str, pd.DataFrame] = {}


def get_org_path(org_id: str) -> Path:
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", org_id):
        raise ValueError("Invalid org_id")

    org_path = (DATA_ROOT / org_id).resolve()

    if not str(org_path).startswith(str(DATA_ROOT)):
        raise ValueError("Invalid org path")

    return org_path


def load_org_tables(org_id: str):
    # ✅ return cached if exists
    if org_id in TABLE_CACHE:
        return TABLE_CACHE[org_id]

    org_path = get_org_path(org_id)
    features_df_path = org_path / "features_df.parquet"

    if not features_df_path.exists():
        print(f"⬇️ Downloading features_df for {org_id} from Supabase...")

        download_file(
            org_id=org_id,
            remote_path="processed/features_df.parquet",
            local_path=str(features_df_path),
        )

    features_df = pd.read_parquet(features_df_path)

    print(f"LOADING FROM DISK: {org_id}")

    # ✅ store in cache
    TABLE_CACHE[org_id] = features_df

    return features_df


def clear_table_cache(org_id: str | None = None):
    # clear all
    if org_id is None:
        TABLE_CACHE.clear()
        return

    # clear specific org
    TABLE_CACHE.pop(org_id, None)
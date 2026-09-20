from pathlib import Path
import pandas as pd
import re

from backend.supabase.storage import download_file


DATA_ROOT = Path("backend/data").resolve()

# Per-org caches
TABLE_CACHE: dict[str, pd.DataFrame] = {}
ACTIVE_PODS_CACHE: dict[str, pd.DataFrame] = {}
INVENTORY_ASSESSMENT_CACHE: dict[str, dict] = {}


def get_org_path(org_id: str) -> Path:
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", org_id):
        raise ValueError("Invalid org_id")

    org_path = (DATA_ROOT / org_id).resolve()

    if not str(org_path).startswith(str(DATA_ROOT)):
        raise ValueError("Invalid org path")

    return org_path


def load_org_tables(org_id: str):
    """
    Load the main features table for an org.

    Cached independently from active_pods_df so requests that do not
    need active POD data do not load it unnecessarily.
    """

    if org_id in TABLE_CACHE:
        print(
            f"⚡ FEATURES CACHE HIT: {org_id} | "
            f"cached orgs: {list(TABLE_CACHE.keys())}"
        )
        return TABLE_CACHE[org_id]

    print(
        f"❌ FEATURES CACHE MISS: {org_id} | "
        f"cached orgs before load: {list(TABLE_CACHE.keys())}"
    )

    org_path = get_org_path(org_id)
    features_df_path = org_path / "features_df.parquet"

    if not features_df_path.exists():
        print(
            f"⬇️ Downloading features_df for "
            f"{org_id} from Supabase..."
        )

        download_file(
            org_id=org_id,
            remote_path="processed/features_df.parquet",
            local_path=str(features_df_path),
        )

    features_df = pd.read_parquet(
        features_df_path
    )

    print(
        f"💾 LOADING FEATURES FROM DISK: {org_id}"
    )

    TABLE_CACHE[org_id] = features_df

    return features_df


def load_active_pods(org_id: str):
    """
    Load the precomputed active POD membership table for an org.

    This is loaded lazily so requests that do not need active POD
    information do not incur the cost of loading the table.
    """

    if org_id in ACTIVE_PODS_CACHE:
        print(
            f"⚡ ACTIVE PODS CACHE HIT: {org_id} | "
            f"cached orgs: {list(ACTIVE_PODS_CACHE.keys())}"
        )
        return ACTIVE_PODS_CACHE[org_id]

    print(
        f"❌ ACTIVE PODS CACHE MISS: {org_id} | "
        f"cached orgs before load: "
        f"{list(ACTIVE_PODS_CACHE.keys())}"
    )

    org_path = get_org_path(org_id)
    active_pods_path = (
        org_path / "active_pods_df.parquet"
    )

    if not active_pods_path.exists():
        print(
            f"⬇️ Downloading active_pods_df for "
            f"{org_id} from Supabase..."
        )

        download_file(
            org_id=org_id,
            remote_path="processed/active_pods_df.parquet",
            local_path=str(active_pods_path),
        )

    active_pods_df = pd.read_parquet(
        active_pods_path
    )

    print(
        f"💾 LOADING ACTIVE PODS FROM DISK: {org_id}"
    )

    ACTIVE_PODS_CACHE[org_id] = active_pods_df

    return active_pods_df


def get_cached_inventory_assessments(
    org_id: str,
):
    return INVENTORY_ASSESSMENT_CACHE.get(org_id)


def cache_inventory_assessments(
    org_id: str,
    assessments: list[dict],
):
    by_sku = {
        (
            row["distributor"],
            row["dc"],
            row["sku"],
        ): row
        for row in assessments
    }

    cached = {
        "rows": assessments,
        "by_sku": by_sku,
    }

    INVENTORY_ASSESSMENT_CACHE[org_id] = cached

    return cached


def clear_table_cache(
    org_id: str | None = None,
):
    if org_id is None:
        TABLE_CACHE.clear()
        ACTIVE_PODS_CACHE.clear()
        INVENTORY_ASSESSMENT_CACHE.clear()
        return

    TABLE_CACHE.pop(org_id, None)
    ACTIVE_PODS_CACHE.pop(org_id, None)
    INVENTORY_ASSESSMENT_CACHE.pop(org_id, None)
from pathlib import Path
import pandas as pd
import re
import threading

from backend.supabase.storage import download_file


DATA_ROOT = Path("backend/data").resolve()

# Per-org caches
TABLE_CACHE: dict[str, pd.DataFrame] = {}
ACTIVE_PODS_CACHE: dict[str, pd.DataFrame] = {}
INVENTORY_ASSESSMENT_CACHE: dict[str, dict] = {}
FILL_RATE_CACHE: dict[str, pd.DataFrame] = {}


# -------------------------------------------------------------------
# Per-org load locks
#
# Prevent multiple simultaneous requests from trying to download/read
# the same org's parquet files at the same time.
# -------------------------------------------------------------------

_ORG_LOAD_LOCKS: dict[str, threading.Lock] = {}
_ORG_LOAD_LOCKS_GUARD = threading.Lock()


def _get_org_load_lock(org_id: str) -> threading.Lock:
    """
    Return a shared lock for this org.

    The guard lock protects creation of the per-org lock itself.
    """
    with _ORG_LOAD_LOCKS_GUARD:
        if org_id not in _ORG_LOAD_LOCKS:
            _ORG_LOAD_LOCKS[org_id] = threading.Lock()

        return _ORG_LOAD_LOCKS[org_id]


def get_org_path(org_id: str) -> Path:
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", org_id):
        raise ValueError("Invalid org_id")

    org_path = (DATA_ROOT / org_id).resolve()

    if not str(org_path).startswith(str(DATA_ROOT)):
        raise ValueError("Invalid org path")

    return org_path


def _local_file_is_valid(path: Path) -> bool:
    """
    A parquet cache file is usable only if it exists and contains data.

    This prevents a failed/interrupted download from leaving behind a
    zero-byte file that future requests mistakenly treat as valid.
    """
    return path.exists() and path.stat().st_size > 0


def load_org_tables(org_id: str):
    """
    Load the main features table for an org.

    Cached independently from active_pods_df so requests that do not
    need active POD data do not load it unnecessarily.
    """

    # Fast path: already loaded in memory.
    if org_id in TABLE_CACHE:
        print(
            f"⚡ FEATURES CACHE HIT: {org_id} | "
            f"cached orgs: {list(TABLE_CACHE.keys())}"
        )
        return TABLE_CACHE[org_id]

    lock = _get_org_load_lock(org_id)

    with lock:
        # IMPORTANT:
        # Another request may have loaded the dataframe while this
        # request was waiting for the lock.
        if org_id in TABLE_CACHE:
            print(
                f"⚡ FEATURES CACHE HIT AFTER WAIT: {org_id}"
            )
            return TABLE_CACHE[org_id]

        print(
            f"❌ FEATURES CACHE MISS: {org_id} | "
            f"cached orgs before load: {list(TABLE_CACHE.keys())}"
        )

        org_path = get_org_path(org_id)
        org_path.mkdir(parents=True, exist_ok=True)

        features_df_path = org_path / "features_df.parquet"

        if not _local_file_is_valid(features_df_path):
            print(
                f"⬇️ Downloading features_df for "
                f"{org_id} from Supabase..."
            )

            # Remove any zero-byte / invalid leftover file first.
            features_df_path.unlink(missing_ok=True)

            download_file(
                org_id=org_id,
                remote_path="processed/features_df.parquet",
                local_path=str(features_df_path),
            )

        # Defensive check after download.
        if not _local_file_is_valid(features_df_path):
            raise RuntimeError(
                f"features_df download failed for {org_id}: "
                f"local parquet file is missing or empty"
            )

        features_df = pd.read_parquet(
            features_df_path
        )

        print(
            f"💾 LOADING FEATURES FROM DISK: {org_id}"
        )

        TABLE_CACHE[org_id] = features_df

        return features_df


def load_fill_rate_df(org_id: str):
    """
    Load the fill-rate fact table for an org.

    Loaded lazily so requests that do not need fill-rate data
    do not incur the cost of loading the table.
    """

    if org_id in FILL_RATE_CACHE:
        print(
            f"⚡ FILL RATE CACHE HIT: {org_id} | "
            f"cached orgs: {list(FILL_RATE_CACHE.keys())}"
        )
        return FILL_RATE_CACHE[org_id]

    lock = _get_org_load_lock(org_id)

    with lock:
        # Re-check after waiting for another request.
        if org_id in FILL_RATE_CACHE:
            print(
                f"⚡ FILL RATE CACHE HIT AFTER WAIT: {org_id}"
            )
            return FILL_RATE_CACHE[org_id]

        print(
            f"❌ FILL RATE CACHE MISS: {org_id} | "
            f"cached orgs before load: "
            f"{list(FILL_RATE_CACHE.keys())}"
        )

        org_path = get_org_path(org_id)
        org_path.mkdir(parents=True, exist_ok=True)

        fill_rate_path = (
            org_path / "fill_rate_df.parquet"
        )

        if not _local_file_is_valid(fill_rate_path):
            print(
                f"⬇️ Downloading fill_rate_df for "
                f"{org_id} from Supabase..."
            )

            fill_rate_path.unlink(missing_ok=True)

            download_file(
                org_id=org_id,
                remote_path="processed/fill_rate_df.parquet",
                local_path=str(fill_rate_path),
            )

        if not _local_file_is_valid(fill_rate_path):
            raise RuntimeError(
                f"fill_rate_df download failed for {org_id}: "
                f"local parquet file is missing or empty"
            )

        fill_rate_df = pd.read_parquet(
            fill_rate_path
        )

        print(
            f"💾 LOADING FILL RATE FROM DISK: {org_id}"
        )

        FILL_RATE_CACHE[org_id] = fill_rate_df

        return fill_rate_df


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

    lock = _get_org_load_lock(org_id)

    with lock:
        # Re-check after waiting for another request.
        if org_id in ACTIVE_PODS_CACHE:
            print(
                f"⚡ ACTIVE PODS CACHE HIT AFTER WAIT: {org_id}"
            )
            return ACTIVE_PODS_CACHE[org_id]

        print(
            f"❌ ACTIVE PODS CACHE MISS: {org_id} | "
            f"cached orgs before load: "
            f"{list(ACTIVE_PODS_CACHE.keys())}"
        )

        org_path = get_org_path(org_id)
        org_path.mkdir(parents=True, exist_ok=True)

        active_pods_path = (
            org_path / "active_pods_df.parquet"
        )

        if not _local_file_is_valid(active_pods_path):
            print(
                f"⬇️ Downloading active_pods_df for "
                f"{org_id} from Supabase..."
            )

            active_pods_path.unlink(missing_ok=True)

            download_file(
                org_id=org_id,
                remote_path="processed/active_pods_df.parquet",
                local_path=str(active_pods_path),
            )

        if not _local_file_is_valid(active_pods_path):
            raise RuntimeError(
                f"active_pods_df download failed for {org_id}: "
                f"local parquet file is missing or empty"
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
        FILL_RATE_CACHE.clear()
        INVENTORY_ASSESSMENT_CACHE.clear()
        return

    TABLE_CACHE.pop(org_id, None)
    ACTIVE_PODS_CACHE.pop(org_id, None)
    FILL_RATE_CACHE.pop(org_id, None)
    INVENTORY_ASSESSMENT_CACHE.pop(org_id, None)
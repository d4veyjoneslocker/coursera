from pathlib import Path
import pandas as pd

from backend.metrics.features import add_features
from backend.data_pipeline.validate_data import validate_data
from backend.data_pipeline.pipeline_helpers import get_source_file_paths
from backend.supabase.storage import upload_file, download_file


def load_source(
    df_list,
    org_id,
    source,
    remote_path,
    force_download=False,
):
    """
    Load a processed distributor source.

    Default behavior:
        Use the local processed file if it already exists.
        Otherwise download the latest persisted version from Supabase.

    force_download=True:
        Ignore any existing local copy and fetch the latest persisted
        version from Supabase.

    This is useful during a KeHE upload:
        - KeHE should use the fresh local candidate created in this run.
        - UNFI should use the latest canonical persisted version.
    """

    paths = get_source_file_paths(org_id, source)
    path = paths["processed_current"]

    if force_download:
        if path.exists():
            path.unlink()

        try:
            print(f"⬇️ Downloading latest {source.upper()} from Supabase...")
            download_file(
                org_id,
                remote_path,
                str(path),
            )
        except Exception as e:
            print(
                f"⚠️ No persisted {source.upper()} found in Supabase. "
                f"Skipping. {repr(e)}"
            )

    elif not path.exists():
        try:
            print(f"⬇️ Downloading {source.upper()} from Supabase...")
            download_file(
                org_id,
                remote_path,
                str(path),
            )
        except Exception as e:
            print(
                f"⚠️ No {source.upper()} found in Supabase. "
                f"Skipping. {repr(e)}"
            )

    if path.exists():
        df = pd.read_parquet(path)
        df_list.append(df)

        print(
            f"✅ Loaded {source.upper()}: "
            f"{len(df)} rows"
        )
    else:
        print(
            f"⚠️ No {source.upper()} parquet found. "
            f"Skipping."
        )


def build_active_pods_df(
    features_df: pd.DataFrame,
    active_months: int = 6,
) -> pd.DataFrame:
    """
    Build monthly active-POD membership from features_df.

    A POD is active in its purchase month and for the following
    active_months - 1 months.
    """

    if active_months < 1:
        raise ValueError("active_months must be at least 1")

    membership_cols = [
        "month_year",
        "pod_helper",
        "chain",
        "sku",
        "dc",
        "distributor",
        "channel",
        "state",
    ]

    missing_cols = [
        col for col in membership_cols
        if col not in features_df.columns
    ]

    if missing_cols:
        raise ValueError(
            f"Missing required active POD columns: {missing_cols}"
        )

    purchases = features_df[membership_cols].copy()

    purchases["month_year"] = pd.PeriodIndex(
        purchases["month_year"],
        freq="M",
    )

    purchases = purchases.drop_duplicates()

    active_frames = []

    for offset in range(active_months):
        shifted = purchases.copy()
        shifted["month_year"] = shifted["month_year"] + offset
        active_frames.append(shifted)

    active_pods_df = (
        pd.concat(active_frames, ignore_index=True)
        .drop_duplicates()
        .sort_values(
            [
                "month_year",
                "distributor",
                "dc",
                "channel",
                "chain",
                "state",
                "sku",
                "pod_helper",
            ]
        )
        .reset_index(drop=True)
    )

    # Add time dimensions so active_pods_df can use
    # the same filter_table logic as features_df.
    active_pods_df["year"] = (
        active_pods_df["month_year"]
        .dt.year
        .astype(str)
    )

    active_pods_df["month"] = (
        active_pods_df["month_year"]
        .dt.month
        .astype(str)
    )

    return active_pods_df

def build_base_tables(
    org_id: str,
    refresh_sources=None,
    active_months: int = 6,
):
    """
    Build the combined features dataframe.

    refresh_sources:
        Optional iterable of distributor names whose processed data
        should be re-downloaded from canonical Supabase storage before
        building features.

    Example for a KeHE upload:
        refresh_sources={"unfi"}

    This means:
        - use the fresh local KeHE candidate
        - use the latest persisted UNFI candidate
    """

    refresh_sources = set(refresh_sources or [])

    dfs = []

    load_source(
        dfs,
        org_id,
        "kehe",
        "processed_sources/kehe_processed.parquet",
        force_download="kehe" in refresh_sources,
    )

    load_source(
        dfs,
        org_id,
        "unfi",
        "processed_sources/unfi_processed.parquet",
        force_download="unfi" in refresh_sources,
    )

    if not dfs:
        raise ValueError("No source data found.")

    clean_df = pd.concat(
        dfs,
        ignore_index=True,
    )

    for col in [
        "upc",
        "coded_customer",
        "store_number",
        "zip",
        "sku",
        "distributor",
        "dc",
    ]:
        if col in clean_df.columns:
            clean_df[col] = clean_df[col].astype(str)

    features_df = add_features(clean_df)
    active_pods_df = build_active_pods_df(
        features_df=features_df,
        active_months=active_months,
    )

    errors = validate_data(clean_df)

    if errors:
        print("❌ Data validation failed:")

        for e in errors:
            print(f"- {e}")

    else:
        print("✅ Data validated")

    return features_df, active_pods_df



def save_base_tables(
    output_dir: str,
    org_id: str,
    upload: bool = True,
    refresh_sources=None,
    active_months: int = 6,
):
    """
    Build and save features_df locally.

    upload=True:
        Preserve existing behavior and immediately upload features_df
        to Supabase.

    upload=False:
        Save the candidate locally only. The caller is responsible for
        validating and publishing it later.
    """

    features_df, active_pods_df = build_base_tables(
        org_id=org_id,
        refresh_sources=refresh_sources,
        active_months=active_months,
    )

    out = Path(output_dir)
    out.mkdir(
        parents=True,
        exist_ok=True,
    )

    for col in [
        "upc",
        "coded_customer",
        "store_number",
        "zip",
        "sku",
        "distributor",
        "dc",
    ]:
        if col in features_df.columns:
            features_df[col] = features_df[col].astype(str)

    features_path = out / "features_df.parquet"
    active_pods_path = out / "active_pods_df.parquet"

    # -------------------------------------------------
    # Save locally
    # -------------------------------------------------

    features_df.to_parquet(
        features_path,
        index=False,
    )

    active_pods_df.to_parquet(
        active_pods_path,
        index=False,
    )

    print(f"✅ features_df saved to {features_path}")
    print(f"✅ active_pods_df saved to {active_pods_path}")

    # -------------------------------------------------
    # Upload to Supabase
    # -------------------------------------------------

    if upload:
        try:
            print("☁️ Uploading base tables to Supabase...")

            upload_file(
                local_path=str(features_path),
                org_id=org_id,
                remote_path="processed/features_df.parquet",
            )

            upload_file(
                local_path=str(active_pods_path),
                org_id=org_id,
                remote_path="processed/active_pods_df.parquet",
            )

            print("✅ base tables uploaded to Supabase")

        except Exception as e:
            print(
                "⚠️ base table upload failed:",
                e,
            )

    return (
        features_df,
        active_pods_df,
        features_path,
        active_pods_path,
    )



if __name__ == "__main__":
    save_base_tables(
        output_dir="backend/data/67a96381-5014-4a9b-bfe8-a14e6da5affe",
        org_id="67a96381-5014-4a9b-bfe8-a14e6da5affe",
    )
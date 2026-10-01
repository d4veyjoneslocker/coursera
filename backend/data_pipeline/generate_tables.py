from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

from backend.metrics.features import add_features
from backend.metrics.fill_rate.features import build_fill_rate_features
from backend.transforms.fill_rate.kehe import transform_kehe_fill_rate
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
    fill_rate_df: pd.DataFrame,
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
        "coded_customer",
        "chain_store_key",
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

    # Actual POD purchase months.
    # Used after expansion to determine whether an active POD
    # actually ordered in each month.
    order_months = (
        purchases[
            [
                "month_year",
                "pod_helper",
            ]
        ]
        .drop_duplicates()
        .assign(ordered=True)
    )

    # First actual purchase month for each POD.
    # A POD can reorder in any month after this month.
    first_purchase_month = (
        purchases
        .groupby(
            "pod_helper",
            as_index=False,
        )["month_year"]
        .min()
        .rename(
            columns={
                "month_year": "first_purchase_month",
            }
        )
    )

    coverage_cols = [
        "distributor",
        "chain_store_key",
        "sku",
    ]

    fill_rate_coverage = (
        fill_rate_df[coverage_cols]
        .dropna(subset=["chain_store_key", "sku"])
        .drop_duplicates()
        .assign(has_fill_rate_data=True)
    )

    purchases = purchases.merge(
        fill_rate_coverage,
        on=coverage_cols,
        how="left",
    )

    purchases["has_fill_rate_data"] = (
        purchases["has_fill_rate_data"]
        .fillna(False)
        .astype(bool)
    )

    purchases["source_month"] = purchases["month_year"]

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

    active_pods_df = (
        active_pods_df
        .sort_values(
            [
                "month_year",
                "pod_helper",
                "source_month",
            ]
        )
        .drop_duplicates(
            subset=[
                "month_year",
                "pod_helper",
            ],
            keep="last",
        )
        .drop(columns=["source_month"])
        .sort_values("month_year")
        .reset_index(drop=True)
    )

    # Add historical reorder state.
    active_pods_df = active_pods_df.merge(
        first_purchase_month,
        on="pod_helper",
        how="left",
    )

    active_pods_df["could_reorder"] = (
        active_pods_df["month_year"]
        > active_pods_df["first_purchase_month"]
    )

    active_pods_df = active_pods_df.drop(
        columns=["first_purchase_month"]
    )

    # Add whether the POD actually ordered in this month.
    active_pods_df = active_pods_df.merge(
        order_months,
        on=[
            "month_year",
            "pod_helper",
        ],
        how="left",
    )

    active_pods_df["ordered"] = (
        active_pods_df["ordered"]
        .fillna(False)
        .astype(bool)
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

    # -------------------------------------------------
    # Build fill-rate table
    # -------------------------------------------------


    fill_rate_source_path = (
        Path(f"backend/data/{org_id}")
        / "processed_sources"
        / "kehe_fill_rate.parquet"
    )

    fill_rate_source_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not fill_rate_source_path.exists():
        print("⬇️ Downloading KeHE fill-rate source from Supabase...")

        download_file(
            org_id,
            "processed_sources/kehe_fill_rate.parquet",
            str(fill_rate_source_path),
        )

    fill_rate_raw = pd.read_parquet(fill_rate_source_path)

    kehe_fill_rate_df = transform_kehe_fill_rate(
        fill_rate_raw,
        org_id=org_id,
    )

    fill_rate_df = build_fill_rate_features(
        kehe_fill_rate_df=kehe_fill_rate_df,
        features_df=features_df,
    )

    active_pods_df = build_active_pods_df(
        features_df=features_df,
        fill_rate_df=fill_rate_df,
        active_months=active_months,
    )

    errors = validate_data(clean_df)

    if errors:
        print("❌ Data validation failed:")

        for e in errors:
            print(f"- {e}")

    else:
        print("✅ Data validated")

    sept = pd.Period("2026-09", freq="M")

    print("\n=== FRESH BUILD SEPTEMBER CHECK ===")

    print(
        "features September PODs:",
        features_df.loc[
            features_df["month_year"] == sept,
            "pod_helper",
        ].nunique(),
    )

    sept_active = active_pods_df[
        active_pods_df["month_year"] == sept
    ]

    print("active POD rows:", len(sept_active))
    print("ordered=True:", sept_active["ordered"].sum())

    print("===================================\n")

    return features_df, active_pods_df, fill_rate_df



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

    features_df, active_pods_df, fill_rate_df = build_base_tables(
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
    fill_rate_path = out / "fill_rate_df.parquet"

    # -------------------------------------------------
    # Save locally
    # -------------------------------------------------

    features_df.to_parquet(
        features_path,
        index=False,
    )

    fill_rate_df.to_parquet(
        fill_rate_path,
        index=False,
    )

    active_pods_df.to_parquet(
        active_pods_path,
        index=False,
    )

    print(f"✅ features_df saved to {features_path}")
    print(f"✅ fill_rate_df saved to {fill_rate_path}")
    print(f"✅ active_pods_df saved to {active_pods_path}")

    # -------------------------------------------------
    # Upload to Supabase
    # -------------------------------------------------

    # -------------------------------------------------
# Upload to Supabase
# -------------------------------------------------

    if upload:
        try:
            print("☁️ Uploading base tables to Supabase...")

            # Current canonical files
            upload_file(
                local_path=str(features_path),
                org_id=org_id,
                remote_path="processed/features_df.parquet",
            )

            upload_file(
                local_path=str(fill_rate_path),
                org_id=org_id,
                remote_path="processed/fill_rate_df.parquet",
            )

            upload_file(
                local_path=str(active_pods_path),
                org_id=org_id,
                remote_path="processed/active_pods_df.parquet",
            )

            print("✅ base tables uploaded to Supabase")

            # -------------------------------------------------
            # Save immutable historical snapshot
            # -------------------------------------------------

            snapshot_at = datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H-%M-%SZ"
            )

            snapshot_dir = f"history/{snapshot_at}"

            upload_file(
                local_path=str(features_path),
                org_id=org_id,
                remote_path=f"{snapshot_dir}/features_df.parquet",
            )

            upload_file(
                local_path=str(fill_rate_path),
                org_id=org_id,
                remote_path=f"{snapshot_dir}/fill_rate_df.parquet",
            )

            print(f"📸 historical snapshot saved: {snapshot_dir}")

        except Exception as e:
            print(
                "⚠️ base table upload failed:",
                e,
            )

    return (
        features_df,
        active_pods_df,
        fill_rate_df,
        features_path,
        active_pods_path,
        fill_rate_path,
    )



if __name__ == "__main__":
    save_base_tables(
        output_dir="backend/data/default_org",
        org_id="default_org",
    )
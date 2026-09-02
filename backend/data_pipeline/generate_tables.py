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


def build_base_tables(
    org_id: str,
    refresh_sources=None,
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

    errors = validate_data(clean_df)

    if errors:
        print("❌ Data validation failed:")

        for e in errors:
            print(f"- {e}")

    else:
        print("✅ Data validated")

    return features_df


def save_base_tables(
    output_dir: str,
    org_id: str,
    upload: bool = True,
    refresh_sources=None,
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

    features_df = build_base_tables(
        org_id=org_id,
        refresh_sources=refresh_sources,
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

    local_path = out / "features_df.parquet"

    features_df.to_parquet(
        local_path,
        index=False,
    )

    print(f"✅ base tables saved to {local_path}")

    # -------------------------------------------------
    # Existing behavior for callers that want immediate
    # publication (e.g. current UNFI flow)
    # -------------------------------------------------
    if upload:
        try:
            print("☁️ Uploading features_df to Supabase...")

            upload_file(
                local_path=str(local_path),
                org_id=org_id,
                remote_path="processed/features_df.parquet",
            )

            print("✅ features_df uploaded to Supabase")

        except Exception as e:
            print(
                "⚠️ features_df upload failed:",
                e,
            )

    return features_df, local_path


if __name__ == "__main__":
    save_base_tables(
        output_dir="backend/data/default_org",
        org_id="default_org",
    )
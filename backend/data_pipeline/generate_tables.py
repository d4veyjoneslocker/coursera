from pathlib import Path
import pandas as pd

from backend.metrics.features import add_features
from backend.data_pipeline.validate_data import validate_data
from backend.data_pipeline.pipeline_helpers import get_source_file_paths
from backend.storage.supabase_storage import upload_file, download_file


def load_source(df_list, org_id, source, remote_path):
    paths = get_source_file_paths(org_id, source)
    path = paths["processed_current"]

    if not path.exists():
        try:
            print(f"⬇️ Downloading {source.upper()} from Supabase...")
            download_file(org_id, remote_path, str(path))
        except Exception as e:
            print(f"⚠️ No {source.upper()} found in Supabase. Skipping. {repr(e)}")

    if path.exists():
        df = pd.read_parquet(path)
        df_list.append(df)
        print(f"✅ Loaded {source.upper()}: {len(df)} rows")
    else:
        print(f"⚠️ No {source.upper()} parquet found. Skipping.")


def build_base_tables(org_id: str):
    dfs = []

    load_source(dfs, org_id, "kehe", "processed_sources/kehe_processed.parquet")
    load_source(dfs, org_id, "unfi", "processed_sources/unfi_processed.parquet")

    if not dfs:
        raise ValueError("No source data found.")

    clean_df = pd.concat(dfs, ignore_index=True)

    for col in ["upc", "coded_customer", "store_number", "zip", "sku", "distributor", "dc"]:
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
):
    features_df = build_base_tables(org_id=org_id)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for col in ["upc", "coded_customer", "store_number", "zip", "sku", "distributor", "dc"]:
        if col in features_df.columns:
            features_df[col] = features_df[col].astype(str)

    local_path = out / "features_df.parquet"
    features_df.to_parquet(local_path, index=False)

    print(f"✅ base tables saved to {out}")

    # -----------------------------
    # Upload to Supabase
    # -----------------------------
    try:
        print("☁️ Uploading features_df to Supabase...")

        upload_file(
            local_path=str(local_path),
            org_id=org_id,
            remote_path="processed/features_df.parquet",
        )

        print("✅ features_df uploaded to Supabase")

    except Exception as e:
        print("⚠️ features_df upload failed:", e)


if __name__ == "__main__":
    save_base_tables(
        output_dir="backend/data/default_org",
        org_id="default_org",
    )
from pathlib import Path
import pandas as pd

from backend.metrics.features import add_features
from backend.data_pipeline.validate_data import validate_data
from backend.data_pipeline.pipeline_helpers import get_source_file_paths


def build_base_tables(org_id: str):
    dfs = []

    # -----------------------------
    # KEHE: read local processed parquet
    # -----------------------------
    kehe_paths = get_source_file_paths(org_id, "kehe")
    kehe_path = kehe_paths["processed_current"]

    if kehe_path.exists():
        clean_kehe_df = pd.read_parquet(kehe_path)
        dfs.append(clean_kehe_df)
        print(f"✅ Loaded KeHE: {len(clean_kehe_df)} rows")
    else:
        print(f"⚠️ No KeHE parquet found at {kehe_path}. Skipping KeHE.")

    # -----------------------------
    # UNFI: read local processed parquet
    # -----------------------------
    unfi_paths = get_source_file_paths(org_id, "unfi")
    unfi_path = unfi_paths["processed_current"]

    if unfi_path.exists():
        clean_unfi_df = pd.read_parquet(unfi_path)
        dfs.append(clean_unfi_df)
        print(f"✅ Loaded UNFI: {len(clean_unfi_df)} rows")
    else:
        print(f"⚠️ No UNFI parquet found at {unfi_path}. Skipping UNFI.")

    # -----------------------------
    # Combine available local sources
    # -----------------------------
    if not dfs:
        raise ValueError("No source data found. Missing both KeHE and UNFI processed parquets.")

    clean_df = pd.concat(dfs, ignore_index=True)

    # -----------------------------
    # Standardize key ID dtypes
    # -----------------------------
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

    features_df.to_parquet(out / "features_df.parquet", index=False)

    print(f"✅ base tables saved to {out}")


if __name__ == "__main__":
    save_base_tables(
        output_dir="backend/data/default_org",
        org_id="default_org",
    )
from pathlib import Path
import pandas as pd
import re
from backend.supabase.storage import download_file

BASE_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def get_source_file_paths(org_id: str, distributor):
    base = BASE_DATA_DIR / org_id

    return {
        "raw_new_month": base / "raw" / distributor / f"{distributor}_new_month.csv",
        "raw_master": base / "raw" / distributor / "raw_master.csv",
        "raw_master_previous": base / "raw" / distributor / "raw_master_previous.csv",

        "processed_current": base / "processed_sources" / f"{distributor}_processed.parquet",
        "processed_previous": base / "processed_sources" / f"{distributor}_processed_previous.parquet",

        "analytics_current": base / "processed" / "features_df.parquet",
    }


def apply_sku_map(
    df: pd.DataFrame,
    org_id: str,
    match_mode: str = "name",
) -> pd.DataFrame:

    sku_map_path = Path(
        f"backend/data/{org_id}/maps/sku_name_map.csv"
    )

    # -----------------------------
    # Validate match mode
    # -----------------------------
    if match_mode not in {"name", "upc"}:
        raise ValueError(
            f"Invalid match_mode: {match_mode}. "
            "Expected 'name' or 'upc'."
        )

    # -----------------------------
    # Ensure local copy exists
    # -----------------------------
    if not sku_map_path.exists():
        try:
            print("⬇️ Downloading SKU map from Supabase...")
            download_file(
                org_id=org_id,
                remote_path="maps/sku_name_map.csv",
                local_path=str(sku_map_path),
            )
        except Exception as e:
            print(
                f"⚠️ No SKU map found in Supabase. "
                f"Skipping mapping. {repr(e)}"
            )
            return df

    if not sku_map_path.exists():
        return df

    # -----------------------------
    # Read + clean map
    # -----------------------------
    sku_map = pd.read_csv(
        sku_map_path,
        encoding="utf-8-sig",
        dtype={"upc": "string"},
    )

    sku_map.columns = sku_map.columns.str.strip().str.lower()

    required_columns = {"raw_sku", "clean_sku"}

    if not required_columns.issubset(sku_map.columns):
        raise ValueError(
            f"Invalid columns in sku_map: "
            f"{sku_map.columns.tolist()}"
        )

    sku_map["raw_sku"] = (
        sku_map["raw_sku"]
        .astype("string")
        .str.strip()
    )

    sku_map["clean_sku"] = (
        sku_map["clean_sku"]
        .astype("string")
        .str.strip()
    )

    df = df.copy()

    # =========================================================
    # MATCH BY NAME
    # =========================================================
    if match_mode == "name":

        if "sku" not in df.columns:
            raise ValueError(
                "match_mode='name' requires a 'sku' column."
            )

        df["sku"] = (
            df["sku"]
            .astype("string")
            .str.strip()
        )

        sku_lookup = dict(
            zip(
                sku_map["raw_sku"],
                sku_map["clean_sku"],
            )
        )

        before = df["sku"].copy()

        df["sku"] = df["sku"].replace(sku_lookup)

        print(
            f"SKU map applied by name. "
            f"Rows changed: {(before != df['sku']).sum()}"
        )

    # =========================================================
    # MATCH BY UPC
    # =========================================================
    else:

        if "upc" not in df.columns:
            raise ValueError(
                "match_mode='upc' requires a 'upc' column."
            )

        if "upc" not in sku_map.columns:
            raise ValueError(
                "match_mode='upc' requires an 'upc' column "
                "in sku_name_map.csv."
            )

        # Map is assumed to already contain canonical UPCs.
        sku_map["upc"] = (
            sku_map["upc"]
            .astype("string")
            .str.strip()
        )

        df["upc"] = (
            df["upc"]
            .astype("string")
            .str.strip()
        )

        upc_lookup = dict(
            zip(
                sku_map["upc"],
                sku_map["clean_sku"],
            )
        )

        df["sku"] = df["upc"].map(upc_lookup)

        print(
            f"SKU map applied by UPC. "
            f"Rows matched: {df['sku'].notna().sum()} / {len(df)}"
        )

    # -----------------------------
    # Optional units_per_case
    # -----------------------------
    if "units_per_case" in sku_map.columns:

        sku_map["units_per_case"] = pd.to_numeric(
            sku_map["units_per_case"],
            errors="coerce",
        )

        case_lookup = dict(
            zip(
                sku_map["clean_sku"],
                sku_map["units_per_case"],
            )
        )

        df["units_per_case"] = df["sku"].map(case_lookup)

        print(
            "Units per case added. "
            f"Rows populated: "
            f"{df['units_per_case'].notna().sum()}"
        )

    return df


def extract_chain_store_number_full_pod(name):
    if pd.isna(name):
        return pd.NA

    name = str(name).strip()
    upper = name.upper()

    def normalize(value):
        if not value:
            return pd.NA
        value = str(value).strip()
        normalized = value.lstrip("0")
        return normalized or "0"

    # SPROUTS:
    # "SPROUTS 672 ST JOHNS FROZ" -> "672"
    # "SPROUTS-418-LA VERNE-FROZ" -> "418"
    # "SPROUTS #23-N.1ST-FROZ" -> "23"
    if upper.startswith("SPROUTS"):
        x = upper[len("SPROUTS"):].replace("-", " ").strip()
        x = x.replace("#", "").strip()

        match = re.match(r"(\d+)", x)
        return normalize(match.group(1)) if match else pd.NA

    # FRESH THYME:
    # "FRESH THYME FRMR MKT 107CHI" -> "107"
    if upper.startswith("FRESH THYME"):
        last_token = upper.split()[-1]

        match = re.match(r"(\d+)", last_token)
        return normalize(match.group(1)) if match else pd.NA

    # GENERAL:
    # "KINGS ALB #3638 SUMMIT" -> "3638"
    # "SAFEWAY HAGAN # 3120 GROC" -> "3120"
    # "ALBERTSONS #0149 GROC" -> "149"
    if "#" in name:
        after_hash = name.split("#", 1)[1].strip()

        match = re.match(r"(\d+)", after_hash)
        return normalize(match.group(1)) if match else pd.NA

    # Final token is entirely numeric:
    # "SAFEWAY COMM MKT BERKELEY 2451" -> "2451"
    last_token = name.split()[-1]

    if last_token.isdigit():
        return normalize(last_token)

    return pd.NA


def extract_chain_store_number_fill_rate(name):
    if pd.isna(name):
        return pd.NA

    name = str(name).strip()
    upper = name.upper()

    def normalize(value):
        if not value:
            return pd.NA
        value = str(value).strip()
        normalized = value.lstrip("0")
        return normalized or "0"

    # First priority: number immediately after "#"
    # "SPROUTS #672" -> "672"
    # "SPROUTS/MPC #181" -> "181"
    # "SAFEWAY HAGAN # 3120" -> "3120"
    # "ALBERTSONS MARKET #0665" -> "665"
    if "#" in name:
        after_hash = name.split("#", 1)[1].strip()

        match = re.match(r"(\d+)", after_hash)
        return normalize(match.group(1)) if match else pd.NA

    # SPROUTS without "#"
    # "SPROUTS-418-LA VERNE-FROZ" -> "418"
    if upper.startswith("SPROUTS"):
        x = upper[len("SPROUTS"):].replace("-", " ").strip()

        match = re.match(r"(\d+)", x)
        return normalize(match.group(1)) if match else pd.NA

    # FRESH THYME without "#"
    # "FRESH THYME FRMR MKT 107CHI" -> "107"
    if upper.startswith("FRESH THYME"):
        last_token = upper.split()[-1]

        match = re.match(r"(\d+)", last_token)
        return normalize(match.group(1)) if match else pd.NA

    # Final fallback: final token must be entirely numeric
    # "SAFEWAY COMM MKT BERKELEY 2451" -> "2451"
    last_token = name.split()[-1]

    if last_token.isdigit():
        return normalize(last_token)

    return pd.NA
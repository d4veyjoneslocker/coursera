import re
import pandas as pd


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


def build_fill_rate_features(
    kehe_fill_rate_df: pd.DataFrame,
    features_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build monthly KeHE fill-rate features and attach DC.

    Fill-rate input expected with:
        - month_year
        - chain
        - distributor
        - customer_name
        - chain_store_key
        - sku
        - ordered
        - shipped

    Output grain:
        month_year x chain x customer_name x chain_store_key x sku

    Features:
        - ordered
        - shipped
        - fill_rate
        - dc
    """

    df = kehe_fill_rate_df.copy()

    # ---------------------------------------------------------
    # Aggregate to monthly store x SKU grain
    # ---------------------------------------------------------
    features = (
        df.groupby(
            [
                "month_year",
                "chain",
                "distributor",
                "customer_name",
                "chain_store_key",
                "sku",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(
            ordered=("ordered", "sum"),
            shipped=("shipped", "sum"),
        )
    )

    features["fill_rate"] = (
        features["shipped"] / features["ordered"]
    ).where(features["ordered"] > 0)

    # =========================================================
    # !!! TEMPORARY — FIX THIS IN THE MAIN FEATURES PIPELINE !!!
    #
    # features_df does NOT currently persist chain_store_key.
    #
    # For now, recreate chain_store_key here from the Full POD
    # customer_name using the SAME extraction logic that we
    # validated in the store-matching test.
    #
    # TODO:
    #   Move chain_store_number + chain_store_key creation into
    #   the normal KeHE / features pipeline so features_df
    #   contains these fields natively.
    #
    #   Once features_df contains chain_store_key, DELETE THIS
    #   ENTIRE BLOCK and use features_df directly below.
    # =========================================================

    features_with_store_key = features_df.copy()

    features_with_store_key["chain_store_number"] = (
        features_with_store_key["customer_name"]
        .apply(extract_chain_store_number_full_pod)
        .astype("string")
    )

    features_with_store_key["chain_store_key"] = (
        features_with_store_key["chain"]
        .astype("string")
        .str.strip()
        .str.upper()
        + "|"
        + features_with_store_key["chain_store_number"]
    )

    # ---------------------------------------------------------
    # Build monthly store x SKU -> DC lookup
    # ---------------------------------------------------------
    store_dc_lookup = (
        features_with_store_key.loc[
            features_with_store_key["distributor"].eq("KEHE"),
            [
                "distributor",
                "month_year",
                "chain_store_key",
                "sku",
                "dc",
            ],
        ]
        .dropna(
            subset=[
                "chain_store_key",
                "dc",
            ]
        )
        .drop_duplicates()
    )

    # ---------------------------------------------------------
    # Validate one DC per month x store x SKU
    # ---------------------------------------------------------
    conflicts = (
        store_dc_lookup
        .groupby(
            [
                "distributor",
                "month_year",
                "chain_store_key",
                "sku",
            ],
            dropna=False,
        )["dc"]
        .nunique()
    )

    conflicts = conflicts[conflicts > 1]

    if not conflicts.empty:
        raise ValueError(
            "Multiple DCs found for the same "
            "distributor/month/store/SKU:\n"
            f"{conflicts.to_string()}"
        )

    # ---------------------------------------------------------
    # Attach DC using canonical store identity
    # ---------------------------------------------------------
    result = features.merge(
        store_dc_lookup,
        on=[
            "distributor",
            "month_year",
            "chain_store_key",
            "sku",
        ],
        how="left",
        validate="many_to_one",
    )

    return result
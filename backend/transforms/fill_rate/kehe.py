import pandas as pd
import numpy as np
from backend.data_pipeline.pipeline_helpers import apply_sku_map, extract_chain_store_number_fill_rate


def transform_kehe_fill_rate(
    df: pd.DataFrame, org_id
) -> pd.DataFrame:
    """
    Transform the combined KeHE fill-rate master into a clean,
    lowest-grain table for use in the SKUba feature pipeline.

    Expected input columns:
        month_year
        RetailerName
        Store
        Item
        Ordered
        Shipped

    Output grain:
        month_year x retailer x customer_name x sku/upc

    NOTE:
        fill_rate is intentionally NOT calculated here.
        We preserve ordered + shipped so fill rate can be calculated
        correctly after aggregation into features_df.
    """

    df = df.copy()

    # ---------------------------------------------------------
    # 1. Normalize month
    # ---------------------------------------------------------

    df["month_year"] = pd.PeriodIndex(
        df["month_year"],
        freq="M",
    )

    for col in ["Ordered", "Shipped"]:
        df[col] = pd.to_numeric(
            df[col]
            .astype("string")
            .str.replace(",", "", regex=False)
            .str.strip(),
            errors="coerce",
        )

    df = df.rename(
        columns={
            "RetailerName": "chain",
            "Store": "customer_name",
            "Ordered": "ordered",
            "Shipped": "shipped",
        }
    )

    df["customer_name"] = df["customer_name"].str.split(" - ").str[0]

    # ---------------------------------------------------------
    # 2. Extract UPC from Item
    #
    # Example:
    # "14 FO ICE CREAM FROCO VNLLA BN (850063086004)"
    # ->
    # upc = "850063086004"
    # ---------------------------------------------------------

    # Extract UPC from Item
    df["upc"] = (
        df["Item"]
        .astype("string")
        .str.extract(r"\((\d+)\)\s*$", expand=False)
        .str.lstrip("0")
    )

    # ---------------------------------------------------------
    # 3. Preserve KeHE's raw SKU description
    # ---------------------------------------------------------

    df = apply_sku_map(df, org_id=org_id, match_mode="upc")

    df["ordered_units"] = df["ordered"]
    df["ordered_cases"] = df["ordered_units"] / df["units_per_case"]

    df["shipped_units"] = df["shipped"]
    df["shipped_cases"] = df["shipped_units"] / df["units_per_case"]

    # ---------------------------------------------------------
    # 7. Validation
    # ---------------------------------------------------------

    unmapped = df["sku"].isna()

    if unmapped.any():
        print(
            f"WARNING: {unmapped.sum():,} fill-rate rows "
            f"could not be mapped to a canonical SKU."
        )

        print(
            df.loc[
                unmapped,
                ["Item", "upc", "upc_normalized"]
            ]
            .drop_duplicates()
            .to_string(index=False)
        )


    # ---------------------------------------------------------
    # 8. Keep canonical fields
    # ---------------------------------------------------------

    df = df[
        [
            "month_year",
            "chain",
            "customer_name",
            "sku",
            "upc",
            "units_per_case",
            "ordered_cases",
            "ordered_units",
            "shipped_cases",
            "shipped_units",
        ]
    ].copy()

    # Normalize across Sprouts areas
    df["chain"] = np.where(
        df["chain"].str.startswith("Sprouts"), "SPROUTS", 
        df["chain"].str.upper()
    )

    df["chain"] = np.where(
        df["chain"].str.startswith("FRESH THYME"), "FRESH THYME", 
        df["chain"]
    )

    df["chain"] = np.select(
        [
            df["chain"].str.startswith("ALB/SWY"),
            df["chain"].str.startswith("ALBERTSONS"),
            df["chain"].str.startswith("SAFEWAY"),
            df["chain"].str.startswith("SWY/CARRS"), 
        ],
        [
            "ALBERTSONS/SAFEWAY",
            "ALBERTSONS/SAFEWAY",
            "ALBERTSONS/SAFEWAY",
            "ALBERTSONS/SAFEWAY",
        ],
        df["chain"].str.upper()
    )

    df["chain_store_number"] = (
        df["customer_name"]
        .apply(extract_chain_store_number_fill_rate)
        .astype("string")
    )

    df["chain_store_key"] = (
        df["chain"].astype("string").str.strip().str.upper()
        + "|"
        + df["chain_store_number"].astype("string")
    )


    # ---------------------------------------------------------
    # 9. Remove rows without usable order quantities
    # ---------------------------------------------------------

    df = df[
        df["ordered_cases"].notna()
        & df["shipped_cases"].notna()
    ].copy()

    df["distributor"] = "KEHE"


    # ---------------------------------------------------------
    # 10. Collapse duplicates at canonical grain
    #
    # If KeHE happens to give multiple records for the same
    # month/store/SKU, ordered and shipped are additive.
    # ---------------------------------------------------------

    df = (
        df.groupby(
            [
                "month_year",
                "chain",
                "distributor",
                "customer_name",
                "chain_store_key",
                "chain_store_number",
                "sku",
                "upc",
                "units_per_case",
            ],
            dropna=False,
            as_index=False,
        )
        .agg(
            ordered_cases=("ordered_cases", "sum"),
            ordered_units=("ordered_units", "sum"),
            shipped_cases=("shipped_cases", "sum"),
            shipped_units=("shipped_units", "sum"),
        )
    )

    return df

if __name__ == "__main__":
    org_id = "default_org"

    input_path = (
        f"backend/data/{org_id}/processed/fill_rate"
    )

    output_path = (
        f"backend/data/{org_id}/processed/"
        "kehe_fill_rate_processed.parquet"
    )

    df = pd.read_parquet(input_path)

    processed = transform_kehe_fill_rate(
        df,
        org_id=org_id,
    )

    processed.to_parquet(
        output_path,
        index=False,
    )

    print(f"Saved {len(processed):,} rows to {output_path}")
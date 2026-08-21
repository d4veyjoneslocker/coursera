import pandas as pd
from backend.data_pipeline.pipeline_helpers import apply_sku_map

def transform_unfi_inventory(
    df: pd.DataFrame,
    org_id: str,
) -> pd.DataFrame:

    df = df.copy()

    rename_map = {
        "Brand": "brand",
        "Warehouse": "dc",
        "Upc": "upc",
        "Description": "sku",

        "VendorItemNumber": "vendor_item_number",

        "MasterPack": "vendor_case_pack",

        "OnHand": "quantity_on_hand_cases",
        "OnOrder": "quantity_on_purchase_order_cases",

        "LeadTime": "lead_time_weeks",

        "Region": "region",

        "WeekEndDate": "report_date",
    }

    df = df.rename(columns=rename_map)

    # -----------------------------
    # Metadata
    # -----------------------------
    df["org_id"] = org_id
    df["distributor"] = "unfi"

    df["report_date"] = pd.to_datetime(
        df["report_date"],
        errors="coerce",
    )

    df["month_year"] = (
        df["report_date"]
        .dt.to_period("M")
        .astype(str)
    )

    # -----------------------------
    # Keep cols
    # -----------------------------
    keep_cols = [
        "org_id",
        "distributor",
        "report_date",
        "month_year",

        "brand",
        "region",
        "dc",
        "upc",
        "sku",

        "vendor_item_number",
        "vendor_case_pack",

        "quantity_on_hand_cases",
        "quantity_on_purchase_order_cases",

        "lead_time_weeks",
    ]

    for col in keep_cols:
        if col not in df.columns:
            df[col] = pd.NA

    out = df[keep_cols].copy()

    # -----------------------------
    # String cleaning
    # -----------------------------
    string_cols = [
        "org_id",
        "distributor",
        "brand",
        "region",
        "dc",
        "upc",
        "sku",
        "vendor_item_number",
    ]

    for col in string_cols:
        out[col] = (
            out[col]
            .astype(str)
            .str.strip()
        )

    # -----------------------------
    # Numeric cleaning
    # -----------------------------
    numeric_cols = [
        "vendor_case_pack",
        "quantity_on_hand_cases",
        "quantity_on_purchase_order_cases",
        "lead_time_weeks",
    ]

    for col in numeric_cols:
        out[col] = pd.to_numeric(
            out[col],
            errors="coerce",
        )

    # -----------------------------
    # Clean invalid case packs
    # -----------------------------
    out.loc[
        out["vendor_case_pack"] <= 0,
        "vendor_case_pack"
    ] = pd.NA

    # -----------------------------
    # Convert cases -> units
    # -----------------------------
    out["quantity_on_hand_units"] = (
        out["quantity_on_hand_cases"]
        * out["vendor_case_pack"]
    )

    out["quantity_on_purchase_order_units"] = (
        out["quantity_on_purchase_order_cases"]
        * out["vendor_case_pack"]
    )

    # -----------------------------
    # Apply SKU map
    # -----------------------------

    out = apply_sku_map(out, org_id)

    return out
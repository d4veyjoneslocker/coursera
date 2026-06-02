import pandas as pd


def transform_kehe_inventory(
    df: pd.DataFrame,
    org_id: str,
) -> pd.DataFrame:

    df = df.copy()

    rename_map = {
        "Brand": "brand",
        "DC": "dc",
        "UPC": "upc",
        "ProductDescription": "sku",
        "VendorCasePack": "vendor_case_pack",

        "QuantityOnHand": "quantity_on_hand_units",
        "QuantityOnPurchaseOrder": "quantity_on_purchase_order_units",
        "QuantityOnSalesOrder": "quantity_on_sales_order_units",

        "WeeksOnHand": "source_weeks_on_hand",
        "WeeksOnPO": "source_weeks_on_po",
    }

    df = df.rename(columns=rename_map)

    # -----------------------------
    # Metadata
    # -----------------------------
    df["org_id"] = org_id
    df["distributor"] = "kehe"

    # KeHE report is current-state snapshot
    df["report_date"] = pd.Timestamp.today().normalize()

    df["month_year"] = (
        df["report_date"]
        .dt.to_period("M")
        .astype(str)
    )

    # -----------------------------
    # Keep only needed cols
    # -----------------------------
    keep_cols = [
        "org_id",
        "distributor",
        "report_date",
        "month_year",

        "brand",
        "dc",
        "upc",
        "sku",

        "vendor_case_pack",

        "quantity_on_hand_units",
        "quantity_on_purchase_order_units",
        "quantity_on_sales_order_units",

        "source_weeks_on_hand",
        "source_weeks_on_po",
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
        "dc",
        "upc",
        "sku",
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

        "quantity_on_hand_units",
        "quantity_on_purchase_order_units",
        "quantity_on_sales_order_units",

        "source_weeks_on_hand",
        "source_weeks_on_po",
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
    # Convert units -> cases
    # -----------------------------
    out["quantity_on_hand_cases"] = (
        out["quantity_on_hand_units"]
        / out["vendor_case_pack"]
    )

    out["quantity_on_purchase_order_cases"] = (
        out["quantity_on_purchase_order_units"]
        / out["vendor_case_pack"]
    )

    out["quantity_on_sales_order_cases"] = (
        out["quantity_on_sales_order_units"]
        / out["vendor_case_pack"]
    )

    return out
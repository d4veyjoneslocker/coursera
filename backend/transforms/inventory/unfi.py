import pandas as pd
from backend.data_pipeline.pipeline_helpers import apply_sku_map

def transform_unfi_inventory(
    df: pd.DataFrame,
    org_id: str,
) -> pd.DataFrame:

    df = df.copy()

    rename_map = {
        "Brand": "brand",
        "Name": "dc",
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
    df["distributor"] = "UNFI"

    df = apply_sku_map(df, org_id)
    df["dc"] = df["dc"].astype("string").str.strip().str.split("-").str[-1]

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
        "units_per_case",

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
        "units_per_case"
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
        * out["units_per_case"]
    )

    out["quantity_on_purchase_order_units"] = (
        out["quantity_on_purchase_order_cases"]
        * out["units_per_case"]
    )

    return out



UNFI_PO_DC_MAP = {
    "Greenwood IN DC": "GRW",
    "Howell NJ DC": "HOW",
    "Hudson Valley NY DC": "HVA",
    "Manchester PA DC": "MAN",
    "Moreno Valley CA DC": "SCAL",
    "Richburg SC DC": "RCH",
    "Ridgefield WA DC": "POR",
    "Sarasota North FL DC": "SRQ",
}


def transform_unfi_purchase_orders(
    df: pd.DataFrame,
    org_id: str,
) -> pd.DataFrame:
    """
    Transform a raw UNFI Purchase Orders export into SKUba's canonical
    purchase-order format.

    One row represents one PO × SKU line.

    This function performs source normalization only. It does not infer
    expected future orders, evaluate PO adequacy, or calculate inventory risk.
    """

    df = df.copy()

    # ------------------------------------------------------------------
    # Remove export-only columns
    # ------------------------------------------------------------------
    df = df.drop(
        columns=[col for col in df.columns if str(col).startswith("Unnamed:")],
        errors="ignore",
    )

    # ------------------------------------------------------------------
    # Rename raw UNFI columns
    # ------------------------------------------------------------------
    rename_map = {
        "PO Status": "po_status",
        "PO Number": "po_number",
        "Distribution Center": "dc_name",
        "Product Code": "vendor_item_number",
        "Product": "sku",
        "UPC": "upc",
        "Original Qty Ordered": "original_quantity_cases",
        "Revised Qty Ordered": "revised_quantity_cases",
        "PO Create Date": "po_create_date",
        "Order Requested Date": "order_requested_date",
        "Qty Received": "received_quantity_cases",
        "Original ETA Date": "original_eta_date",
        "Revised ETA Date": "revised_eta_date",
        "Delivery Appointment Date": "delivery_appointment_date",
        "Landed Date": "landed_date",
        "Received Date": "received_date",
        "Revised Pickup Date": "revised_pickup_date",
        "PO Amount": "po_amount",
        "Off Invoice Allowance": "off_invoice_allowance",
        "Line Purchase Price": "line_purchase_price",
        "Weight": "weight",
        "Delivery Method": "delivery_method",
        "Transaction Master Cases": "transaction_master_cases",
        "PO Buyer Name": "po_buyer_name",
        "Ship From Address": "ship_from_address",
        "Ship From City": "ship_from_city",
        "Ship From State": "ship_from_state",
        "Ship From Zip": "ship_from_zip",
        "On-Time Status": "on_time_status",
        "Delivered in Full": "delivered_in_full",
    }

    df = df.rename(columns=rename_map)

    # ------------------------------------------------------------------
    # Add SKUba identifiers
    # ------------------------------------------------------------------
    df["org_id"] = org_id
    df["distributor"] = "UNFI"

    # Keep the original UNFI DC name AND our normalized DC code.
    df["dc"] = df["dc_name"].map(UNFI_PO_DC_MAP)
    df = apply_sku_map(df, org_id)

    # Fail loudly if UNFI introduces a DC we haven't mapped yet.
    unmapped_dcs = (
        df.loc[df["dc"].isna(), "dc_name"]
        .dropna()
        .unique()
        .tolist()
    )

    if unmapped_dcs:
        raise ValueError(
            f"Unmapped UNFI purchase-order DCs: {unmapped_dcs}"
        )

    # ------------------------------------------------------------------
    # Normalize identifiers
    # ------------------------------------------------------------------
    df["po_number"] = df["po_number"].astype("string").str.strip()
    df["vendor_item_number"] = (
        df["vendor_item_number"].astype("string").str.strip()
    )

    # Keep UPC as a string so leading zeroes aren't lost downstream.
    df["upc"] = (
        df["upc"]
        .astype("string")
        .str.replace(r"\.0$", "", regex=True)
        .str.replace(r"\D", "", regex=True)
    )

    # ------------------------------------------------------------------
    # Normalize dates
    # ------------------------------------------------------------------
    date_columns = [
        "po_create_date",
        "order_requested_date",
        "original_eta_date",
        "revised_eta_date",
        "delivery_appointment_date",
        "landed_date",
        "received_date",
        "revised_pickup_date",
    ]

    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.normalize()

    # ------------------------------------------------------------------
    # Normalize numeric fields
    # ------------------------------------------------------------------
    numeric_columns = [
        "original_quantity_cases",
        "revised_quantity_cases",
        "received_quantity_cases",
        "po_amount",
        "off_invoice_allowance",
        "line_purchase_price",
        "weight",
        "transaction_master_cases",
    ]

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["open_quantity_cases"] = df["revised_quantity_cases"].fillna(df["original_quantity_cases"]) - df["received_quantity_cases"].fillna(0)

    # ------------------------------------------------------------------
    # Normalize categorical/text fields
    # ------------------------------------------------------------------
    text_columns = [
        "po_status",
        "dc_name",
        "sku",
        "delivery_method",
        "po_buyer_name",
        "ship_from_address",
        "ship_from_city",
        "ship_from_state",
        "ship_from_zip",
        "on_time_status",
        "delivered_in_full",
    ]

    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    # ------------------------------------------------------------------
    # Canonical column order
    # ------------------------------------------------------------------
    columns = [
        "org_id",
        "distributor",
        "po_number",
        "po_status",

        "dc",
        "dc_name",

        "vendor_item_number",
        "sku",
        "upc",

        "original_quantity_cases",
        "revised_quantity_cases",
        "received_quantity_cases",
        "open_quantity_cases",

        "po_create_date",
        "order_requested_date",
        "original_eta_date",
        "revised_eta_date",
        "delivery_appointment_date",
        "landed_date",
        "received_date",
        "revised_pickup_date",

        "delivery_method",
        "on_time_status",
        "delivered_in_full",

        "po_amount",
        "off_invoice_allowance",
        "line_purchase_price",
        "weight",
        "transaction_master_cases",

        "po_buyer_name",

        "ship_from_address",
        "ship_from_city",
        "ship_from_state",
        "ship_from_zip",
    ]

    # Only select columns that actually exist in the export.
    columns = [col for col in columns if col in df.columns]

    df = df[columns].copy()

    # ------------------------------------------------------------------
    # Stable ordering
    # ------------------------------------------------------------------
    df = df.sort_values(
        ["po_create_date", "po_number", "dc", "upc"],
        na_position="last",
    ).reset_index(drop=True)

    return df



def transform_unfi_projected_orders(
    df: pd.DataFrame,
    org_id: str,
) -> pd.DataFrame:
    """
    Transform a raw UNFI Projected Orders Detail export into SKUba's
    canonical projected-order format.

    One row represents one projected DC × SKU order.

    This function performs source normalization only. It does not evaluate
    whether the projected order is sufficient or calculate inventory risk.
    """
    df = df.copy()

    # Remove export-only columns
    df = df.drop(
        columns=[col for col in df.columns if str(col).startswith("Unnamed:")],
        errors="ignore",
    )

    # Rename raw UNFI columns
    rename_map = {
        "DC Code": "dc_name",
        "Product Code": "vendor_item_number",
        "Product": "sku",
        "UPC": "upc",
        "Projected Order Date": "projected_order_date",
        "Projected Order Quantity": "projected_order_cases",
    }

    df = df.rename(columns=rename_map)

    # Add SKUba identifiers
    df["org_id"] = org_id
    df["distributor"] = "UNFI"
    df["dc"] = (
        df["dc_name"]
        .astype("string")
        .str.strip()
        .replace({
            "MOR": "SCAL",
            "RID": "POR",
        })
    )
    df = apply_sku_map(df, org_id)

    # Normalize identifiers
    df["vendor_item_number"] = (
        df["vendor_item_number"]
        .astype("string")
        .str.strip()
    )

    df["upc"] = (
        df["upc"]
        .astype("string")
        .str.replace(r"\.0$", "", regex=True)
        .str.replace(r"\D", "", regex=True)
    )

    # Normalize projected order fields
    df["projected_order_date"] = pd.to_datetime(
        df["projected_order_date"],
        errors="coerce",
    ).dt.normalize()

    df["projected_order_cases"] = pd.to_numeric(
        df["projected_order_cases"],
        errors="coerce",
    )

    # Normalize text
    for col in ["dc_name", "sku"]:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    columns = [
        "org_id",
        "distributor",
        "dc",
        "dc_name",
        "vendor_item_number",
        "sku",
        "upc",
        "units_per_case",
        "projected_order_date",
        "projected_order_cases",
    ]

    columns = [col for col in columns if col in df.columns]

    return (
        df[columns]
        .sort_values(
            ["projected_order_date", "dc", "upc"],
            na_position="last",
        )
        .reset_index(drop=True)
    )
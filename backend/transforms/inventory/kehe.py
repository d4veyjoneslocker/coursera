import pandas as pd
from backend.data_pipeline.pipeline_helpers import apply_sku_map


def transform_kehe_inventory(df: pd.DataFrame, org_id: str, inventory_as_of_date=None) -> pd.DataFrame:

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
    df["distributor"] = "KEHE"

    kehe_dc_map = {
    "Aurora, CO": "AUR",
    "Bloomington, IN": "BLO",
    "Chino A, CA": "CHN",
    "Dallas/Fort Worth, TX": "DFW",
    "Douglasville, GA": "DGV",
    "Lehigh Valley, PA": "LHV",
    "Miami, FL": "MIA",
    "North East Maryland, MD": "EMD",
    "Phoenix, AZ": "PHX",
    "Portland, OR": "POR",
    "Stockton, CA": "NCA",
    }

    df["dc"] = df["dc"].replace(kehe_dc_map)

    # KeHE report is current-state snapshot
    inventory_as_of_date = pd.Timestamp.today().normalize() if inventory_as_of_date is None else pd.Timestamp(inventory_as_of_date).normalize()
    df["report_date"] = inventory_as_of_date

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

    df = apply_sku_map(df, org_id)
    out = df[keep_cols + ["units_per_case"]].copy()

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
            out[col].astype(str).str.replace(",", "", regex=False),
            errors="coerce",
        )

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


KEHE_PROJECTION_DC_MAP = {
    "AURORA (12)": "AUR",
    "BLOOMINGTON (16)": "BLO",
    "CHINO (41)": "CHN",
    "DALLAS (19)": "DFW",
    "DOUGLASVILLE (55)": "DGV",
    "EAST MARYLAND (27)": "EMD",
    "FT. LAUDERDALE(31)": "MIA",
    "LEHIGH VALLEY (15)": "LHV",
    "NOR CAL(33)": "NCA",
    "PHOENIX (14)": "PHX",
    "PORTLAND (25)": "POR",
}


def transform_kehe_order_projections(
    df: pd.DataFrame,
    org_id: str,
    projection_as_of_date=None,
) -> pd.DataFrame:
    """
    Transform a raw KeHE Order Projection report into SKUba's
    canonical forward-order projection format.

    One row = DC × UPC × projected week.
    """

    df = df.copy()

    df = df.rename(
        columns={
            "dc_name": "dc_name",
            "proj_date2": "projected_order_date",
            "brand_name": "brand",
            "upc": "upc",
            "item_description": "sku",
            "Item_Projection_Week": "projected_order_units",
        }
    )

    df["org_id"] = org_id
    df["distributor"] = "KEHE"

    projection_as_of_date = pd.Timestamp.today().normalize() if projection_as_of_date is None else pd.Timestamp(projection_as_of_date).normalize()
    df["projection_as_of_date"] = projection_as_of_date

    # DC normalization
    df["dc_name"] = df["dc_name"].astype("string").str.strip()
    df["dc"] = df["dc_name"].map(KEHE_PROJECTION_DC_MAP)
    df = apply_sku_map(df,org_id)

    unmapped_dcs = (
        df.loc[df["dc"].isna(), "dc_name"]
        .dropna()
        .unique()
        .tolist()
    )

    if unmapped_dcs:
        raise ValueError(
            f"Unmapped KeHE projection DCs: {unmapped_dcs}"
        )

    # UPC normalization
    df["upc"] = (
        df["upc"]
        .astype("string")
        .str.replace(r"\.0$", "", regex=True)
        .str.replace(r"\D", "", regex=True)
        .str.lstrip("0")
    )

    # Date normalization
    df["projected_order_date"] = pd.to_datetime(
        df["projected_order_date"],
        errors="coerce",
    ).dt.normalize()

    # Projection quantity
    df["projected_order_units"] = pd.to_numeric(
        df["projected_order_units"],
        errors="coerce",
    )

    # Text cleanup
    for col in ["brand", "sku"]:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    columns = [
        "org_id",
        "distributor",
        "projection_as_of_date",
        "projected_order_date",
        "dc",
        "dc_name",
        "brand",
        "upc",
        "sku",
        "projected_order_units",
        "units_per_case"
    ]

    df = df[columns].copy()

    df = df.sort_values(
        ["projected_order_date", "dc", "upc"],
        na_position="last",
    ).reset_index(drop=True)

    return df
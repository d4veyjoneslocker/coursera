import pandas as pd
import numpy as np
from backend.mappings.channel import channel_map
from backend.transforms.set_distributor_data_types import set_data_types
from backend.data_pipeline.pipeline_helpers import apply_sku_map, extract_chain_store_number_full_pod

def transform_kehe_full_pod_vendor(df, org_id):

    # Convert date columns to datetime format
    date_columns = ['DateRangeEnd', 'DateRangeStart_Month']
    for col in date_columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')


    # Renaming columns to keep untransformed

    df = df.rename(columns={
        'Addressline1': 'street_address',
        'CurrentYearQTY': 'units',
        'CustomerCity': 'city',
        'CustomerName': 'customer_name',
        'CustomerStateCode': 'state',
        'DC': 'dc',
        'PriorYearCost': 'revenue_py',
        'PriorYearQty': 'units_py',
        'ProductSize': 'fl_oz',
        'UPC': 'upc',
    })


    # Adding new columns
    #------------------------------------------------------------

    # Time columns

    df["year"] = df["DateRangeStart_Month"].dt.year
    df["month"] = df["DateRangeStart_Month"].dt.month
    df["month_year"] = df["DateRangeStart_Month"].dt.to_period("M")

    # Distributor (hard coded)
    df["distributor"] = "KEHE"

    # Normalize across Sprouts areas
    df["chain"] = np.where(
        df["RetailerName"].str.startswith("Sprouts"), "SPROUTS", 
        df["RetailerName"].str.upper()
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

    # Convert zip code to 5-digit string
    df["zip"] = df["CustomerPostalCode"].astype(str).str[:5]
    # Adjust Sprouts store numbers

    df["store_number"] = np.where(
        df["chain"] == "SPROUTS", df["customer_name"].str[8:11].str.strip("#- T").astype(str),
        df["AddressBookNumber"]
    )

    df["chain_store_number"] = (
        df["customer_name"]
        .apply(extract_chain_store_number_full_pod)
        .astype("string")
    )

    df["chain_store_key"] = (
        df["chain"].astype("string").str.strip().str.upper()
        + "|"
        + df["chain_store_number"]
    )

    # Fix Sprouts addresses

    df.loc[
        (df["chain"] == "SPROUTS") & (df["store_number"]=="650"), "street_address"
        ] = "330 BUENA VISTA BLVD STE 111"
    
    df.loc[
        (df["chain"] == "SPROUTS") & (df["store_number"]=="651"), "street_address"
        ] = "12500 LAKE UNDERHILL RD STE 11"

    # Map SKUs using sku_map

    df["sku"] = df["ProductDescription"]
    df = apply_sku_map(df, org_id)

    # Map Channels using channel_map + fix Sprouts channels

    df["channel"] = df["Channel"].map(channel_map)
    df["channel"] = np.where(
        df["chain"] == "SPROUTS", "GROCERY",
        df["channel"]
    )

    # adding coded customer helper

    df["coded_customer"] = df["chain"].astype(str) + " " + df["city"].astype(str) + " " + df["store_number"].astype(str)


    #Removes currency symbols from CurrentYearCost and casts it as an int
    df["revenue"] = (
        df["CurrentYearCost"]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("(", "-", regex=False)
        .str.replace(")", "", regex=False)
        .str.strip()
    )

    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce")


    # groups by coded_customer to get rid of Sprouts duplicates due to customer name changes

    df = df.groupby(
    ["coded_customer", "sku", "month_year"], as_index=False
        ).agg({
            "customer_name": "first",
            "chain_store_number": "first",
            "chain_store_key": "first",
            "store_number": "first",
            "chain": "first",
            "street_address": "first",
            "city": "first",
            "state": "first",
            "zip": "first",
            "channel": "first",
            "upc": "first",
            "distributor": "first",
            "dc": "first",
            "year": "first",
            "month": "first",
            "revenue": "sum",
            "units": "sum",
        })
    

    
    df["helper"] = df["coded_customer"] + "-" + df["sku"] + "-" + df["month_year"].astype(str)
    df["pod_helper"] = df["coded_customer"] + "-" + df["sku"]
    
    df = set_data_types(df)
    

    #------------------------------------------------------------

    # selecting and ordering columns

    df = df[
        [
            "helper",
            "pod_helper",
            "coded_customer",
            "customer_name",
            "chain_store_key",
            "chain_store_number",
            "store_number",
            "chain",
            "street_address",
            "city",
            "state",
            "zip",
            "channel",
            "upc",
            "sku",
            "distributor",
            "dc",
            "year",
            "month",
            "month_year",
            "revenue",
            "units",
        ]
    ]

    return df
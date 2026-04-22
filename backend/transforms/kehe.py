import pandas as pd
import numpy as np
from backend.mappings.sku import sku_map
from backend.mappings.channel import channel_map
from backend.transforms.set_distributor_data_types import set_data_types

def transform_kehe_full_pod_vendor(df):
    # Convert date columns to datetime format
    date_columns = ['DateRangeEnd', 'DateRangeStart_Month']
    for col in date_columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    # Renaming columns to keep untransformed

    df = df.rename(columns={
        'AddressLine1': 'street_address',
        'CurrentYearCost': 'revenue',
        'CurrentYearQty': 'units',
        'CustomerCity': 'city',
        'CustomerName': 'customer_name',
        'CustomerStateCode': 'state',
        'Dc': 'dc',
        'PriorYearCost': 'revenue_py',
        'PriorYearQty': 'units_py',
        'ProductSize': 'fl_oz',
        'Upc': 'upc',
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

    # Convert zip code to 5-digit string
    df["zip"] = df["CustomerPostalCode"].str[:5].astype(str)

    # Adjust Sprouts store numbers

    df["store_number"] = np.where(
        df["chain"] == "SPROUTS", df["customer_name"].str[8:11].str.strip("#- T").astype(str),
        df["AddressBookNumber"]
    )

    # Fix Sprouts addresses

    df.loc[
        (df["chain"] == "SPROUTS") & (df["store_number"]=="650"), "street_address"
        ] = "330 BUENA VISTA BLVD STE 111"
    
    df.loc[
        (df["chain"] == "SPROUTS") & (df["store_number"]=="651"), "street_address"
        ] = "12500 LAKE UNDERHILL RD STE 11"

    # Map SKUs using sku_map

    df["sku"] = df["ProductDescription"].map(sku_map)

    # Map Channels using channel_map + fix Sprouts channels

    df["channel"] = df["Channel"].map(channel_map)
    df["channel"] = np.where(
        df["chain"] == "SPROUTS", "GROCERY",
        df["channel"]
    )

    # adding coded customer helper

    df["coded_customer"] = df["chain"].astype(str) + " " + df["city"].astype(str) + " " + df["store_number"].astype(str)

    # groups by coded_customer to get rid of Sprouts duplicates due to customer name changes

    df = df.groupby(
    ["coded_customer", "sku", "month_year"], as_index=False
        ).agg({
            "customer_name": "first",
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
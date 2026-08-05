import pandas as pd
import numpy as np
from backend.mappings.channel import channel_map
from backend.mappings.upc import upc_map
from backend.data_pipeline.pipeline_helpers import apply_sku_map
from backend.transforms.set_distributor_data_types import set_data_types
from backend.transforms.whole_foods_id import add_whole_foods_flags

def transform_unfi_natural_vendor_sales(df, org_id):

    # Convert date columns to datetime format
    date_columns = ['SalesPeriodEnd', 'SalesPeriodStart_Week']
    for col in date_columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    # Renaming columns to keep untransformed

    df = df.rename(columns={
        'Warehouse': 'dc',
        'TotalSales': 'revenue',
    })

    # Adding new columns
    #------------------------------------------------------------

    # Time columns

    df["year"] = df["SalesPeriodStart_Week"].dt.year
    df["month"] = df["SalesPeriodStart_Week"].dt.month
    df["month_year"] = df["SalesPeriodStart_Week"].dt.to_period("M")

    # Distributor (hard coded)
    df["distributor"] = "UNFI"

    # convert cases to units

    df["units"] = df["TotalQuantityShipped"] * 8

    # map Channels

    df["channel"] = df["ChannelDesc"].map(channel_map)

    # map SKUs

    df["sku"] = df["Description"]
    df = apply_sku_map(df, org_id)

    # map UPCs

    df["upc"] = df["Upc"].map(upc_map)

    # fix chains (Doordash)

    df["chain"] = np.select(
        [
         df["ChainName"].str.startswith("DOOR"),
         df["ChainName"].str.startswith("WAKEFERN")   
        ],
        [
         "DOORDASH",
         "SHOPRITE"
        ],
        df["ChainName"].str.upper()
    )

    df["chain"] = np.select(
        [
         df["ChainName"].str.startswith("ALB/SWY"),
         df["ChainName"].str.startswith("ALBERTSONS"),
         df["ChainName"].str.startswith("SAFEWAY"),
         df["ChainName"].str.startswith("SWY/CARRS"), 
        ],
        [
         "ALBERTSONS/SAFEWAY",
         "ALBERTSONS/SAFEWAY",
         "ALBERTSONS/SAFEWAY",
         "ALBERTSONS/SAFEWAY",
        ],
        df["ChainName"].str.upper()
    )

    # convert zip

    df["zip_length"] = df["Zip"].astype(str).str.len()

    df["zip"] = np.where(
        df["zip_length"] == 4, "0" + df["Zip"].astype(str),
        df["Zip"].astype(str),
    )

    df["state"] = df["State"].str.upper()
    
    # map Whole Foods

    df = add_whole_foods_flags(df, "backend/mappings/whole_foods.csv")

    # Updated chain for WF and fill in chain blanks as "Independent"

    df["chain"] = np.select(
        [
            df["is_whole_foods"],
            (df["chain"].isna()) | (df["chain"] == "")            
        ],
        [
            "WHOLE FOODS",
            "INDEPENDENT"
        ],
        df["chain"].str.upper()
    )

    # Update store number for WF

    df["store_number"] = np.where(
        df["chain"] == "WHOLE FOODS", df["wf_Store_Number"].astype(str),
        df["CustomerAccount"].astype(str)
    )

    # Update street address for WF 

    df["street_address"] = np.where(
        df["chain"] == "WHOLE FOODS", df["wf_Street"].str.upper(),
        df["CustomerAddress"].str.upper()
    )

    # Update city for WF

    df["city"] = np.where(
        df["chain"] == "WHOLE FOODS", df["wf_City"].str.upper(),
        df["City"].str.upper()
    )

    # Update state for WF

    df["state"] = np.where(
        df["chain"] == "WHOLE FOODS", df["wf_State"],
        df["state"]
    )

    # Update customer name for WF

    df["customer_name"] = np.where(
        df["chain"] == "WHOLE FOODS", df["wf_Store_Name"].str.upper(),
        df["CustomerName"].str.upper()
    )

    # Create coded customer name, combining chain/store name and store number (or zip for confidential)

    df["coded_customer"] = np.select(
        [
            df["chain"] == "WHOLE FOODS",
            df["chain"] == "SHOPRITE",
            df["chain"] == "CONFIDENTIAL"
        ],

        [df["customer_name"].str.upper() + " " + df["store_number"].astype(str),
         "SHOPRITE" + " " + df["store_number"].astype(str),
         "CONFIDENTIAL" + " " + df["zip"].astype(str)
        ],
        df["chain"].astype(str) + " " + df["city"].astype(str) + " " + df["store_number"].astype(str)
    )

    # Aggregating all entries in the same month into 1 row
    df = (
    df.groupby([
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
        "possible_whole_foods"
        ], as_index=False, dropna=False)
      .agg({
          "units": "sum",
          "revenue": "sum",
      })
    )


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
            "possible_whole_foods"
        ]
    ]

    return df





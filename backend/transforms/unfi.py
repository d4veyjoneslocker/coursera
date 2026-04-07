import pandas as pd
import numpy as np
from mappings.sku import sku_map
from mappings.channel import channel_map
from mappings.upc import upc_map

def transform_unfi_natural_vendor_sales(df):
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

    df["sku"] = df["Description"].map(sku_map)

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

    # convert zip

    df["zip_length"] = df["Zip"].astype(str).str.len()

    df["zip"] = np.where(
        df["zip_length"] == 4, "0" + df["Zip"].astype(str),
        df["Zip"].astype(str),
    )
    
    # map Whole Foods

    wf_map = pd.read_csv("mappings/whole_foods.csv", dtype={"zip": str})

    df = df.merge(wf_map, on="zip", how="left")

    # Updated chain for WF and fill in chain blanks as "Independent"

    df["chain"] = np.select(
        [
            (df["wf_Chain"] == "Whole Foods") & (df["chain"] == "CONFIDENTIAL"),
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
        df["State"].str.upper()
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
        ], as_index=False)
      .agg({
          "units": "sum",
          "revenue": "sum",
      })
    )

    #------------------------------------------------------------

    # selecting and ordering columns

    df = df[
        [
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





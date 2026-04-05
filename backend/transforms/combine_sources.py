import pandas as pd
import numpy as np
from crisp_data_pull_generic import pull_crisp_data

def combine_distributors(unfi, kehe):

    # combining unfi and kehe dataframes
    combined = pd.concat([unfi, kehe], ignore_index=True)

    # setting data types of key columns

    combined["store_number"] = combined["store_number"].astype(str)
    combined["sku"] = combined["sku"].astype(str)

    combined["month_year"] = (
        pd.to_datetime(
            combined["month_year"].astype(str).str.strip(),
            format="%Y-%m",
            errors="coerce"
            )
        .dt.to_period("M")
    )

    combined["units"] = pd.to_numeric(combined["units"], errors="coerce")
    combined["revenue"] = pd.to_numeric(combined["revenue"], errors="coerce")
    combined["month"] = pd.to_numeric(combined["month"], errors="coerce")
    combined["year"] = pd.to_numeric(combined["year"], errors="coerce")

    # add helper column (customer name, store number, sku, month, year)

    combined.insert(0, "helper", combined["coded_customer"] + "-" + combined["sku"] + "-" + combined["month_year"].astype(str))
    combined.insert(1, "pod_helper", combined["coded_customer"] + "-" + combined["sku"])

    # remove NAs

    combined = combined.dropna(subset=["customer_name"])
    
    # return combined table

    return combined
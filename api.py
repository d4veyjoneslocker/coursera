
from fastapi import FastAPI
import pandas as pd
from serving.filter_table import filter_table

app = FastAPI()

monthly_summary = pd.read_parquet("monthly_summary.parquet")

#@app.get("/units")
#def units(chain: str = None, sku: str = None, retailer: str = None):
#    filters = {
#        "chain": chain,
#        "sku": sku,
#        "retailer": retailer
#    }
    
#    df = get_metric_timeseries(monthly_summary, "units", **filters)
#    return df.to_dict(orient="records")

@app.get("/units")
def units(chain: str = None):
    df = filter_table(monthly_summary, chain=chain)

    df = df.reset_index()

    df = df[["month_year", "units"]]
    df["month_year"] = df["month_year"].astype(str)

    return df.to_dict(orient="records")

import pandas as pd
from backend.data_pipeline.pipeline_helpers import apply_sku_map

def transform_whole_foods_data(df: pd.DataFrame, org_id: str) -> pd.DataFrame:

    df = df.copy

    df = df.map(lambda x: x.upper() if isinstance(x, str) else x)

    rename_map = {
        "Store Number": "store_number",
        "Store Name": "customer_name",
        "Region": "wf_region",
        "Channel Type": "purchase_method",
        "Net Sales": "net_sales",
        "Unit Sales": "net_unit_sales",
        "Gross Sales": "gross_sales",
        "Return Sales": "return_sales",
        "Gross Units": "gross_units",
        "Return Units": "return_units",
    }

    df = df.rename(columns=rename_map)

    df["week_end_date"] = pd.to_datetime(
        df["Week Desc"].astype(str)
        .str.replace("Week Ending", "", regex=False)
        .str.strip()
    )

    df["year"] = df["week_end_date"].dt.year
    df["month"] = df["week_end_date"].dt.month
    df["month_year"] = df["week_end_date"].dt.to_period("M")

    df["chain"] = "WHOLE FOODS"

    df["sku"] = df["Item Description"]
    df = apply_sku_map(df, org_id)

    df["coded_customer"] = "chain" + " " + "store_name" + " " + "store_number"
    df["helper"] = df["coded_customer"] + "-" + df["sku"] + df["month_year"].astype(str)
    df["method_helper"] = df["coded_customer"] + "-" + df["purchase_method"] + "-" + df["sku"] + df["month_year"].astype(str)
    df["pod_helper"] = df["coded_customer"] + "-" + df["month_year"].astype(str)

    df = (
        df.groupby([
            "helper",
            "method_helper",
            "pod_helper",
            "coded_customer",
            "customer_name",
            "store_number",
            "chain",
            "purchase_method",
            "upc", #needs to be mapped
            "sku",
            "week_end_date",
            "year",
            "month",
            "month_year",
            ], as_index=False, dropna=False)
        .agg({
            "net_revenue": "sum",
            "net_unit_sales": "sum",
            "gross_revenue": "sum",
            "return_revenue": "sum",
            "gross_units": "sum",
            "return_units": "sum"
        })
        )

    df["avg_retail_price"] = (df["net_revenue"] / df["net_unit_sales"])


    df = df[
            [
                "helper",
                "method_helper",
                "pod_helper",
                "coded_customer",
                "customer_name",
                "store_number",
                "chain",
                "purchase_method",
                "upc", #needs to be mapped
                "sku",
                "week_end_date",
                "year",
                "month",
                "month_year",
                "net_revenue",
                "net_unit_sales",
                "avg_retail_price",
                "gross_revenue",
                "return_revenue",
                "gross_units",
                "return_units",
            ]
        ]





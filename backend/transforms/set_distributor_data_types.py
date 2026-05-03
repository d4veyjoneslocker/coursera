import pandas as pd

def set_data_types(df):
    df = df.copy()

    if "store_number" in df.columns:
        df["store_number"] = df["store_number"].astype(str)

    if "sku" in df.columns:
        df["sku"] = df["sku"].astype(str)

    if "month_year" in df.columns:
        df["month_year"] = (
            pd.to_datetime(
                df["month_year"].astype(str).str.strip(),
                format="%Y-%m",
                errors="coerce"
            )
            .dt.to_period("M")
        )

    for col in ["units", "revenue", "month", "year"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df
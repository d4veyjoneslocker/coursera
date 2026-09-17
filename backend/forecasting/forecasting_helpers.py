import pandas as pd


def add_expected_delivery_date(
    df: pd.DataFrame,
    order_date_col: str,
    lead_time_col: str = "median_replenishment_days",
) -> pd.DataFrame:
    df = df.copy()
    df[order_date_col] = pd.to_datetime(df[order_date_col], errors="coerce")
    df["expected_delivery_date"] = df[order_date_col] + pd.to_timedelta(df[lead_time_col], unit="D")
    return df
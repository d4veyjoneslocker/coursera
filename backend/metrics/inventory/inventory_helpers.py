import pandas as pd

def get_latest_unfi_dc_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df["distributor"] == "UNFI"].copy()
    df["report_date"] = pd.to_datetime(df["report_date"])

    latest_dates = (
        df.groupby("dc", as_index=False)["report_date"]
        .max()
        .rename(columns={"report_date": "latest_report_date"})
    )

    df = df.merge(latest_dates, on="dc", how="inner")

    return df[
        df["report_date"] == df["latest_report_date"]
    ].drop(columns="latest_report_date")
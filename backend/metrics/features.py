import pandas as pd
from backend.data_validation.phase_1 import validate_first_pod_flag
import numpy as np

def calculate_store_health_status_monthly(df):

    today = pd.Timestamp.today()
    current_period = pd.Period(today, freq="M")

    # last full month
    last_full_month = current_period - 1

    # only keep data up to last full month
    df = df[df["month_year"] <= last_full_month]

    current_month = df["month_year"].max()

    table = df.groupby(
        ["coded_customer"] + 
        ["first_month_purchased",
        "second_to_last_month_purchased",
        "last_month_purchased"], dropna=False
        ).agg(
            units = ("units", "sum"),
            revenue = ("revenue", "sum")
        ).reset_index()
    

    table["status"] = ""

    conditions = [
        table["first_month_purchased"] >= (current_month),
        table["last_month_purchased"] <= (current_month - 5),
        table["last_month_purchased"] <= (current_month - 3),
        (table["last_month_purchased"] >= (current_month - 2)) & (table["second_to_last_month_purchased"] <= (current_month - 5)),
        table["last_month_purchased"] >= (current_month - 2),
    ]

    choices = [
        "New",
        "Inactive",
        "Struggling",
        "Revived",
        "Healthy"
    ]

    table["status"] = np.select(conditions, choices, default="-")

    table = table[
        ["coded_customer"] + 
        ["first_month_purchased",
        "second_to_last_month_purchased",
        "last_month_purchased",
        "status",
        "units",
        "revenue"]
    ]

    return table


def add_features(df):
    df = df.copy()

    df["first_month_purchased"] = (
        df.groupby("coded_customer")["month_year"].transform("min")
    )

    df["last_month_purchased"] = (
        df.groupby("coded_customer")["month_year"].transform("max")
    )

    df["second_to_last_month_purchased"] = (
        df.groupby("coded_customer")["month_year"]
        .transform(
            lambda x: (
                x.drop_duplicates().nlargest(2).iloc[-1]
                if len(x.drop_duplicates()) > 1
                else pd.Period("NaT", freq="M")
            )
    )
    )

    df["second_to_last_month_purchased"] = df["second_to_last_month_purchased"].astype("period[M]")

    df["first_store_flag"] = (
        df["month_year"] == df["first_month_purchased"]
    )

    df["first_month_purchased_sku"] = (
        df.groupby("pod_helper")["month_year"].transform("min")
    )

    df["first_pod_flag"] = (
        df["month_year"] == df["first_month_purchased_sku"]
    )

    df["reorder_flag"] = ~df["first_store_flag"]

    df["reorder_flag_pod"] = ~df["first_pod_flag"]

    df["count"] = 1

    status_table = calculate_store_health_status_monthly(df)

    df = df.merge(
        status_table[["coded_customer", "status"]].drop_duplicates(),
        on="coded_customer",
        how="left")
    

    # ADD THIS TEST BACK IN

    #validate_first_pod_flag(df)

    return df

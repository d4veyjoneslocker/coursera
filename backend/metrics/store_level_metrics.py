import pandas as pd
import numpy as np
from filters.filters import non_time_filter
from metrics.features import add_month_features


def calculate_store_health_status(df):

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
        table["first_month_purchased"] >= (current_month - 1),
        table["last_month_purchased"] <= (current_month - 5),
        table["last_month_purchased"] <= (current_month - 3),
        (table["last_month_purchased"] >= (current_month - 2)) & (table["last_month_purchased"] <= (current_month - 5)),
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


def calculate_reorder_stats(df):


    df = df.groupby(["coded_customer","month_year"],as_index=False
    ).agg(
        units = ("units", "sum"),
        revenue = ("revenue", "sum"),
    ).reset_index().sort_values("month_year", ascending=False)

    df_w_features = add_month_features(df)

    table = df_w_features.groupby(
        ["coded_customer"], dropna=False
        ).agg(
            units = ("units", "sum"),
            revenue = ("revenue", "sum"),
            reorders =("reorder_flag","sum")
        ).reset_index().sort_values("reorders",ascending=False)
    
    return table

def calculate_store_vpo(df):

    result = (
        df.groupby("coded_customer", dropna=False)
            .agg(
                active_pods = ("count", "sum"),
                volume = ("units", "sum")
            ).reset_index()
        )

    result["vpo"] = result["volume"]/result["active_pods"]/4

    return result[["coded_customer", "vpo", "active_pods", "volume"]]

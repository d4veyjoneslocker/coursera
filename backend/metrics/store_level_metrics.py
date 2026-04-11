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

def calculate_store_health_status_monthly(df):

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

# CUSTOMER LEVEL REORDER STATS

def calculate_reorder_stats(df):

    df = df.groupby(["coded_customer","month_year"],as_index=False
    ).agg(
        units = ("units", "sum"),
        revenue = ("revenue", "sum"),
        status=("status", "first"),
        first_month_purchased=("first_month_purchased", "first"),
        second_to_last_month_purchased=("second_to_last_month_purchased", "first"),
        last_month_purchased=("last_month_purchased", "first")
    ).reset_index().sort_values("month_year", ascending=False)

    df["first_store_flag"] = (
        df["month_year"] == df["first_month_purchased"]
    )

    df["reorder_flag"] = ~df["first_store_flag"]

    table = df.groupby(
        ["coded_customer"], dropna=False
        ).agg(
            units = ("units", "sum"),
            revenue = ("revenue", "sum"),
            status=("status", "first"),
            first_month_purchased=("first_month_purchased", "first"),
            second_to_last_month_purchased=("second_to_last_month_purchased", "first"),
            last_month_purchased=("last_month_purchased", "first"),
            reorders =("reorder_flag","sum"),
        ).reset_index().sort_values("reorders",ascending=False)
    
    return table

# MONTH-LEVEL REORDER STATS

def calculate_reorder_stats_monthly(df):

    df_w_features = add_month_features(df)

    df_w_features = df_w_features.groupby(["coded_customer","month_year"],as_index=False
    ).agg(
        reorder = ("reorder_flag","max"),
        new_store = ("first_store_flag","max")
    ).reset_index()

    result = df_w_features.groupby(["month_year"]).agg(
        reorders = ("reorder","sum"),
        new_stores = ("new_store","sum")
    ).reset_index()

    result["prior_store_base"] = (
        result["new_stores"]
        .cumsum()
        .shift(1)
        .fillna(0)
    )

    result["reorder_rate"] = np.where(
        result["prior_store_base"] > 0,
        result["reorders"] / result["prior_store_base"],
        0
    )

    result["month_year"] = result["month_year"].astype(str)
    
    return result

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


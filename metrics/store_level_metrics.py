import pandas as pd
import numpy as np
from filters.filters import non_time_filter


def calculate_store_health_status(df):
    table = df.groupby(
        ["coded_customer"] + 
        non_time_filter + 
        ["first_month_purchased",
        "second_to_last_month_purchased",
        "last_month_purchased"], dropna=False
        ).agg(
            units = ("units", "sum"),
            revenue = ("revenue", "sum")
        ).reset_index()
    
    current_month = df["month_year"].max()

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
        non_time_filter + 
        ["first_month_purchased",
        "second_to_last_month_purchased",
        "last_month_purchased",
        "status",
        "units",
        "revenue"]
    ]

    return table

#def calculate_reorder_rate(df):
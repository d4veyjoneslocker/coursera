import pandas as pd
from backend.data_validation.phase_1 import validate_first_pod_flag
import numpy as np

def calculate_store_health_status_monthly(df):
    df = df.copy()

    if df.empty:
        return pd.DataFrame(columns=[
            "coded_customer",
            "first_month_purchased",
            "second_to_last_month_purchased",
            "last_month_purchased",
            "status",
            "units",
            "revenue",
        ])

    # 🔥 Use latest available month (includes current month)
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
        table["first_month_purchased"] >= (current_month-1),
        table["last_month_purchased"] <= (current_month - 6),
        table["last_month_purchased"] <= (current_month - 3),
        (table["last_month_purchased"] >= (current_month - 2)) & (table["second_to_last_month_purchased"] <= (current_month - 6)),
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

def calculate_store_sku_status_monthly(df):
    df = df.copy()

    if df.empty:
        return pd.DataFrame(columns=[
            "pod_helper",
            "coded_customer",
            "sku",
            "sku_first_month_purchased",
            "sku_second_to_last_month_purchased",
            "sku_last_month_purchased",
            "sku_status",
            "units",
            "revenue",
        ])

    current_month = df["month_year"].max()

    sku_grain = ["pod_helper"]

    table = (
        df.groupby(
            sku_grain
            + [
                "coded_customer",
                "sku",
                "sku_first_month_purchased",
                "sku_second_to_last_month_purchased",
                "sku_last_month_purchased",
            ],
            dropna=False,
        )
        .agg(
            units=("units", "sum"),
            revenue=("revenue", "sum"),
        )
        .reset_index()
    )

    conditions = [
        table["sku_first_month_purchased"] >= (current_month - 1),

        table["sku_last_month_purchased"] <= (current_month - 6),

        table["sku_last_month_purchased"] <= (current_month - 3),

        (
            table["sku_last_month_purchased"] >= (current_month - 2)
        )
        & (
            table["sku_second_to_last_month_purchased"]
            <= (current_month - 6)
        ),

        table["sku_last_month_purchased"] >= (current_month - 2),
    ]

    choices = [
        "New",
        "Inactive",
        "Struggling",
        "Revived",
        "Healthy",
    ]

    table["sku_status"] = np.select(
        conditions,
        choices,
        default="-",
    )

    return table[
        [
            "pod_helper",
            "coded_customer",
            "sku",
            "sku_first_month_purchased",
            "sku_second_to_last_month_purchased",
            "sku_last_month_purchased",
            "sku_status",
            "units",
            "revenue",
        ]
    ]


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

    # SKU-LEVEL STATUS

    df["sku_first_month_purchased"] = (
        df.groupby("pod_helper")["month_year"].transform("min")
    )

    df["sku_last_month_purchased"] = (
        df.groupby("pod_helper")["month_year"].transform("max")
    )

    df["sku_second_to_last_month_purchased"] = (
        df.groupby("pod_helper")["month_year"]
        .transform(
            lambda x: (
                x.drop_duplicates().nlargest(2).iloc[-1]
                if len(x.drop_duplicates()) > 1
                else pd.Period("NaT", freq="M")
            )
        )
    )

    df["sku_second_to_last_month_purchased"] = df["sku_second_to_last_month_purchased"].astype("period[M]")


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
    sku_status_table = calculate_store_sku_status_monthly(df)

    df = df.merge(
        status_table[["coded_customer", "status"]].drop_duplicates(),
        on="coded_customer",
        how="left")
    
    df = df.merge(
        sku_status_table[
            ["pod_helper", "sku_status"]
        ].drop_duplicates(),
        on="pod_helper",
        how="left",
    )
        

    # ADD THIS TEST BACK IN

    #validate_first_pod_flag(df)

    return df

import pandas as pd
import numpy as np

def pct_change(current, prior):
    return np.where(
        prior > 0,
        current / prior - 1,
        np.nan
    )

def monthly_summary(df, df_clone):
    monthly = (
        df.groupby("month_year").agg(
            units = ("units", "sum"),
            revenue = ("revenue", "sum"),
            store_count = ("coded_customer", "nunique"),
            pod_purchases = ("pod_helper", "nunique") # THIS ISNT QUITE RIGHT BC IT SHLD BE ROLLING?
        )
        .reset_index()
        .sort_values("month_year")
    )
    
    # The comparison table is identical to the base table, except it doesn't respond to time filters!

    monthly_clone = (
        df_clone.groupby("month_year").agg(
            units = ("units", "sum"),
            revenue = ("revenue", "sum"),
            pod_purchases = ("pod_helper", "nunique")

        )
        .reset_index()
        .sort_values("month_year")
    )

    monthly_clone["units_l1m"] = monthly_clone["units"].shift(1)
    monthly_clone["revenue_l1m"] = monthly_clone["revenue"].shift(1)

    monthly_clone["units_3m"] = monthly_clone["units"].rolling(3).sum()
    monthly_clone["revenue_3m"] = monthly_clone["revenue"].rolling(3).sum()

    monthly_clone["units_l3m"] = monthly_clone["units"].shift(3).rolling(3).sum()
    monthly_clone["revenue_l3m"] = monthly_clone["revenue"].shift(3).rolling(3).sum()

    monthly_clone["units_py"] = monthly_clone["units"].shift(12)
    monthly_clone["revenue_py"] = monthly_clone["revenue"].shift(12)

    monthly = monthly.merge(
        monthly_clone[["month_year", 
            "units_l1m",
            "revenue_l1m",
            "units_3m",
            "revenue_3m",
            "units_l3m",
            "revenue_l3m",
            "units_py",
            "revenue_py"]],
        on = "month_year",
        how = "left"
    )

    monthly["units_l1m_pct"] = pct_change(monthly["units"],monthly["units_l1m"])
    monthly["revenue_l1m_pct"] = pct_change(monthly["revenue"],monthly["revenue_l1m"])

    monthly["units_l3m_pct"] = pct_change(monthly["units_3m"],monthly["units_l3m"])
    monthly["revenue_l3m_pct"] = pct_change(monthly["revenue_3m"],monthly["revenue_l3m"])

    monthly["units_py_pct"] = pct_change(monthly["units"],monthly["units_py"])
    monthly["revenue_py_pct"] = pct_change(monthly["revenue"],monthly["revenue_py"])

    # selecting and ordering columns

    monthly = monthly[
        [
            "units",
            "revenue",
            "store_count",
            "units_l1m",
            "units_l1m_pct",
            "revenue_l1m",
            "revenue_l1m_pct",
            "units_3m",
            "units_l3m",
            "units_l3m_pct",
            "revenue_3m",
            "revenue_l3m",
            "revenue_l3m_pct",
            "units_py_pct",
            "revenue_py_pct",
        ]
    ]

    return monthly


# ADD LOGIC FOR COMPARISON TABLE FOR ROLLING POD


# distinct count month
# skus selling
# l1m growth
# l3m growth
# growth vs py
# share of brand
# buying stores (distinct count)
# count (POD count)
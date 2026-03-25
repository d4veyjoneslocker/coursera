import pandas as pd
import numpy as np
from filters.filters import monthly_filter

monthly_clone_filter =  [x for x in monthly_filter if x not in ("month", "year")]

def pct_change(current, prior):
    return np.where(
        prior > 0,
        current / prior - 1,
        np.nan
    )

def get_chain_month(chain_table_monthly, month):
    return chain_table_monthly[
        chain_table_monthly["month_year"] == month
    ]

def monthly_summary(df, df_clone):
    monthly = (
        df.groupby(["month_year"] + monthly_filter).agg(
            units = ("units", "sum"),
            revenue = ("revenue", "sum"),
            buying_stores = ("coded_customer", "nunique"),
            skus_selling = ("sku", "nunique"),
            pod_purchases = ("pod_helper", "nunique") # THIS ISNT QUITE RIGHT BC IT SHLD BE ROLLING?
        )
        .reset_index()
        .sort_values(["month_year"] + monthly_filter)
    )
    
    # The comparison table is identical to the base table, except it doesn't respond to time filters!

    monthly_clone = (
        df_clone.groupby(["month_year"] + monthly_filter).agg(
            units = ("units", "sum"),
            revenue = ("revenue", "sum"),
            pod_purchases = ("pod_helper", "nunique"),
            new_buyers = ("first_store_flag", "sum"),
            new_pods = ("first_pod_flag", "sum")
        )
        .reset_index()
        .sort_values(["month_year"] + monthly_filter)
    )

    monthly_clone["units_l1m"] = monthly_clone["units"].shift(1)
    monthly_clone["revenue_l1m"] = monthly_clone["revenue"].shift(1)

    monthly_clone["units_3m"] = monthly_clone["units"].rolling(3, min_periods=3).sum()
    monthly_clone["revenue_3m"] = monthly_clone["revenue"].rolling(3, min_periods=3).sum()

    monthly_clone["units_l3m"] = monthly_clone["units"].shift(3).rolling(3, min_periods=3).sum()
    monthly_clone["revenue_l3m"] = monthly_clone["revenue"].shift(3).rolling(3, min_periods=3).sum()

    monthly_clone["units_py"] = monthly_clone["units"].shift(12)
    monthly_clone["revenue_py"] = monthly_clone["revenue"].shift(12)

    monthly_clone["active_pods"] = monthly_clone["new_pods"].cumsum()

    # Merge clone table with base table

    monthly = monthly.merge(
        monthly_clone[["month_year", 
            "units_l1m",
            "revenue_l1m",
            "units_3m",
            "revenue_3m",
            "units_l3m",
            "revenue_l3m",
            "units_py",
            "revenue_py",
            "active_pods"] + monthly_filter],
        on = ["month_year"] + monthly_filter,
        how = "left"
    )

    monthly["units_l1m_pct"] = pct_change(monthly["units"],monthly["units_l1m"])
    monthly["revenue_l1m_pct"] = pct_change(monthly["revenue"],monthly["revenue_l1m"])

    monthly["units_l3m_pct"] = pct_change(monthly["units_3m"],monthly["units_l3m"])
    monthly["revenue_l3m_pct"] = pct_change(monthly["revenue_3m"],monthly["revenue_l3m"])

    monthly["units_py_pct"] = pct_change(monthly["units"],monthly["units_py"])
    monthly["revenue_py_pct"] = pct_change(monthly["revenue"],monthly["revenue_py"])

    monthly["vpo"] = monthly["units"] / monthly["active_pods"] / 4


    # selecting and ordering columns

    monthly = monthly[
        [
            "month_year",
            "units",
            "revenue",
            "buying_stores",
            "active_pods",]
            +
            monthly_filter
            +
        [
            "vpo",
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

def sku_mix(df):
    df = (
        df.groupby("sku").agg(
            units = ("units", "sum"),
            revenue = ("revenue", "sum"),
            buying_stores = ("coded_customer", "nunique"),
    )
    .reset_index()
    )

    df["total"] = df["units"].sum()

    df["share"] = df["units"]/df["total"].astype(float)

    df = df[
        [
            "sku",
            "units",
            "revenue",
            "buying_stores",
            "share",
        ]
    ]

    return df

def chain_table(df, df_clone):
    chain_table = (
        df.groupby("chain").agg(
            units = ("units", "sum"),
            revenue = ("revenue", "sum"),
            buying_stores = ("coded_customer", "nunique")
        )
        .reset_index()
    )

    chain_table_monthly = (
        df_clone.groupby(["chain","month_year"]).agg(
            units = ("units", "sum"),
            revenue = ("revenue", "sum"),
            buying_stores = ("coded_customer", "nunique"),
            new_pods = ("first_pod_flag", "sum")
        )
        .reset_index()
        .set_index("month_year")
        .asfreq("M")
        .reset_index()
    )
    
    chain_table_monthly = chain_table_monthly.sort_values(["chain", "month_year"])

    # Adding absolute values for L1M, 3M, L3M, and active PODs

    chain_table_monthly["units_l1m"] = chain_table_monthly.groupby("chain")["units"].shift(1)
    chain_table_monthly["revenue_l1m"] = chain_table_monthly.groupby("chain")["revenue"].shift(1)

    chain_table_monthly["units_3m"] = (
        chain_table_monthly.groupby("chain")["units"]
        .transform(lambda x: x.rolling(3, min_periods=3).sum())
    )

    chain_table_monthly["revenue_3m"] = (
        chain_table_monthly.groupby("chain")["revenue"]
        .transform(lambda x: x.rolling(3, min_periods=3).sum())
    )

    chain_table_monthly["units_l3m"] = (
        chain_table_monthly.groupby("chain")["units"]
        .transform(lambda x: x.shift(3).rolling(3, min_periods=3).sum())
    )

    chain_table_monthly["revenue_l3m"] = (
        chain_table_monthly.groupby("chain")["revenue"]
        .transform(lambda x: x.shift(3).rolling(3, min_periods=3).sum())
    )

    chain_table_monthly["active_pods"] = chain_table_monthly.groupby("chain")["new_pods"].cumsum()

    # Calculating % changes / vpo

    chain_table_monthly["units_l1m_pct"] = pct_change(chain_table_monthly["units"],chain_table_monthly["units_l1m"])
    chain_table_monthly["revenue_l1m_pct"] = pct_change(chain_table_monthly["revenue"],chain_table_monthly["revenue_l1m"])

    chain_table_monthly["units_l3m_pct"] = pct_change(chain_table_monthly["units_3m"],chain_table_monthly["units_l3m"])
    chain_table_monthly["revenue_l3m_pct"] = pct_change(chain_table_monthly["revenue_3m"],chain_table_monthly["revenue_l3m"])

    chain_table_monthly["vpo"] = chain_table_monthly["units"] / chain_table_monthly["active_pods"] / 4

    chain_table_monthly = chain_table_monthly[
        [
            "chain",
            "month_year",
            "units",
            "revenue",
            "buying_stores",
            "active_pods",
            "vpo",
            "units_l1m",
            "revenue_l1m",
            "units_l3m",
            "revenue_l3m",
            "units_l1m_pct",
            "revenue_l1m_pct",
            "units_l3m_pct",
            "revenue_l3m_pct"
        ]
    ]

    selected_month = pd.Period("2026-02", freq="M")

    chain_table_selected_month = get_chain_month(chain_table_monthly, selected_month)

    chain_table = chain_table.merge(
        chain_table_selected_month[[
            "chain",
            "units_l1m",
            "revenue_l1m",
            "units_l3m",
            "revenue_l3m",
            "units_l1m_pct",
            "revenue_l1m_pct",
            "units_l3m_pct",
            "revenue_l3m_pct",
            "vpo"
            ]],
        on="chain",
        how="left"
    )


    chain_table = chain_table[
        [
            "chain",
            "units",
            "revenue",
            "buying_stores",
            "units_l1m",
            "revenue_l1m",
            "units_l3m",
            "revenue_l3m",
            "units_l1m_pct",
            "revenue_l1m_pct",
            "units_l3m_pct",
            "revenue_l3m_pct",
        ]
    ]



    return chain_table

    









# distinct count month
# skus selling
# l1m growth
# l3m growth
# growth vs py
# share of brand
# buying stores (distinct count)
# count (POD count)
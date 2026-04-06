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
        df.groupby(["month_year"]).agg(
            units = ("units", "sum"),
            revenue = ("revenue", "sum"),
            buying_stores = ("coded_customer", "nunique"),
            skus_selling = ("sku", "nunique"),
            monthly_pods = ("pod_helper", "nunique") # THIS ISNT QUITE RIGHT BC IT SHLD BE ROLLING?
        )
        .reset_index()
        .sort_values(["month_year"])
    )
    
    # The comparison table is identical to the base table, except it doesn't respond to time filters!

    monthly_clone = (
        df_clone.groupby(["month_year"]).agg(
            units = ("units", "sum"),
            revenue = ("revenue", "sum"),
            monthly_pods = ("pod_helper", "nunique"),
            new_buyers = ("first_store_flag", "sum"),
            new_pods = ("first_pod_flag", "sum")
        )
        .reset_index()
        .sort_values(["month_year"])
    )

    months = sorted(df_clone["month_year"].unique())

    monthly_clone["buying_stores_total"] = [
        df.loc[df["month_year"] <= m, "coded_customer"].nunique()
        for m in monthly_clone["month_year"]
    ]

    monthly_clone["buying_stores_3m"] = [
        df_clone.loc[
            df_clone["month_year"].isin(months[max(0, i-3):i]),
            "coded_customer"
        ].nunique()
        for i in range(len(months))
    ]

    monthly_clone["buying_stores_l3m"] = [
        df_clone.loc[
            df_clone["month_year"].isin(months[i-6:i-3]),
            "coded_customer"
        ].nunique() if i >= 6 else None
        for i in range(len(months))
    ]

    monthly_clone["active_pods"] = monthly_clone["new_pods"].cumsum()

    # Merge clone table with base table

    monthly = monthly.merge(
        monthly_clone[["month_year", 
            "active_pods",
            "buying_stores_total",
            "buying_stores_3m",
            "buying_stores_l3m",
            "new_pods"
            ]],
        on = ["month_year"],
        how = "left"
    )

    monthly["vpo"] = monthly["units"] / monthly["active_pods"] / 4


    # selecting and ordering columns

    monthly = monthly[
        [
            "month_year",
            "units",
            "revenue",
            "buying_stores",
            "active_pods",
            "new_pods",
            "vpo",
            "buying_stores_total",
            "buying_stores_3m",
            "buying_stores_l3m",
        ]
    ].sort_values(["month_year"])

    # LOGIC TO REMOVE CURRENT MONTH

    current_month = pd.Timestamp.today().to_period("M")
    monthly = monthly[monthly["month_year"] != current_month].copy()

    monthly["month_year"] = monthly["month_year"].astype(str)

    return monthly

def sku_mix(df):
    df = (
        df.groupby(["sku"] + monthly_filter).agg(
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
        + monthly_filter
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
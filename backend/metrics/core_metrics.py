import pandas as pd
import numpy as np
from filters.filters import monthly_filter
from metrics.growth_metrics import add_time_metrics_chain


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

def calculate_reorder_rate(df):
    denom = df["total_buyers"] - df["new_buyers"]
    
    result = df["repeat_buyers"] / denom
    
    return result.replace([float("inf"), -float("inf")], None)

def monthly_summary(df, df_clone):
    monthly = (
        df.groupby(["month_year"]).agg(
            units = ("units", "sum"),
            revenue = ("revenue", "sum"),
            buying_stores = ("coded_customer", "nunique"),
            skus_selling = ("sku", "nunique"),
            buying_pods = ("pod_helper", "nunique") # THIS ISNT QUITE RIGHT BC IT SHLD BE ROLLING?
        )
        .reset_index()
        .sort_values(["month_year"])
    )
    
    # The comparison table is identical to the base table, except it doesn't respond to time filters!
    # Buying PODs anchors the grains of the two tables

    monthly_clone = (
        df_clone.groupby(["month_year"]).agg(
            units = ("units", "sum"),
            revenue = ("revenue", "sum"),
            buying_pods = ("pod_helper", "nunique"),
            new_buyers = ("first_store_flag", "sum"),
            buying_stores = ("coded_customer", "nunique"),
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
            df_clone["month_year"].isin(months[i-5:i-2]),
            "coded_customer"
        ].nunique() if i >= 5 else None
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
    ]

    return df

def active_store_rate(df):

    store_universe = (
        df.groupby(["month_year", "coded_customer"], as_index=False)
        .agg(
            repeat_buyer=("reorder_flag", "max"),
            new_buyer=("first_store_flag", "max"),
        )
        .sort_values(["coded_customer", "month_year"])
    )

    result = (
        store_universe.groupby("month_year", as_index=False)
        .agg(
            repeat_buyers=("repeat_buyer", "sum"),
            new_buyers=("new_buyer", "sum"),
            buying_stores=("coded_customer", "nunique"),
        )
        .sort_values("month_year")
        .reset_index(drop=True)
    )

    result["total_buyers"] = result["new_buyers"].cumsum()
    result["existing_buyers"] = result["total_buyers"] - result["new_buyers"]

    result["repeat_buyers_3m"] = result["repeat_buyers"].rolling(3, min_periods=3).sum()
    result["existing_buyers_3m"] = result["existing_buyers"].rolling(3, min_periods=3).sum()

    result["repeat_buyers_l1m"] = result["repeat_buyers"].shift(1)
    result["repeat_buyers_l3m"] = result["repeat_buyers_3m"].shift(3)

    result["new_buyers_l1m"] = result["new_buyers"].shift(1)
    result["new_buyers_l3m"] = result["new_buyers"].rolling(3, min_periods=3).sum().shift(3)

    result["total_buyers_l1m"] = result["total_buyers"].shift(1)
    result["total_buyers_l3m"] = result["total_buyers"].shift(3)

    result["existing_buyers_l1m"] = result["existing_buyers"].shift(1)
    result["existing_buyers_l3m"] = result["existing_buyers_3m"].shift(3)

    result["reorder_rate"] = calculate_reorder_rate(result)

    result["repeat_buyers_lifetime"] = result["repeat_buyers"].cumsum()
    result["existing_buyers_lifetime"] = result["existing_buyers"].cumsum()

    result["reorder_rate_lifetime"] = (
        result["repeat_buyers_lifetime"] / result["existing_buyers_lifetime"]
    ).replace([float("inf"), -float("inf")], None)

    result["reorder_rate_3m"] = (
        result["repeat_buyers_3m"] / result["existing_buyers_3m"]
    ).replace([float("inf"), -float("inf")], None)

    result["reorder_rate_l1m"] = result["reorder_rate"].shift(1)
    result["reorder_rate_l3m"] = result["reorder_rate_3m"].shift(3)

    return result





def chain_table(df, df_clone):
    real_current_month = pd.Timestamp.today().to_period("M")
    visible_latest_month = df["month_year"].max() if not df.empty else None

    if visible_latest_month == real_current_month:
        df_full_months = df[df["month_year"] != real_current_month].copy()
        latest_month = df_full_months["month_year"].max() if not df_full_months.empty else None
    else:
        latest_month = visible_latest_month


    chain_table = (
        df.groupby("chain").agg(
            units = ("units", "sum"),
            revenue = ("revenue", "sum"),
            buying_stores = ("coded_customer", "nunique")
        )
        .reset_index()
    )

    print("CHAIN TABLE COLUMNS:", df_clone.columns.tolist())

    chain_table_monthly = (
        df_clone.groupby(["chain","month_year"]).agg(
            units = ("units", "sum"),
            revenue = ("revenue", "sum"),
            buying_stores = ("coded_customer", "nunique"),
            new_pods = ("first_pod_flag", "sum")
        )
        .reset_index()
        .sort_values(["chain", "month_year"])
    )
    

    # Adding absolute values for L1M, 3M, L3M, and active PODs

    chain_table_monthly["active_pods"] = chain_table_monthly.groupby("chain")["new_pods"].cumsum()

    # Calculating % changes / vpo

    chain_table_monthly["vpo"] = chain_table_monthly["units"] / chain_table_monthly["active_pods"] / 4

    chain_table_monthly = add_time_metrics_chain(chain_table_monthly, "chain", ["units", "revenue"])

    chain_table_selected_month = get_chain_month(chain_table_monthly, latest_month)

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
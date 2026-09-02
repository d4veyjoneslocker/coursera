import pandas as pd
from backend.metrics.metric_helpers import total, peak, average, latest_month, safe_float, safe_int
from backend.metrics.metric_calculators import calculate_units, calculate_buying_stores, calculate_active_pods, calculate_vpo, calculate_average_skus_per_store

# Pie Chart KPIS



def avg_skus_per_store(df):
    avg_skus_per_store = calculate_average_skus_per_store(df)

    return {"skus_per_store":{
                "key": "skus_per_store",
                "title": "Avg. SKUs per Store",
                "value": avg_skus_per_store}}

def count_channels(df):
    return {"channel_count":
                {"key": "channel_count",
                "title": "Channel Count",
                "value": df["channel"].nunique()}}

# Bar Chart cards KPIs

def unit_kpis(df):

    total_units = calculate_units(df, group_cols=[])
    current_month = pd.Timestamp.today().to_period("M")

    df = df[df["month_year"] != current_month].copy()


    return [
        {
        "key": "total_units",
        "title": "Total Units",
        "value": safe_int(total_units),
        },
        {
        "key": "l1m_units",
        "title": "L1M Units",
        "value": safe_int(latest_month(df["units"])),
        "sideValue": safe_float(latest_month(df["units_l1m_pct"])),
        "sideLabel": "vs LM",
        "sideType": "percent"
        },
        {
        "key": "l3m_units",
        "title": "L3M Units",
        "value": safe_int(latest_month(df["units_3m"])),
        "sideValue": safe_float(latest_month(df["units_l3m_pct"])),
        "sideLabel": "vs L3M",
        "sideType": "percent"
        },
    ]

def buying_kpis(df, df_store_level):
    current_month = pd.Timestamp.today().to_period("M")
    total_buyers = calculate_buying_stores(df_store_level, group_cols=[])

    df = df[df["month_year"] != current_month].copy()
    
    return [
        {
        "key": "total_buyers",
        "title": "Total buyers",
        "value": safe_int(total_buyers),
        },
        {
        "key": "l1m_buyers",
        "title": "L1M buyers",
        "value": safe_int(latest_month(df["buying_stores"])),
        "sideValue": safe_float(latest_month(df["buying_stores_l1m_pct"])),
        "sideLabel": "vs L1M",
        "sideType": "percent"
        },
        {
        "key": "l3m_buyers",
        "title": "L3M buyers",
        "value": safe_int(latest_month(df["buying_stores_3m"])),
        "sideValue": safe_float(latest_month(df["buying_stores_l3m_pct"])),
        "sideLabel": "vs L3M",
        "sideType": "percent"
        },
    ]

def pod_kpis(df, df_full):
    current_month = pd.Timestamp.today().to_period("M")
    total_pods = calculate_active_pods(df, df_full, group_cols=[])

    df = df[df["month_year"] != current_month].copy()

    return [
        {
        "key": "total_pods",
        "title": "Total PODs",
        "value": safe_int(total_pods),
        },
        {
        "key": "l1m_new_pods",
        "title": "L1M New PODs",
        "value": safe_int(latest_month(df["new_pods"])),
        "sideValue": safe_float(latest_month(df["new_pods_l1m_pct"])),
        "sideLabel": "vs L1M",
        "sideType": "percent"
        },
        {
        "key": "l3m_new_pods",
        "title": "L3M New PODs",
        "value": safe_int(latest_month(df["new_pods_3m"])),
        "sideValue": safe_float(latest_month(df["new_pods_l3m_pct"])),
        "sideLabel": "vs L3M",
        "sideType": "percent"
        },
    ]

def vpo_kpis(df, df_full):
    current_month = pd.Timestamp.today().to_period("M")
    total_vpo = calculate_vpo(df, df_full, group_cols=[])

    df = df[df["month_year"] != current_month].copy()
 
    return [
        {
        "key": "total_velocity",
        "title": "Total velocity",
        "value": safe_float(total_vpo),
        },
        {
        "key": "l1m_velocity",
        "title": "L1M velocity",
        "value": safe_float(latest_month(df["vpo"])),
        "sideValue": safe_float(latest_month(df["vpo_l1m_pct"])),
        "sideLabel": "vs L1M",
        "sideType": "percent"
        },
        {
        "key": "l3m_velocity",
        "title": "L3M velocity",
        "value": safe_float(latest_month(df["vpo_3m"])),
        "sideValue": safe_float(latest_month(df["vpo_l3m_pct"])),
        "sideLabel": "vs L3M",
        "sideType": "percent"
        },
    ]
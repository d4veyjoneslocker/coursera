import pandas as pd
import numpy as np
from filters.filters import monthly_filter
from metrics.core_metrics import monthly_summary

def total(series):
    return series.sum() if len(series) else None

def peak(series):
    return series.max() if len(series) else None

def average(series):
    return series.mean()

def latest_month(series):
    if len(series) == 0:
        return None
    value = series.iloc[-1]
    return None if pd.isna(value) else value

def l3m(series):
    return series.tail(3).sum() if len(series) else None

def safe_float(val):
    return float(val) if pd.notna(val) else None

def safe_int(val):
    return int(val) if pd.notna(val) else None

def calculate_avg_skus_per_store(df):
    skus_per_store = df.groupby("coded_customer")["sku"].nunique()
    avg_skus_per_store = skus_per_store.mean()

    return {"skus_per_store":{
                "key": "skus_per_store",
                "title": "Avg. SKUs per Store",
                "value": avg_skus_per_store}}

def count_channels(df):
    return {"channel_count":
                {"key": "channel_count",
                "title": "Channel Count",
                "value": df["channel"].nunique()}}

def kpi_data(df, df_full_months):


    current_month = pd.Timestamp.today().to_period("M")
    full_df = df.copy()
    df = df[df["month_year"] != current_month].copy()
    total_units = max(df_full_months["units"])
    total_buyers = max(df_full_months["buying_stores_total"])

    #UNITS

    #total units

    unit_kpis = [
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

    buyers_kpis = [
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

    pod_kpis = [
        {
        "key": "total_pods",
        "title": "Total PODs",
        "value": safe_int(peak(df["active_pods"])),
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

    velocity_kpis = [
        {
        "key": "total_velocity",
        "title": "Total velocity",
        "value": safe_float(latest_month(df["vpo_lifetime_average"])),
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


    return {
        "units_kpis": unit_kpis,
        "buyers_kpis": buyers_kpis,
        "pod_kpis": pod_kpis,
        "velocity_kpis": velocity_kpis,
    }

def store_health_kpis(df):
    current_month = pd.Timestamp.today().to_period("M")
    df = df[df["month_year"] != current_month].copy()

    reorder_kpis = [
        {
        "key": "total_reorder_rate",
        "title": "Ttl reorder rate",
        "value": safe_float(latest_month(df["reorder_rate_lifetime"])),
        },
        {
        "key": "l1m_reorder_rate",
        "title": "L1M reorder rate",
        "value": safe_float(latest_month(df["reorder_rate"])),
        "sideValue": safe_float(latest_month(df["reorder_rate_l1m_abs"])),
        "sideLabel": "vs L1M",
        "sideType": "absolute"
        },
        {
        "key": "l3m_reorder_rate",
        "title": "L3M reorder rate",
        "value": safe_float(latest_month(df["reorder_rate_3m"])),
        "sideValue": safe_float(latest_month(df["reorder_rate_l3m_abs"])),
        "sideLabel": "vs L3M",
        "sideType": "absolute"
        },
    ]

    return {
        "reorder_kpis": reorder_kpis
    }



def buying_kpis(df):
    current_month = pd.Timestamp.today().to_period("M")
    df = df[df["month_year"] != current_month].copy()

    buyers_kpis = [
        {
        "key": "total_buyers",
        "title": "Total buyers",
        "value": safe_int(latest_month(df["buying_stores_total"])),
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

    return {
        "buyers_kpis": buyers_kpis,
    }

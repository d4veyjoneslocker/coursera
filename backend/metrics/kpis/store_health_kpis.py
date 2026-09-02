
import pandas as pd
from backend.metrics.metric_helpers import total, peak, average, latest_month, safe_float, safe_int
from backend.metrics.metric_calculators import calculate_buying_stores, calculate_reorder_rate

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

def reorder_kpis(df, df_all_time, df_store_level):

    current_month = pd.Timestamp.today().to_period("M")

    total_reorder_rate = calculate_reorder_rate(df_store_level, df_all_time)

    df = df[df["month_year"] != current_month].copy()

    return [
        {
        "key": "total_reorder_rate",
        "title": "Ttl reorder rate",
        "value": safe_float(total_reorder_rate),
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

def count_channels(df):
    return {"channel_count":
                {"key": "channel_count",
                "title": "Channel Count",
                "value": df["channel"].nunique()}}


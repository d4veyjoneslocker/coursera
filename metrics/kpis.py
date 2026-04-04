import pandas as pd
import numpy as np
from filters.filters import monthly_filter

def total(series):
    return series.sum()

def peak(series):
    return series.max() if len(series) else None

def average(series):
    return series.mean()

def latest_month(series):
    if len(series) == 0:
        return None
    value = series.iloc[-2]
    return None if pd.isna(value) else value
    

def l3m(series):
    return series.tail(3).sum() if len(series) else None

def kpi_data(df):
    #UNITS

    #total units

    unit_kpis = [
        {
        "key": "total_units",
        "title": "Total Units",
        "value": int(total(df["units"])),
        },
        {
        "key": "l1m_units",
        "title": "L1M Units",
        "value": int(latest_month(df["units"])),
        "sideValue": float(latest_month(df["units_l1m_pct"])),
        "sideLabel": "vs LM"
        },
        {
        "key": "l3m_units",
        "title": "L3M Units",
        "value": int(latest_month(df["units_3m"])),
        "sideValue": float(latest_month(df["units_l3m_pct"])),
        "sideLabel": "vs L3M"
        },
    ]

    return unit_kpis
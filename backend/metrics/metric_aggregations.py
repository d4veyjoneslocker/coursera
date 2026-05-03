import pandas as pd

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
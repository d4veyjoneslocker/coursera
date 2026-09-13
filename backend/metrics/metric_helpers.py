import pandas as pd
import numpy as np

# AGGREGATIONS

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

def pct_change(current, prior):
    current = pd.to_numeric(current, errors="coerce")
    prior = pd.to_numeric(prior, errors="coerce")

    return np.where(
        (prior.isna()) | (prior == 0),
        np.nan,
        current / prior - 1
    )

def abs_change(current, prior):
    return np.where(
        pd.notna(prior),
        current - prior,
        np.nan
    )


# HELPER FUNCTIONS

def grouped_cumsum(df, metric, group_cols):
    non_time_cols = [c for c in group_cols if c != "month_year"]

    if non_time_cols:
        return df.groupby(non_time_cols)[metric].cumsum()

    return df[metric].cumsum()


def clean_group_cols(group_cols):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    group_cols = group_cols or []

    if "month_year" in group_cols:
        group_cols = [c for c in group_cols if c != "month_year"] + ["month_year"]
    else:
        group_cols = group_cols + ["month_year"]

    return group_cols


def get_current_period(include_current_month=False):
    today = pd.Timestamp.today()
    current_period = pd.Period(today, freq="M")

    if not include_current_month:
        current_period -= 1

    return current_period

def calculate_avg_skus_per_store(df, grain):
    result = (
        df.groupby([grain, "coded_customer"])["sku"]
        .nunique()
        .reset_index(name="sku_count")
    )

    result = (
        result.groupby(grain, as_index=False)["sku_count"]
        .mean()
        .rename(columns={"sku_count": "avg_skus_per_store"})
    )

    return result


def resolve_period(period, year):
    period = period.upper()

    period_map = {
        "Q1": (1, 3),
        "Q2": (4, 6),
        "Q3": (7, 9),
        "Q4": (10, 12),
        "H1": (1, 6),
        "H2": (7, 12),
        "FY": (1, 12),
    }

    if period not in period_map:
        raise ValueError(f"Unsupported period: {period}")

    start_month, end_month = period_map[period]

    return {
        "label": f"{period} {year}",
        "start": pd.Period(f"{year}-{start_month:02d}", freq="M"),
        "end": pd.Period(f"{year}-{end_month:02d}", freq="M"),
    }


def resolve_period_comparison(period, year, comparison):
    current = resolve_period(period, year)
    comparison = comparison.upper()

    if comparison == "PY":
        prior = resolve_period(period, year - 1)

    elif comparison == "PP":
        months = len(
            pd.period_range(
                start=current["start"],
                end=current["end"],
                freq="M",
            )
        )

        prior_end = current["start"] - 1
        prior_start = prior_end - (months - 1)

        prior = {
            "label": label_period(prior_start, prior_end),
            "start": prior_start,
            "end": prior_end,
        }

    else:
        raise ValueError(f"Unsupported comparison: {comparison}")

    return current, prior

def get_period_months(start, end):
    start = pd.Period(start, freq="M")
    end = pd.Period(end, freq="M")

    if end < start:
        raise ValueError("end must be on or after start")

    return list(pd.period_range(start=start, end=end, freq="M"))


def filter_to_period(df, start, end, date_col="month_year"):
    start = pd.Period(start, freq="M")
    end = pd.Period(end, freq="M")

    return df[
        (df[date_col] >= start) &
        (df[date_col] <= end)
    ].copy()

def label_period(start, end):
    start = pd.Period(start, freq="M")
    end = pd.Period(end, freq="M")

    months = len(
        pd.period_range(
            start=start,
            end=end,
            freq="M",
        )
    )

    if months == 3:
        quarter = ((start.month - 1) // 3) + 1
        if start.month in (1, 4, 7, 10):
            return f"Q{quarter} {start.year}"

    if months == 6:
        if start.month == 1:
            return f"H1 {start.year}"
        if start.month == 7:
            return f"H2 {start.year}"

    if months == 12 and start.month == 1:
        return f"FY {start.year}"

    return f"{start.strftime('%b %Y')}–{end.strftime('%b %Y')}"
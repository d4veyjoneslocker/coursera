import pandas as pd

from backend.metrics.metric_calculators import (
    calculate_units,
    calculate_buying_stores,
    calculate_vpo,
)
from backend.metrics.metric_aggregations import safe_float


def get_current_and_prior_ytd(df: pd.DataFrame, today=None):
    today = pd.Timestamp.today() if today is None else pd.Timestamp(today)
    last_full_month = pd.Period(today, freq="M") - 1

    current_year = last_full_month.year
    prior_year = current_year - 1
    month_cutoff = last_full_month.month

    out = df.copy()
    out["month_year"] = pd.PeriodIndex(out["month_year"], freq="M")

    current_ytd = out[
        (out["month_year"].dt.year == current_year)
        & (out["month_year"].dt.month <= month_cutoff)
    ].copy()

    prior_ytd = out[
        (out["month_year"].dt.year == prior_year)
        & (out["month_year"].dt.month <= month_cutoff)
    ].copy()

    return current_ytd, prior_ytd, last_full_month


def build_deep_dive_kpis(df: pd.DataFrame, today=None):
    current_ytd, prior_ytd, last_full_month = get_current_and_prior_ytd(
        df,
        today=today,
    )

    units_current = calculate_units(current_ytd)
    units_prior = calculate_units(prior_ytd)

    buying_stores_current = calculate_buying_stores(current_ytd)
    buying_stores_prior = calculate_buying_stores(prior_ytd)

    vpo_current = calculate_vpo(current_ytd, df)
    vpo_prior = calculate_vpo(prior_ytd, df)

    sales_growth = pct_change(units_current, units_prior)
    distribution_growth = pct_change(buying_stores_current, buying_stores_prior)
    velocity_growth = pct_change(vpo_current, vpo_prior)

    return {
        "last_full_month": str(last_full_month),
        "cards": [
            {
                "key": "sales",
                "label": "Unit Sales",
                "value": format_compact(units_current),
                "unit": "units sold",
                "trendValue": format_growth(sales_growth),
                "trendLabel": f"vs YTD {prior_year_label(last_full_month)}",
                "trendDirection": get_trend_direction(sales_growth),
                "interpretation": (
                    "Sales growth is being driven by a wider retail footprint "
                    "and stronger productivity in key accounts."
                ),
                "expandedPoints": [
                    "Whole Foods contributed 42% of incremental YTD units.",
                    "SKU D added 31 new active stores versus the prior-year period.",
                    "Natural channel velocity improved 18%, while active stores also expanded.",
                ],
            },
            {
                "key": "distribution",
                "label": "Distribution",
                "value": format_compact(buying_stores_current),
                "unit": "active stores",
                "trendValue": format_growth(distribution_growth),
                "trendLabel": f"vs YTD {prior_year_label(last_full_month)}",
                "trendDirection": get_trend_direction(distribution_growth),
                "interpretation": (
                    "The brand is reaching more buying doors, with expansion "
                    "coming from both new accounts and deeper SKU placement."
                ),
                "expandedPoints": [
                    "Active stores increased from 90 to 1.2K versus the same YTD period last year.",
                    "60% of new placements came from existing retail accounts adding more SKUs.",
                    "SKU E entered 3 new states and added 170 active stores.",
                ],
            },
            {
                "key": "velocity",
                "label": "Velocity",
                "value": format_compact(vpo_current),
                "unit": "VPO",
                "trendValue": format_growth(velocity_growth),
                "trendLabel": f"vs YTD {prior_year_label(last_full_month)}",
                "trendDirection": get_trend_direction(velocity_growth),
                "interpretation": (
                    "Store-level productivity improved, suggesting the newer "
                    "distribution is not just broader, but also working harder."
                ),
                "expandedPoints": [
                    "VPO increased from 0.3 to 2.3 versus the same YTD period last year.",
                    "SKU E is averaging 16.5 VPO, the highest among active SKUs.",
                    "Specialty is producing 1.5x its expected unit share based on store footprint.",
                ],
            },
        ],
    }


def pct_change(current, prior):
    if prior is None or pd.isna(prior) or prior == 0:
        return None

    return safe_float((current - prior) / prior)


def format_compact(value):
    if value is None or pd.isna(value):
        return "—"

    value = float(value)

    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"

    if value >= 1_000:
        return f"{value / 1_000:.1f}K"

    if value >= 100:
        return f"{value:.0f}"

    return f"{value:.1f}"


def format_growth(value):
    if value is None or pd.isna(value):
        return None

    sign = "+" if value > 0 else ""
    return f"{sign}{round(value * 100)}%"


def get_trend_direction(value):
    if value is None or pd.isna(value) or value == 0:
        return "flat"

    return "up" if value > 0 else "down"


def prior_year_label(last_full_month):
    return f"{last_full_month.month:02d}/{last_full_month.year - 1}"
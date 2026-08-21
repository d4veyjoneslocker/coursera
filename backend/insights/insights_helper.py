import pandas as pd
from backend.metrics.metric_helpers import get_current_period
from backend.metrics.monthly_metric_calculators import (
    calculate_monthly_revenue,
    calculate_monthly_units,
)
from backend.metrics.metric_growth_rates import (
    add_additive_metric_3m,
    calculate_buying_stores_3m,
    calculate_vpo_3m,
    add_prior_month_columns,
    add_pct_change_columns,
)

def format_filter_values(values, max_items=3):
    if not values:
        return None

    if not isinstance(values, list):
        values = [values]

    values = [v for v in values if v]

    if len(values) == 1:
        return values[0]

    if len(values) == 2:
        return f"{values[0]} and {values[1]}"

    shown = values[:max_items]
    extra_count = len(values) - max_items

    text = f"{', '.join(shown[:-1])}, and {shown[-1]}"

    if extra_count > 0:
        text += f" + {extra_count} more"

    return text


def build_filter_context(filters, exclude_keys=None):
    if not filters:
        return "", []

    exclude_keys = exclude_keys or set()

    filter_labels = {
        "sku": "for",
        "channel": "in",
        "distributor": "in stores serviced by",
        "dc": "from DC",
        "state": "in",
        "chain": "in",
    }

    context_parts = []
    part_objects = []

    for key, prefix in filter_labels.items():
        if key in exclude_keys:
            continue

        value_text = format_filter_values(filters.get(key))
        if not value_text:
            continue

        context_parts.append(f"{prefix} {value_text}")
        part_objects.extend([
            {"type": "text", "value": f" {prefix} "},
            {"type": "chip", "value": value_text, "tone": "neutral"},
        ])

    context_str = " " + " ".join(context_parts) if context_parts else ""

    return context_str, part_objects

def format_pct(
    value,
    decimals=0,
    signed=False,
    null_value="-",
):
    try:
        if value is None or pd.isna(value):
            return null_value

        value = float(value)

        if not pd.notna(value) or value in [float("inf"), float("-inf")]:
            return null_value

        sign = "+" if signed and value > 0 else ""

        return f"{sign}{value:.{decimals}%}"

    except (TypeError, ValueError):
        return null_value


def format_float(
    value,
    decimals=1,
    null_value="-",
):
    try:
        if value is None or pd.isna(value):
            return null_value

        value = float(value)

        if not pd.notna(value) or value in [float("inf"), float("-inf")]:
            return null_value

        return f"{value:,.{decimals}f}"

    except (TypeError, ValueError):
        return null_value


def format_number(
    value,
    null_value="-",
):
    try:
        if value is None or pd.isna(value):
            return null_value

        value = float(value)

        if not pd.notna(value) or value in [float("inf"), float("-inf")]:
            return null_value

        return f"{int(round(value)):,}"

    except (TypeError, ValueError):
        return null_value
    
def get_last_full_month(today=None) -> pd.Period:
    if today is None:
        today = pd.Timestamp.today()

    current_month = pd.Period(today, freq="M")

    return current_month - 1

def safe_float(val):
    return float(val) if pd.notna(val) else None

def _build_3m_metrics(
    df_filtered: pd.DataFrame,
    df_full: pd.DataFrame,
    grain: list[str],
) -> pd.DataFrame:
    """
    Uses SKUba's existing metric functions to build
    L3M performance and growth at any requested grain.
    """

    if df_filtered is None or df_filtered.empty:
        return pd.DataFrame()

    result = calculate_monthly_revenue(
        df_filtered,
        grain,
    )

    result = result.merge(
        calculate_monthly_units(
            df_filtered,
            grain,
        ),
        on=grain + ["month_year"],
        how="left",
    )

    result = add_additive_metric_3m(
        result,
        grain,
        "revenue",
    )

    result = add_additive_metric_3m(
        result,
        grain,
        "units",
    )

    result = result.merge(
        calculate_buying_stores_3m(
            df_filtered,
            grain,
        ),
        on=grain + ["month_year"],
        how="left",
    )

    result = result.merge(
        calculate_vpo_3m(
            df_filtered,
            df_full,
            grain,
        ),
        on=grain + ["month_year"],
        how="left",
    )

    result = add_prior_month_columns(
        result,
        grain,
        "revenue",
        l3m=True,
    )

    result = add_prior_month_columns(
        result,
        grain,
        "units",
        l3m=True,
    )

    result = add_prior_month_columns(
        result,
        grain,
        "buying_stores",
        l3m=True,
    )

    result = add_prior_month_columns(
        result,
        grain,
        "vpo",
        l3m=True,
    )

    result = add_pct_change_columns(
        result,
        "revenue",
        l3m=True,
    )

    result = add_pct_change_columns(
        result,
        "units",
        l3m=True,
    )

    result = add_pct_change_columns(
        result,
        "buying_stores",
        l3m=True,
    )

    result = add_pct_change_columns(
        result,
        "vpo",
        l3m=True,
    )

    current_month = get_current_period(
        include_current_month=True
    )

    result = result[
        result["month_year"] != current_month
    ].copy()

    if result.empty:
        return result

    latest_month = result["month_year"].max()

    return result[
        result["month_year"] == latest_month
    ].copy()

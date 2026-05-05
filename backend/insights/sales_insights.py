import pandas as pd

def build_top_sales_month_insight(monthly_df):
    """
    Returns an insight if latest full month is top 3 all-time
    for units, buying stores, or velocity. Otherwise returns None.
    """

    metrics = {
        "units": {"col": "units", "label": "sales"},
        "buyers": {"col": "buying_stores", "label": "buying stores"},
        "velocity": {"col": "vpo", "label": "velocity"},
    }

    df = monthly_df.copy()

    if df.empty or "month_year" not in df.columns:
        return None

    if not isinstance(df["month_year"].dtype, pd.PeriodDtype):
        df["month_year"] = pd.PeriodIndex(df["month_year"].astype(str), freq="M")

    df = df.sort_values("month_year")

    current_month = pd.Timestamp.today().to_period("M")
    last_full_month = current_month - 1

    df = df[df["month_year"] <= last_full_month]

    if df.empty:
        return None

    latest_month = df["month_year"].max()
    month_display = latest_month.to_timestamp().strftime("%B %Y")

    candidates = {}

    for key, meta in metrics.items():
        col = meta["col"]

        if col not in df.columns:
            continue

        metric_df = (
            df[["month_year", col]]
            .dropna()
            .sort_values(col, ascending=False)
            .reset_index(drop=True)
        )

        if metric_df.empty:
            continue

        metric_df["rank"] = metric_df.index + 1

        latest_match = metric_df[metric_df["month_year"] == latest_month]

        if latest_match.empty:
            continue

        rank = int(latest_match.iloc[0]["rank"])

        if rank > 3:
            continue

        latest_value = latest_match.iloc[0][col]
        below_row = metric_df[metric_df["rank"] == rank + 1]

        pct_vs_below = None

        if not below_row.empty:
            below_value = below_row.iloc[0][col]

            if pd.notna(below_value) and below_value != 0:
                pct = (latest_value - below_value) / below_value

                if pct >= 0.02:
                    pct_vs_below = pct

        candidates[key] = {
            "metric": key,
            "rank": rank,
            "value": latest_value,
            "pct_vs_below": pct_vs_below,
            **meta,
        }

    if not candidates:
        return None

    units_top3 = "units" in candidates
    velocity_top3 = "velocity" in candidates

    if units_top3 and velocity_top3:
        selected = [candidates["units"], candidates["velocity"]]

    elif "buyers" in candidates:
        buyer_rank = candidates["buyers"]["rank"]
        units_rank = candidates.get("units", {}).get("rank", 999)
        velocity_rank = candidates.get("velocity", {}).get("rank", 999)

        if buyer_rank < units_rank and buyer_rank < velocity_rank:
            selected = [candidates["buyers"]]
        else:
            selected = [min(candidates.values(), key=lambda x: x["rank"])]

    else:
        selected = [min(candidates.values(), key=lambda x: x["rank"])]

    if len(selected) == 2:
        metric_parts = []

        for i, m in enumerate(selected):
            if i > 0:
                metric_parts.append({"type": "text", "value": " and "})

            metric_parts.extend([
                {
                    "type": "chip",
                    "value": f"#{m['rank']} all-time",
                    "tone": "positive",
                },
                {
                    "type": "text",
                    "value": f" for {m['label']}",
                },
            ])

        summary = (
            f"{month_display} was "
            + " and ".join(
                f"#{m['rank']} all-time for {m['label']}" for m in selected
            )
            + "."
        )

        return {
            "type": "top_sales_month",
            "summary": summary,
            "parts": [
                {"type": "chip", "value": month_display, "tone": "neutral"},
                {"type": "text", "value": " was "},
                *metric_parts,
                {"type": "text", "value": "."},
            ],
            "metrics": selected,
        }

    m = selected[0]

    value_label = f"{int(m['value']):,} units"

    summary = f"{month_display} was your #{m['rank']} all-time month for {m['label']}"

    parts = [
        {"type": "chip", "value": month_display, "tone": "neutral"},
        {"type": "text", "value": " was your "},
        {
            "type": "chip",
            "value": f"#{m['rank']} all-time",
            "tone": "positive",
        },
        {"type": "text", "value": f" month for {m['label']}"},
    ]

    if m["pct_vs_below"] is not None:
        pct = round(m["pct_vs_below"] * 100)

        summary += f", coming in {pct}% above the next-best month"

        parts[-1]["value"] += f", coming in {pct}% above the next-best month"

    summary += "."
    parts.append({"type": "text", "value": "."})

    parts.append({
        "type": "chip",
        "value": value_label,
        "tone": "positive",
    })

    return {
        "type": "top_sales_month",
        "summary": summary,
        "parts": parts,
        "metrics": selected,
    }

def build_top_reorder_rate_month_insight(monthly_df):
    """
    Returns an insight if latest full month is top 3 all-time
    for reorder rate. Otherwise returns None.
    """

    df = monthly_df.copy()

    if df.empty or "month_year" not in df.columns or "reorder_rate" not in df.columns:
        return None

    if not isinstance(df["month_year"].dtype, pd.PeriodDtype):
        df["month_year"] = pd.PeriodIndex(df["month_year"].astype(str), freq="M")

    df = df.sort_values("month_year")

    current_month = pd.Timestamp.today().to_period("M")
    last_full_month = current_month - 1

    df = df[df["month_year"] <= last_full_month]

    if df.empty:
        return None

    latest_month = df["month_year"].max()
    month_display = latest_month.to_timestamp().strftime("%B %Y")

    metric_df = (
        df[["month_year", "reorder_rate"]]
        .dropna()
        .sort_values("reorder_rate", ascending=False)
        .reset_index(drop=True)
    )

    if metric_df.empty:
        return None

    metric_df["rank"] = metric_df.index + 1

    latest_match = metric_df[metric_df["month_year"] == latest_month]

    if latest_match.empty:
        return None

    rank = int(latest_match.iloc[0]["rank"])

    if rank > 3:
        return None

    latest_value = latest_match.iloc[0]["reorder_rate"]

    below_row = metric_df[metric_df["rank"] == rank + 1]

    pts_vs_below = None

    if not below_row.empty:
        below_value = below_row.iloc[0]["reorder_rate"]

        if pd.notna(below_value):
            diff = latest_value - below_value

            # 0.02 = 2 percentage points if reorder_rate is stored as decimal
            if diff >= 0.02:
                pts_vs_below = diff

    reorder_rate_display = f"{latest_value * 100:.1f}%"
    value_label = f"{reorder_rate_display} reorder rate"

    summary = f"{month_display} was your #{rank} all-time month for reorder rate"

    parts = [
        {"type": "chip", "value": month_display, "tone": "neutral"},
        {"type": "text", "value": " was your "},
        {
            "type": "chip",
            "value": f"#{rank} all-time",
            "tone": "positive",
        },
        {"type": "text", "value": " month for reorder rate"},
    ]

    if pts_vs_below is not None:
        pts = pts_vs_below * 100
        pts_display = f"{pts:.1f} pts"

        summary += f", coming in {pts_display} above the next-best month"

        parts[-1]["value"] += f", coming in {pts_display} above the next-best month"

    summary += "."
    parts.append({"type": "text", "value": "."})

    parts.append({
        "type": "chip",
        "value": value_label,
        "tone": "positive",
    })

    return {
        "type": "top_reorder_rate_month",
        "summary": summary,
        "parts": parts,
        "metrics": [
            {
                "metric": "reorder_rate",
                "rank": rank,
                "value": latest_value,
                "pts_vs_below": pts_vs_below,
            }
        ],
    }

import pandas as pd

def build_top_reorder_rate_month_insight(monthly_df):
    """
    Returns an insight if latest full month is top 3 all-time
    for reorder rate. Otherwise returns None.
    """

    df = monthly_df.copy()

    if df.empty or "month_year" not in df.columns or "reorder_rate" not in df.columns:
        return None

    if not isinstance(df["month_year"].dtype, pd.PeriodDtype):
        df["month_year"] = pd.PeriodIndex(df["month_year"].astype(str), freq="M")

    df = df.sort_values("month_year")

    current_month = pd.Timestamp.today().to_period("M")
    last_full_month = current_month - 1

    df = df[df["month_year"] <= last_full_month]

    if df.empty:
        return None

    latest_month = df["month_year"].max()
    month_display = latest_month.to_timestamp().strftime("%B %Y")

    metric_df = (
        df[["month_year", "reorder_rate"]]
        .dropna()
        .sort_values("reorder_rate", ascending=False)
        .reset_index(drop=True)
    )

    if metric_df.empty:
        return None

    metric_df["rank"] = metric_df.index + 1

    latest_match = metric_df[metric_df["month_year"] == latest_month]

    if latest_match.empty:
        return None

    rank = int(latest_match.iloc[0]["rank"])

    if rank > 3:
        return None

    latest_value = latest_match.iloc[0]["reorder_rate"]

    below_row = metric_df[metric_df["rank"] == rank + 1]

    pts_vs_below = None

    if not below_row.empty:
        below_value = below_row.iloc[0]["reorder_rate"]

        if pd.notna(below_value):
            diff = latest_value - below_value

            # 0.02 = 2 percentage points if reorder_rate is stored as decimal
            if diff >= 0.02:
                pts_vs_below = diff

    reorder_rate_display = f"{latest_value * 100:.1f}%"
    value_label = f"{reorder_rate_display} reorder rate"

    summary = f"{month_display} was your #{rank} all-time month for reorder rate"

    parts = [
        {"type": "chip", "value": month_display, "tone": "neutral"},
        {"type": "text", "value": " was your "},
        {
            "type": "chip",
            "value": f"#{rank} all-time",
            "tone": "positive",
        },
        {"type": "text", "value": " month for reorder rate"},
    ]

    if pts_vs_below is not None:
        pts = pts_vs_below * 100
        pts_display = f"{pts:.1f} pts"

        summary += f", coming in {pts_display} above the next-best month"

        parts[-1]["value"] += f", coming in {pts_display} above the next-best month"

    summary += "."
    parts.append({"type": "text", "value": "."})

    parts.append({
        "type": "chip",
        "value": value_label,
        "tone": "positive",
    })

    return {
        "type": "top_reorder_rate_month",
        "summary": summary,
        "parts": parts,
        "metrics": [
            {
                "metric": "reorder_rate",
                "rank": rank,
                "value": latest_value,
                "pts_vs_below": pts_vs_below,
            }
        ],
    }
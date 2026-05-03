import pandas as pd
from backend.insights.insights_helper import build_filter_context


def build_sku_velocity_insight(sku_df, filters=None):
    df = sku_df.copy()

    change_col = "vpo_l3m_abs"

    df = df[df["vpo_l3m"].notna()]
    df = df[df["vpo_l3m"] > 0]

    if df.empty:
        return None
    
    for col in ["vpo_3m", "vpo_l3m", "vpo_l3m_pct", "vpo_l3m_abs"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["sku", "vpo_3m", "vpo_l3m", "vpo_l3m_pct", "vpo_l3m_abs"])

    if df.empty:
        return None

    # Focus on meaningful SKUs only
    df = df[
        (df["units_l3m"] >= 50) &
        (df[change_col].abs() >= 0.25)
    ]

    if df.empty:
        return None

    row = df.sort_values(change_col, ascending=False).iloc[0]

    direction = "improving" if row[change_col] > 0 else "declining"
    up_down = "up" if row[change_col] > 0 else "down"

    tone = "positive" if row[change_col] > 0 else "negative"

    context_str, context_parts = build_filter_context(
        filters,
        exclude_keys={"sku"},
    )

    return {
        "type": "sku_velocity",
        "summary": (
            f"{row['sku']} velocity is {up_down} {abs(row[change_col]):.1f} "
            f"units per pod per week{context_str} vs the prior 3 months."
        ),
        "parts": [
            {"type": "chip", "value": row["sku"], "tone": "neutral"},
            {"type": "text", "value": " velocity is "},
            {"type": "chip", "value": up_down, "tone": tone},
            {"type": "text", "value": " "},
            {
                "type": "chip",
                "value": f"{abs(row[change_col]):.1f} units per pod/week",
                "tone": tone,
            },
            *context_parts,
            {"type": "text", "value": " vs the prior 3 months."},
        ],
        "sku": row["sku"],
        "abs_change": row[change_col],
        "pct_change": row.get("vpo_l3m_pct"),
    }


def get_last_completed_months(df, month_col="month_year", n=3):

    d = df.copy()
    d[month_col] = pd.PeriodIndex(d[month_col], freq="M")

    current_month = pd.Timestamp.today().to_period("M")

    completed_months = sorted(
        d.loc[d[month_col] < current_month, month_col].dropna().unique()
    )

    return completed_months[-n:]


def build_void_opportunity_insight(df, filters=None, penetration_threshold=0.15):
    """
    Returns the single highest-impact void opportunity insight.
    """

    d = df.copy()
    d["month_year"] = pd.PeriodIndex(d["month_year"], freq="M")

    # --- 1. Get last 3 months INCLUDING current (for void detection)
    current_month = pd.Timestamp.today().to_period("M")
    all_months = sorted(d["month_year"].unique())

    last_3m = [m for m in all_months if m <= current_month][-3:]

    if len(last_3m) < 2:
        return None

    d = d[d["month_year"].isin(last_3m)]

    if d.empty:
        return None

    # --- 2. Store universe (stores buying the brand)
    store_total = (
        d.groupby(["chain", "coded_customer"], as_index=False)
        .agg(total_units_3m=("units", "sum"))
    )

    active_stores = store_total[store_total["total_units_3m"] > 0]

    if active_stores.empty:
        return None

    # --- 3. Store x SKU units (for carry detection)
    store_sku = (
        d.groupby(["chain", "coded_customer", "sku"], as_index=False)
        .agg(units_3m=("units", "sum"))
    )

    # --- 4. SKU universe per chain
    chain_skus = (
        d.groupby(["chain", "sku"], as_index=False)
        .agg(chain_sku_units_3m=("units", "sum"))
    )

    chain_skus = chain_skus[chain_skus["chain_sku_units_3m"] > 0]

    universe = active_stores[["chain", "coded_customer"]].merge(
        chain_skus[["chain", "sku"]],
        on="chain",
        how="inner"
    )

    merged = universe.merge(
        store_sku,
        on=["chain", "coded_customer", "sku"],
        how="left"
    )

    merged["units_3m"] = merged["units_3m"].fillna(0)

    # --- 5. Evaluate voids
    results = []

    grouped = merged.groupby(["chain", "sku"])

    # Precompute completed months for velocity (EXCLUDE current)
    completed_months = [m for m in all_months if m < current_month][-3:]

    for (chain, sku), g in grouped:

        total_stores = g["coded_customer"].nunique()

        carrying_df = g[g["units_3m"] > 0]
        carrying_stores = carrying_df["coded_customer"].nunique()

        if carrying_stores < 2:
            continue

        penetration = carrying_stores / total_stores if total_stores > 0 else 0

        if penetration < penetration_threshold:
            continue

        void_stores = total_stores - carrying_stores

        if void_stores <= 0:
            continue

        if void_stores < 2:
            continue

        # --- Velocity (EXCLUDE current month)
        velocity_df = df.copy()
        velocity_df["month_year"] = pd.PeriodIndex(velocity_df["month_year"], freq="M")

        velocity_df = velocity_df[
            (velocity_df["month_year"].isin(completed_months)) &
            (velocity_df["chain"] == chain) &
            (velocity_df["sku"] == sku)
        ]

        velocity_by_store = (
            velocity_df.groupby("coded_customer", as_index=False)
            .agg(units_3m_completed=("units", "sum"))
        )

        velocity_by_store = velocity_by_store[
            velocity_by_store["units_3m_completed"] > 0
        ]

        if velocity_by_store.empty:
            continue

        median_units_3m = velocity_by_store["units_3m_completed"].median()
        vpo_weekly = median_units_3m / 13

        if vpo_weekly <= 0:
            continue

        # --- Opportunity
        annual_units = vpo_weekly * void_stores * 52

        if annual_units < 200:
            continue

        results.append({
            "chain": chain,
            "sku": sku,
            "void_stores": int(void_stores),
            "carrying_stores": int(carrying_stores),
            "total_stores": int(total_stores),
            "penetration": round(penetration, 2),
            "vpo_weekly": round(vpo_weekly, 2),
            "annual_units": int(annual_units),
            "captured_units": int(annual_units),
        })

    if not results:
        return None

    # --- 6. Pick highest impact
    top = sorted(results, key=lambda x: x["captured_units"], reverse=True)[0]

    context_str, context_parts = build_filter_context(
        filters,
        exclude_keys={"sku", "chain"},
    )

    # --- 7. Return insight
    return {
        "type": "distribution_opportunity",
        "summary": (
            f"{top['sku']} isn't sold in {top['void_stores']} stores in {top['chain']}{context_str}, "
            f"representing ~{top['captured_units']:,} units/year in upside."
        ),
        "parts": [
            {"type": "chip", "value": top["sku"], "tone": "neutral"},
            {"type": "text", "value": " isn't sold in "},
            {"type": "chip", "value": f"{top['void_stores']} stores", "tone": "neutral"},
            {"type": "text", "value": " in "},
            {"type": "chip", "value": top["chain"], "tone": "neutral"},
            *context_parts,
            {"type": "text", "value": ", representing "},
            {
                "type": "chip",
                "value": f"~{top['captured_units']:,} units/year",
                "tone": "positive",
            },
            {"type": "text", "value": " in upside."},
        ],
        "sku": top["sku"],
        "chain": top["chain"],
        "impact_units": top["captured_units"],
    }


def build_velocity_gap_opportunity_insight(chain_sku_df, filters=None):
    df = chain_sku_df.copy()

    required_cols = {
        "channel",
        "sku",
        "chain",
        "vpo_3m",
        "buying_stores_3m",
        "units_3m",
    }

    if not required_cols.issubset(df.columns):
        return None

    df = df.dropna(subset=list(required_cols))

    EXCLUDED_CHAINS = {"FRESHDIRECT", "AMAZON", "THRIVE MARKET"}

    df = df[~df["chain"].astype(str).str.upper().isin(EXCLUDED_CHAINS)]

    df = df[
        (df["buying_stores_3m"] >= 2)
        & (df["units_3m"] >= 5)
        & (df["vpo_3m"] > 0)
        & (df["vpo_3m"] <= 15)
    ]
    if "month_year" in df.columns:
        latest_month = df["month_year"].max()
        df = df[df["month_year"] == latest_month]

    if df.empty:
        return None

    opportunities = []

    for (channel, sku), group_df in df.groupby(["channel", "sku"]):
        if group_df["chain"].nunique() < 2:
            continue

        high = group_df.sort_values("vpo_3m", ascending=False).iloc[0]
        low = group_df.sort_values("vpo_3m", ascending=True).iloc[0]

        if high["chain"] == low["chain"]:
            continue

        gap_ratio = high["vpo_3m"] / low["vpo_3m"]

        if gap_ratio < 1.3:
            continue

        velocity_gap = high["vpo_3m"] - low["vpo_3m"]

        # Conservative assumption: lower-performing chain closes 50% of the gap
        captured_gap = velocity_gap * 0.5

        estimated_units_opportunity = captured_gap * low["buying_stores_3m"] * 4

        if estimated_units_opportunity < 10:
            continue

        opportunities.append(
            {
                "channel": channel,
                "sku": sku,
                "high": high,
                "low": low,
                "gap_ratio": gap_ratio,
                "estimated_units_opportunity": estimated_units_opportunity,
            }
        )

    if not opportunities:
        return None

    best = max(opportunities, key=lambda x: x["estimated_units_opportunity"])

    channel = best["channel"]
    sku = best["sku"]
    high = best["high"]
    low = best["low"]
    gap_ratio = best["gap_ratio"]
    estimated_units_opportunity = best["estimated_units_opportunity"]

    context_str, context_parts = build_filter_context(
        filters,
        exclude_keys={"sku", "chain", "channel"},
    )

    return {
        "type": "distribution_opportunity",
        "summary": (
            f"{sku} is selling {gap_ratio:.1f}x faster in "
            f"{high['chain']} than {low['chain']}{context_str}."
        ),
        "parts": [
            {"type": "chip", "value": str(sku), "tone": "neutral"},
            {"type": "text", "value": " is selling "},
            {
                "type": "chip",
                "value": f"{gap_ratio:.1f}x faster",
                "tone": "positive",
            },
            {"type": "text", "value": " in "},
            {"type": "chip", "value": str(high["chain"]), "tone": "neutral"},
            {"type": "text", "value": " than "},
            {"type": "chip", "value": str(low["chain"]), "tone": "neutral"},
            *context_parts,
            {"type": "text", "value": ", representing "},
            {
                "type": "chip",
                "value": f"~{estimated_units_opportunity:,.0f} units/month",
                "tone": "positive",
            },
            {"type": "text", "value": " in upside."},
        ],
    }
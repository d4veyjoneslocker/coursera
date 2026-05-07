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


def build_void_opportunity_insight(df, filters=None):
    table = df.copy()

    if table.empty:
        return None

    required_cols = [
        "channel",
        "sku",
        "chain",
        "vpo_3m",
        "buying_stores_3m",
        "total_brand_stores_3m",
        "void_stores_3m",
        "brand_units_lift_pct",
    ]

    missing_cols = [col for col in required_cols if col not in table.columns]
    if missing_cols:
        return None

    table = table[
        table["chain"].notna()
        & ~table["chain"].astype(str).str.strip().str.upper().eq("CONFIDENTIAL")
    ].copy()

    if table.empty:
        return None

    table = table[
        (table["void_stores_3m"] > 0)
        & (table["buying_stores_3m"] >= 2)
        & (table["brand_units_lift_pct"].notna())
        & (table["brand_units_lift_pct"] > 0)
        & (table["vpo_3m"] > 0)
    ].copy()

    if table.empty:
        return None

    table["captured_units"] = (
        table["vpo_3m"] * table["void_stores_3m"] * 52
    )

    table = table[table["captured_units"] >= 200]

    if table.empty:
        return None

    top = table.sort_values("captured_units", ascending=False).iloc[0]

    context_str, context_parts = build_filter_context(
        filters,
        exclude_keys={"sku", "chain", "channel"},
    )

    sku = top["sku"]
    chain = top["chain"]
    channel = top["channel"]

    buying_stores = int(top["carrying_stores_6m"])
    void_stores = int(top["void_stores_3m"])
    total_stores = int(top["total_brand_stores_3m"])

    vpo = float(top["vpo_3m"])
    lift = float(top["brand_units_lift_pct"])
    captured_units = int(top["captured_units"])

    # -----------------------------
# New insight signals
# -----------------------------
    opportunity_stores_1_sku = int(top.get("opportunity_stores_1_sku", 0) or 0)

    assortment_distribution_context = ""

    if opportunity_stores_1_sku >= 5:
        assortment_distribution_context = (
            f"{opportunity_stores_1_sku} of these stores are only carrying 1 SKU, "
            f"suggesting an opportunity to expand assortment within existing accounts. "
        )

    distribution_context = ""

    if (
        void_stores >= 10
        and buying_stores >= 5
        and lift > 0.2
    ):
        distribution_context = (
            "This pattern may indicate a distribution or item setup issue, "
            "where the SKU is present in some stores but not being consistently distributed across the chain. "
        )

    assortment_context = ""

    opportunity_avg_skus = top.get("opportunity_avg_skus")
    chain_avg_skus = top.get("chain_avg_skus")
    channel_avg_skus = top.get("channel_avg_skus")

    if (
        pd.notna(opportunity_avg_skus)
        and pd.notna(chain_avg_skus)
        and pd.notna(channel_avg_skus)
    ):
        assortment_context = (
            f"These opportunity stores carry {float(opportunity_avg_skus):.1f} SKUs on average, "
            f"compared to {float(chain_avg_skus):.1f} across {chain} and "
            f"{float(channel_avg_skus):.1f} across {channel}. "
        )

    headline = f"{sku} may have room to expand in {chain}."

    body = (
        f"{sku} is currently sold in {buying_stores} of {total_stores} active {chain} stores "
        f"in {channel}, leaving {void_stores} stores that buy the brand but do not carry this SKU. "
        f"{assortment_context}"
        f"{assortment_distribution_context}"
        f"{distribution_context}"
        f"Among the stores that do carry it, velocity is {vpo:.1f} units per store per week. "
        f"Those stores also sell {lift:.0%} more total brand units per store than stores that do not carry it. "
        f"Expanding into the remaining stores could represent approximately {captured_units:,} units per year."
    )

    summary = (
        f"{sku} is missing from {void_stores} active {chain} stores{context_str}, "
        f"with ~{captured_units:,} units/year in potential upside."
    )

    return {
        "type": "distribution_opportunity",
        "section": "opportunities",
        "priority": 30,

        "summary": summary,

        "parts": [
            {"type": "chip", "value": sku, "tone": "neutral"},
            {"type": "text", "value": " is missing from "},
            {
                "type": "chip",
                "value": f"{void_stores} stores",
                "tone": "neutral",
            },
            {"type": "text", "value": " in "},
            {"type": "chip", "value": chain, "tone": "neutral"},
            *context_parts,
            {"type": "text", "value": ", representing "},
            {
                "type": "chip",
                "value": f"~{captured_units:,} units/year",
                "tone": "positive",
            },
            {"type": "text", "value": " in upside."},
        ],

        "headline": headline,
        "body": body,

        "body_parts": [
            {"type": "sku_chip", "value": sku},

            {"type": "text", "value": " is currently sold in "},

            {
                "type": "metric_chip",
                "value": f"{buying_stores} stores",
                "tone": "neutral",
            },

            {"type": "text", "value": " in "},

            {"type": "chain_chip", "value": chain},

            {
                "type": "text",
                "value": ", leaving ",
            },

            {
                "type": "metric_chip",
                "value": f"{void_stores} stores",
                "tone": "positive",
            },

            {
                "type": "text",
                "value": " that buy the brand but do not carry this SKU. These non-buying stores carry only ",
            },

            {
                "type": "metric_chip",
                "value": f"{opportunity_avg_skus:.1f} SKUs on average",
                "tone": "neutral",
            },

            {"type": "text", "value": ", compared to "},

            {
                "type": "metric_chip",
                "value": f"{chain_avg_skus:.1f} across {chain}",
                "tone": "neutral",
            },

            {"type": "text", "value": " and "},

            {
                "type": "metric_chip",
                "value": f"{channel_avg_skus:.1f} across the {channel} channel",
                "tone": "neutral",
            },

            {
                "type": "text",
                "value": ". This pattern may indicate a distribution or item setup issue, as the SKU is present in some stores but not consistently distributed across the chain. ",
            },

            {"type": "chain_chip", "value": chain},

            {"type": "text", "value": " stores currently carrying "},

            {"type": "sku_chip", "value": sku},

            {"type": "text", "value": " sell "},

            {
                "type": "metric_chip",
                "value": f"{lift:.0%} more total brand units/store",
                "tone": "positive",
            },

            {
                "type": "text",
                "value": " than stores that do not currently carry it, while ",
            },

            {"type": "sku_chip", "value": sku},

            {"type": "text", "value": " itself averages "},

            {
                "type": "metric_chip",
                "value": f"{vpo:.1f} units/store/week",
                "tone": "positive",
            },

            {
                "type": "text",
                "value": ". Based on this rate, expanding into the remaining stores could represent approximately ",
            },

            {
                "type": "metric_chip",
                "value": f"{captured_units:,} units/year",
                "tone": "positive",
            },

            {"type": "text", "value": "."},
        ],

        "metrics": {
            "buying_stores_3m": buying_stores,
            "void_stores_3m": void_stores,
            "total_brand_stores_3m": total_stores,
            "vpo_3m": vpo,
            "brand_units_lift_pct": lift,
            "impact_units": captured_units,
            "opportunity_avg_skus": opportunity_avg_skus,
            "chain_avg_skus": chain_avg_skus,
            "channel_avg_skus": channel_avg_skus,
            "carrying_brand_units_per_store_3m": top.get(
                "carrying_brand_units_per_store_3m"
            ),
            "noncarrying_brand_units_per_store_3m": top.get(
                "noncarrying_brand_units_per_store_3m"
            ),
        },

        "entities": {
            "sku": sku,
            "chain": chain,
            "channel": channel,
        },

        "sku": sku,
        "chain": chain,
        "channel": channel,
        "impact_units": captured_units,

        "cta": {
            "label": "View opportunity stores",
            "href": (
                f"/insights/distribution_opportunity"
                f"?chain={chain}&sku={sku}&channel={channel}"
            ),
        },
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
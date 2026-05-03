from backend.insights.insights_helper import build_filter_context


def build_chain_decline_insight(chain_df, filters=None):
    df = chain_df.copy()

    df = df[df["units_l3m"] > 0]
    if df.empty:
        return None

    change_col = "units_l3m_abs"

    total_change = df[change_col].sum()

    if total_change >= 0:
        return None

    total_decline = abs(df[df[change_col] < 0][change_col].sum())

    if total_decline == 0:
        return None

    df["contribution"] = df[change_col].apply(
        lambda x: abs(x) / total_decline if x < 0 else 0
    )

    total_prior = df["units_l3m"].sum()

    if total_prior == 0:
        return None

    df["prior_share"] = df["units_l3m"] / total_prior

    df = df[df["chain"].astype(str).str.upper() != "CONFIDENTIAL"]

    df = df[
        (df["prior_share"] >= 0.02) &
        (df[change_col] <= -50)
    ]

    if df.empty:
        return None

    row = df.sort_values(change_col).iloc[0]
    contribution = row["contribution"]

    context_str, context_parts = build_filter_context(
        filters,
        exclude_keys={"chain"},
    )

    return {
        "type": "chain_decline_driver",
        "summary": (
            f"{row['chain']} drove {contribution:.0%} of your total unit decline{context_str}, "
            f"down {abs(row[change_col]):,.0f} units vs the prior 3 months."
        ),
        "parts": [
            {"type": "chip", "value": row["chain"], "tone": "neutral"},
            {"type": "text", "value": " drove "},
            {"type": "chip", "value": f"{contribution:.0%}", "tone": "negative"},
            {"type": "text", "value": " of your total unit decline"},
            *context_parts,
            {"type": "text", "value": ", "},
            {
                "type": "chip",
                "value": f"down {abs(row[change_col]):,.0f} units",
                "tone": "negative",
            },
            {"type": "text", "value": " vs the prior 3 months."},
        ],
        "chain": row["chain"],
        "abs_change": row[change_col],
        "pct_change": row.get("units_l3m_pct"),
        "contribution": contribution,
    }


def build_chain_growth_insight(chain_df, filters=None):
    df = chain_df.copy()

    change_col = "units_l3m_abs"

    df = df[df["units_l3m"] > 0]
    if df.empty:
        return None

    total_change = df[change_col].sum()

    if total_change <= 0:
        return None

    total_growth = df[df[change_col] > 0][change_col].sum()

    if total_growth == 0:
        return None

    df["contribution"] = df[change_col].apply(
        lambda x: x / total_growth if x > 0 else 0
    )

    total_prior = df["units_l3m"].sum()

    if total_prior == 0:
        return None

    df["prior_share"] = df["units_l3m"] / total_prior

    df = df[
        (df["chain"].astype(str).str.upper() != "CONFIDENTIAL") &
        (df[change_col] >= 50) &
        (df["contribution"] >= 0.10)
    ]

    if df.empty:
        return None

    row = df.sort_values(change_col, ascending=False).iloc[0]

    context_str, context_parts = build_filter_context(
        filters,
        exclude_keys={"chain"},
    )

    return {
        "type": "chain_growth_driver",
        "summary": (
            f"{row['chain']} drove {row['contribution']:.0%} of your total unit growth{context_str}, "
            f"up {row[change_col]:,.0f} units vs the prior 3 months."
        ),
        "parts": [
            {"type": "chip", "value": row["chain"], "tone": "neutral"},
            {"type": "text", "value": " drove "},
            {"type": "chip", "value": f"{row['contribution']:.0%}", "tone": "positive"},
            {"type": "text", "value": " of your total unit growth"},
            *context_parts,
            {"type": "text", "value": ", "},
            {
                "type": "chip",
                "value": f"up {row[change_col]:,.0f} units",
                "tone": "positive",
            },
            {"type": "text", "value": " vs the prior 3 months."},
        ],
        "chain": row["chain"],
        "abs_change": row[change_col],
        "pct_change": row.get("units_l3m_pct"),
        "contribution": row["contribution"],
    }
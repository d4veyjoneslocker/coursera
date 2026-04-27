def build_chain_decline_insight(chain_df):
    """
    Returns a single most important decline insight at the chain level.
    """

    df = chain_df.copy()

    # --- Guard: need prior data
    df = df[df["units_l3m"] > 0]

    if df.empty:
        return None

    # --- Total change
    total_change = df["units_l3m_abs"].sum()

    # If business isn't declining, skip
    if total_change >= 0:
        return None

    # --- Add contribution
    df["contribution"] = df["units_l3m_abs"] / total_change

    # --- Materiality filters (simple V1)
    total_prior = df["units_l3m"].sum()

    df["prior_share"] = df["units_l3m"] / total_prior

    df = df[
        (df["prior_share"] >= 0.02) &  # at least 2% of business
        (df["units_l3m_abs"] <= -50)  # at least -50 units decline
    ]

    if df.empty:
        return None

    # --- Pick biggest driver (most negative change)
    row = df.sort_values("units_l3m_abs").iloc[0]

    contribution = row["contribution"]

    insight = {
        "type": "chain_decline_driver",
        "summary": (
            f"{row['chain']} drove {abs(contribution):.0%} of your total unit decline, "
            f"down {abs(row['units_l3m_abs']):,.0f} units vs the prior 3 months."
        ),
        "parts": [
            {"type": "chip", "value": row["chain"], "tone": "neutral"},
            {"type": "text", "value": " drove "},
            {"type": "chip", "value": f"{abs(contribution):.0%}", "tone": "negative"},
            {"type": "text", "value": " of your total unit decline, "},
            {"type": "chip", "value": f"down {abs(row['units_l3m_abs']):,.0f} units", "tone": "negative"},
            {"type": "text", "value": " vs the prior 3 months."},
        ],
        "chain": row["chain"],
        "abs_change": row["units_l3m_abs"],
        "pct_change": row.get("units_l3m_pct"),
        "contribution": contribution,
    }

    return insight

def build_chain_growth_insight(chain_df):
    df = chain_df.copy()

    change_col = "units_l3m_abs"

    df = df[df["units_l3m"] > 0]

    if df.empty:
        return None

    total_change = df[change_col].sum()

    # If business is not growing, skip
    if total_change <= 0:
        return None

    total_prior = df["units_l3m"].sum()

    df["prior_share"] = df["units_l3m"] / total_prior
    df["contribution"] = df[change_col] / total_change

    df = df[
        (df["prior_share"] >= 0.02) &
        (df[change_col] >= 50)
    ]

    if df.empty:
        return None

    row = df.sort_values(change_col, ascending=False).iloc[0]

    return {
        "type": "chain_growth_driver",
        "summary": (
            f"{row['chain']} drove {row['contribution']:.0%} of your total unit growth, "
            f"up {row[change_col]:,.0f} units vs the prior 3 months."
        ),
        "parts": [
            {"type": "chip", "value": row["chain"], "tone": "neutral"},
            {"type": "text", "value": " drove "},
            {"type": "chip", "value": f"{row['contribution']:.0%}", "tone": "positive"},
            {"type": "text", "value": " of your total unit growth, "},
            {"type": "chip", "value": f"up {row[change_col]:,.0f} units", "tone": "positive"},
            {"type": "text", "value": " vs the prior 3 months."},
        ],
        "chain": row["chain"],
        "abs_change": row[change_col],
        "pct_change": row.get("units_l3m_pct"),
        "contribution": row["contribution"],
    }
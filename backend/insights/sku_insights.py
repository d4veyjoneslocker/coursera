def build_sku_velocity_insight(sku_df):
    df = sku_df.copy()

    change_col = "vpo_l3m_abs"

    df = df[df["vpo_l3m"].notna()]
    df = df[df["vpo_l3m"] > 0]

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

    return {
        "type": "sku_velocity",
        "summary": (
            f"{row['sku']} velocity is {up_down} {abs(row[change_col]):.1f} "
            f"units per pod per week vs the prior 3 months."
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
            {"type": "text", "value": " vs the prior 3 months."},
        ],
        "sku": row["sku"],
        "abs_change": row[change_col],
        "pct_change": row.get("vpo_l3m_pct"),
    }
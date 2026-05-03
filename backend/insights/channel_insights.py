from backend.insights.insights_helper import build_filter_context


def build_channel_reorder_driver_insight(channel_df, filters=None):
    df = channel_df.copy()

    change_col = "reorder_rate_l3m_abs"

    df = df[
        df[change_col].notna()
        & (df["buying_stores_l3m"] >= 10)
        & (df[change_col].abs() >= 0.05)
    ]

    if df.empty:
        return None

    row = df.loc[df[change_col].abs().idxmax()]

    verb = "dropping" if row[change_col] < 0 else "improving"
    direction_word = "down" if row[change_col] < 0 else "up"
    tone = "negative" if row[change_col] < 0 else "positive"

    # 👇 ADD THIS
    context_str, context_parts = build_filter_context(
        filters,
        exclude_keys={"channel"},
    )

    return {
        "type": "channel_reorder_driver",
        "summary": (
            f"Reorder rate is {verb} in {row['channel']}{context_str}, "
            f"{direction_word} {abs(row[change_col]):.0%} pts vs the prior 3 months."
        ),
        "parts": [
            {"type": "text", "value": "Reorder rate is "},
            {"type": "chip", "value": verb, "tone": tone},
            {"type": "text", "value": " in "},
            {"type": "chip", "value": row["channel"], "tone": "neutral"},
            *context_parts,  # 👈 ADD THIS
            {"type": "text", "value": ", "},
            {
                "type": "chip",
                "value": f"{direction_word} {abs(row[change_col]):.0%} pts",
                "tone": tone,
            },
            {"type": "text", "value": " vs the prior 3 months."},
        ],
        "channel": row["channel"],
        "abs_change": row[change_col],
    }
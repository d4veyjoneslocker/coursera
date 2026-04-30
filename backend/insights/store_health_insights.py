def build_chain_struggling_insight(df):
    df = df.copy()

    # Get one row per store
    store_status = (
        df.groupby(["chain", "coded_customer"], as_index=False)
        .agg(status=("status", "first"))
    )

    # Count by chain + status
    counts = (
        store_status.groupby(["chain", "status"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    # Total stores per chain
    counts["total"] = counts.drop(columns=["chain"]).sum(axis=1)

    # % struggling
    if "Struggling" not in counts.columns:
        counts["Struggling"] = 0

    counts["struggling_pct"] = counts["Struggling"] / counts["total"]

    # Filter meaningful chains
    counts = counts[counts["total"] >= 10]

    if counts.empty:
        return None

    # Compare vs overall
    total_stores = counts["total"].sum()
    total_struggling = counts["Struggling"].sum() if "Struggling" in counts else 0

    overall_pct = total_struggling / total_stores if total_stores > 0 else 0

    counts["vs_avg"] = counts["struggling_pct"] - overall_pct

    # Focus on chains worse than average
    counts = counts[counts["vs_avg"] > 0.05]

    if counts.empty:
        return None

    row = counts.sort_values("vs_avg", ascending=False).iloc[0]

    return {
        "type": "chain_struggling",
        "summary": (
            f"{row['chain']} has {row['struggling_pct']:.0%} of stores marked as struggling, "
            f"{row['vs_avg']:+.0%} pts vs your overall average."
        ),
        "parts": [
            {"type": "chip", "value": row["chain"], "tone": "neutral"},
            {"type": "text", "value": " has "},
            {
                "type": "chip",
                "value": f"{row['struggling_pct']:.0%}",
                "tone": "negative",
            },
            {"type": "text", "value": " of stores marked as struggling, "},
            {
                "type": "chip",
                "value": f"{row['vs_avg']:+.0%} pts",
                "tone": "negative",
            },
            {"type": "text", "value": " vs your overall average."},
        ],
        "chain": row["chain"],
        "struggling_pct": row["struggling_pct"],
    }
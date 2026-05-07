import pandas as pd

from backend.insights.insights_helper import build_filter_context
from backend.insights.diagnostics import (
    get_root_cause_concentration,
    describe_root_cause_signal,
)


def build_chain_struggling_insight(df, filters=None, limit: int = 1):
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
        return [] if limit > 1 else None

    # Compare vs overall
    total_stores = counts["total"].sum()
    total_struggling = counts["Struggling"].sum() if "Struggling" in counts else 0
    overall_pct = total_struggling / total_stores if total_stores > 0 else 0

    counts["vs_avg"] = counts["struggling_pct"] - overall_pct

    # Focus on chains worse than average
    counts = counts[counts["vs_avg"] > 0.05]

    if counts.empty:
        return [] if limit > 1 else None

    insights = []

    for rank, (_, row) in enumerate(
        counts.sort_values("vs_avg", ascending=False).head(limit).iterrows()
    ):
        chain = row["chain"]
        struggling_count = int(row["Struggling"])
        total_count = int(row["total"])
        struggling_pct = row["struggling_pct"]
        vs_avg = row["vs_avg"]

        context_str, context_parts = build_filter_context(
            filters,
            exclude_keys={"chain", "status"},
        )

        # -----------------------------
        # Supporting diagnostic context
        # -----------------------------
        struggling_rows = df[
            (df["chain"] == chain) &
            (df["status"] == "Struggling")
        ].copy()

        chain_universe = df[df["chain"] == chain].copy()

        root_cause = get_root_cause_concentration(
            affected_df=struggling_rows,
            universe_df=chain_universe,
            dimensions=["sku", "state"],
        )

        root_cause_text = describe_root_cause_signal(root_cause)

        # Latest order month
        latest_month_display = None
        latest_count = 0

        if "last_month_purchased" in struggling_rows.columns and not struggling_rows.empty:
            temp = (
                struggling_rows.groupby(["chain", "coded_customer"], as_index=False)
                .agg(last_month_purchased=("last_month_purchased", "first"))
            )

            latest_month = temp["last_month_purchased"].max()

            if pd.notna(latest_month):
                latest_count = int(
                    temp["last_month_purchased"].eq(latest_month).sum()
                )

                if hasattr(latest_month, "to_timestamp"):
                    latest_month_display = latest_month.to_timestamp().strftime("%B %Y")
                else:
                    latest_month_display = pd.to_datetime(latest_month).strftime("%B %Y")

        # -----------------------------
        # Narrative
        # -----------------------------
        headline = f"{chain} has a high share of struggling stores."

        body = (
            f"{chain} has {struggling_count} of {total_count} stores marked as struggling, "
            f"or {struggling_pct:.0%} of its store base. That is {vs_avg:+.0%} pts"
            "above your overall average, which suggests the issue is concentrated in this chain rather than spread evenly across the business. "
        )

        if latest_month_display:
            body += (
                f"The most recent orders from this group came in {latest_month_display}, "
                f"with {latest_count} stores last ordering that month. "
            )

        if root_cause and root_cause_text:
            body += f"{root_cause_text} "

        summary = (
            f"{chain} has {struggling_pct:.0%} of stores marked as struggling{context_str}, "
            f"{vs_avg:+.0%} pts vs your overall average."
        )

        insights.append({
            "type": "chain_struggling",
            "section": "at_risk",
            "priority": 20 + rank,

            "summary": summary,

            "parts": [
                {"type": "chip", "value": chain, "tone": "neutral"},
                {"type": "text", "value": " has "},
                {
                    "type": "chip",
                    "value": f"{struggling_pct:.0%}",
                    "tone": "negative",
                },
                {"type": "text", "value": " of stores marked as struggling"},
                *context_parts,
                {"type": "text", "value": ", "},
                {
                    "type": "chip",
                    "value": f"{vs_avg:+.0%} pts",
                    "tone": "negative",
                },
                {"type": "text", "value": " vs your overall average."},
            ],

            "headline": headline,
            "body": body,

            "body_parts": [
                {"type": "chain_chip", "value": chain},

                {"type": "text", "value": " has "},

                {
                    "type": "metric_chip",
                    "value": f"{struggling_count} struggling stores",
                    "tone": "negative",
                },

                {"type": "text", "value": f" out of {total_count} total stores, representing "},

                {
                    "type": "metric_chip",
                    "value": f"{struggling_pct:.0%} of the chain",
                    "tone": "negative",
                },

                {"type": "text", "value": ". That is "},

                {
                    "type": "metric_chip",
                    "value": f"{vs_avg:+.0%} pts",
                    "tone": "negative",
                },

                {
                    "type": "text",
                    "value": " above your overall average, suggesting the issue is concentrated within this chain rather than spread evenly across the business.",
                },
            ]
            + (
                [
                    {
                        "type": "text",
                        "value": " The most recent orders from this group came in ",
                    },

                    {
                        "type": "metric_chip",
                        "value": latest_month_display,
                        "tone": "neutral",
                    },

                    {"type": "text", "value": ", with "},

                    {
                        "type": "metric_chip",
                        "value": f"{latest_count} store" if latest_count == 1 else f"{latest_count} stores",
                        "tone": "neutral",
                    },

                    {"type": "text", "value": " last ordering that month."},
                ]
                if latest_month_display
                else []
            )
            + (
                [
                    {
                        "type": "text",
                        "value": f" {root_cause_text}",
                    }
                ]
                if root_cause and root_cause_text
                else []
            ),

            "metrics": {
                "struggling_pct": struggling_pct,
                "vs_avg": vs_avg,
                "struggling_stores": struggling_count,
                "total_stores": total_count,
                "overall_struggling_pct": overall_pct,
            },

            "entities": {"chain": chain},

            "diagnostics": {"root_cause": root_cause},

            "chain": chain,
            "struggling_pct": struggling_pct,

            "cta": {
                "label": "View struggling stores",
                "href": f"/insights/struggling_stores?chain={chain}",
            },
        })

    if limit == 1:
        return insights[0] if insights else None

    return insights
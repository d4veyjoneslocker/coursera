import pandas as pd
from pathlib import Path

from backend.data_pipeline.table_loader import load_org_tables, load_active_pods, load_fill_rate_df
from backend.insights.diagnostics import build_fill_rate_diagnostics, attach_fill_rate_inventory_assessments
from backend.serving.routes.inventory.inventory import _load_cached_inventory_assessments

FILL_RATE_DRIVERS = {
    "fulfillment",
    "ordering_and_fulfillment",
}


def build_chain_story(chain_row, supporting_dcs):
    return {
        "story_grain": "chain",
        "chain": chain_row["chain"],
        "sku": chain_row["sku"],
        "primary_driver": chain_row["primary_driver"],
        "chain_diagnostic": chain_row.to_dict(),
        "supporting_dcs": supporting_dcs.to_dict(orient="records"),
        "supporting_dc_count": len(supporting_dcs),
    }


def build_dc_story(dc_row, chain_row):
    return {
        "story_grain": "dc",
        "chain": dc_row["chain"],
        "sku": dc_row["sku"],
        "distributor": dc_row["distributor"],
        "dc": dc_row["dc"],
        "primary_driver": dc_row["primary_driver"],
        "dc_diagnostic": dc_row.to_dict(),
        "chain_diagnostic": (
            chain_row.to_dict()
            if chain_row is not None
            else None
        ),
    }


def select_fill_rate_stories(chain_sku, dc_sku):
    stories = []

    for _, chain_row in chain_sku.iterrows():
        chain = chain_row["chain"]
        sku = chain_row["sku"]

        dc_rows = dc_sku[
            (dc_sku["chain"] == chain)
            & (dc_sku["sku"] == sku)
        ]

        fill_rate_dcs = dc_rows[
            dc_rows["primary_driver"].isin(FILL_RATE_DRIVERS)
        ]

        # Chain-level diagnostic already says fill rate is involved.
        # Surface one chain story and use the DCs as supporting evidence.
        if chain_row["primary_driver"] in FILL_RATE_DRIVERS:
            stories.append(
                build_chain_story(
                    chain_row=chain_row,
                    supporting_dcs=fill_rate_dcs,
                )
            )

        # Chain-level diagnostic does not show a fill-rate issue,
        # but individual DC diagnostics do.
        else:
            for _, dc_row in fill_rate_dcs.iterrows():

                # Keep unmapped DC rows in diagnostics,
                # but don't create a DC story without a DC.
                if pd.isna(dc_row["dc"]):
                    continue

                stories.append(
                    build_dc_story(
                        dc_row=dc_row,
                        chain_row=chain_row,
                    )
                )

    return stories


def build_fill_rate_insights(
    features_df,
    active_pods_df,
    fill_rate_df,
    inventory_assessments,
    period="L3M",
    comparison="PP",
    end_month=None,
):
    # =====================================================
    # DIAGNOSTIC PIPELINE
    # =====================================================

    diagnostics = build_fill_rate_diagnostics(
        features_df=features_df,
        active_pods_df=active_pods_df,
        fill_rate_df=fill_rate_df,
        period=period,
        comparison=comparison,
        end_month=end_month,
    )

    # =====================================================
    # CURRENT INVENTORY CONTEXT
    # =====================================================

    dc_with_inventory = attach_fill_rate_inventory_assessments(
        dc_sku_diagnostics=diagnostics["dc_sku"],
        inventory_assessments=inventory_assessments,
    )

    # =====================================================
    # STORY SELECTION
    # =====================================================

    stories = select_fill_rate_stories(
        chain_sku=diagnostics["chain_sku"],
        dc_sku=dc_with_inventory,
    )

    return {
        "stories": stories,
        "chain_sku": diagnostics["chain_sku"],
        "chain_sku_monthly": diagnostics["chain_sku_monthly"],
        "dc_sku": dc_with_inventory,
        "dc_sku_monthly": diagnostics["dc_sku_monthly"],
    }

def narrate_fill_rate_story(story):
    """
    Turn a selected fill-rate story into user-facing narrative.

    This function does NOT make analytical decisions.
    Eligibility, driver classification, story grain, and materiality
    should already be determined upstream.

    Returns:
        {
            "headline": str,
            "summary": str,
            "detail": str | None,
            "action_context": str | None,
        }
    """

    def format_pct(value):
        if pd.isna(value):
            return None
        return f"{abs(value) * 100:.0f}%"

    def format_weeks(value):
        if pd.isna(value):
            return None
        return f"{value:.1f}"

    def period_text(period):
        if period == "L3M":
            return "over the last 3 months compared with the prior 3 months"
        if period == "L2M":
            return "over the last 2 months compared with the prior 2 months"
        return "over the comparison period"

    # =====================================================
    # CHAIN STORY
    # =====================================================

    if story["story_grain"] == "chain":

        diagnostic = story["chain_diagnostic"]
        supporting_dcs = story.get("supporting_dcs", [])

        chain = story["chain"]
        sku = story["sku"]

        velocity_pct = diagnostic.get("velocity_pct_change")
        order_pct = diagnostic.get("order_velocity_pct_change")
        fill_pct = diagnostic.get("fill_rate_pct_change")
        driver = story["primary_driver"]
        period = diagnostic.get("diagnostic_period")

        velocity_text = format_pct(velocity_pct)
        order_text = format_pct(order_pct)
        fill_text = format_pct(fill_pct)
        timeframe = period_text(period)

        # -----------------------------
        # Headline
        # -----------------------------

        if len(supporting_dcs) == 1:
            dc = supporting_dcs[0].get("dc")
            headline = (
                f"{sku} is slowing at {chain}, with fulfillment pressure "
                f"concentrated at {dc}"
            )
        elif len(supporting_dcs) > 1:
            headline = (
                f"{sku} is slowing at {chain}, with fulfillment pressure "
                f"across multiple DCs"
            )
        else:
            headline = (
                f"{sku} is slowing at {chain}, with lower fulfillment "
                f"contributing"
            )

        # -----------------------------
        # Summary
        # -----------------------------

        summary = (
            f"{sku} velocity at {chain} declined {velocity_text} {timeframe}."
        )

        if driver == "ordering_and_fulfillment":
            summary += (
                f" The data points to both softer ordering and lower "
                f"fulfillment, with order velocity down {order_text} and "
                f"fill rate down {fill_text}."
            )

        elif driver == "fulfillment":
            summary += (
                f" The data points to lower fulfillment as a meaningful "
                f"factor, with fill rate down {fill_text}."
            )

        # -----------------------------
        # DC detail
        # -----------------------------

        detail = None

        if len(supporting_dcs) == 1:
            dc_row = supporting_dcs[0]

            dc = dc_row.get("dc")
            dc_fill_pct = format_pct(
                dc_row.get("diagnostic_fill_rate_pct_change")
            )
            dc_velocity_pct = format_pct(
                dc_row.get("diagnostic_velocity_pct_change")
            )

            detail = (
                f"The fulfillment issue appears concentrated at {dc}, "
                f"where fill rate declined {dc_fill_pct} and sales velocity "
                f"declined {dc_velocity_pct}."
            )

        elif len(supporting_dcs) > 1:
            dc_names = [
                str(row.get("dc"))
                for row in supporting_dcs
                if pd.notna(row.get("dc"))
            ]

            if dc_names:
                detail = (
                    f"Fulfillment pressure is showing up across "
                    f"{len(dc_names)} DCs: {', '.join(dc_names)}."
                )

        # -----------------------------
        # Current inventory context
        # -----------------------------

        action_context = None

        if len(supporting_dcs) == 1:
            dc_row = supporting_dcs[0]

            dc = dc_row.get("dc")
            inventory_status = dc_row.get("inventory_status")
            weeks_on_hand = dc_row.get("estimated_weeks_on_hand")
            weeks_text = format_weeks(weeks_on_hand)

            if inventory_status == "action":
                action_context = (
                    f"{dc} also currently requires inventory action"
                    + (
                        f", with approximately {weeks_text} weeks on hand."
                        if weeks_text
                        else "."
                    )
                )

            elif inventory_status == "monitor":
                action_context = (
                    f"{dc} is currently being monitored for inventory risk"
                    + (
                        f", with approximately {weeks_text} weeks on hand."
                        if weeks_text
                        else "."
                    )
                )

            elif inventory_status == "healthy":
                action_context = (
                    f"{dc} currently has healthy inventory"
                    + (
                        f" at approximately {weeks_text} weeks on hand, "
                        f"so the historical fulfillment pressure does not "
                        f"appear to reflect a current inventory shortage."
                        if weeks_text
                        else "."
                    )
                )

        return {
            "headline": headline,
            "summary": summary,
            "detail": detail,
            "action_context": action_context,
        }

    # =====================================================
    # DC STORY
    # =====================================================

    if story["story_grain"] == "dc":

        diagnostic = story["dc_diagnostic"]

        chain = story["chain"]
        sku = story["sku"]
        dc = story["dc"]

        velocity_pct = diagnostic.get("velocity_pct_change")
        order_pct = diagnostic.get("order_velocity_pct_change")
        fill_pct = diagnostic.get("fill_rate_pct_change")

        driver = story["primary_driver"]
        period = diagnostic.get("diagnostic_period")

        velocity_text = format_pct(velocity_pct)
        order_text = format_pct(order_pct)
        fill_text = format_pct(fill_pct)
        timeframe = period_text(period)

        # -----------------------------
        # Headline
        # -----------------------------

        if driver == "ordering_and_fulfillment":
            headline = (
                f"{dc} is showing both ordering and fulfillment pressure "
                f"for {sku}"
            )
        else:
            headline = (
                f"{dc} stands out as a fulfillment issue for {sku}"
            )

        # -----------------------------
        # Summary
        # -----------------------------

        summary = (
            f"{sku} velocity at {chain} through {dc} declined "
            f"{velocity_text} {timeframe}."
        )

        if driver == "ordering_and_fulfillment":
            summary += (
                f" Order velocity declined {order_text} while fill rate "
                f"declined {fill_text}, suggesting both weaker ordering "
                f"and fulfillment contributed."
            )

        elif driver == "fulfillment":
            summary += (
                f" Fill rate declined {fill_text}, while ordering did not "
                f"show the same deterioration, pointing to fulfillment "
                f"as the stronger signal."
            )

        # -----------------------------
        # Detail
        # -----------------------------

        detail = (
            f"The broader {chain} × {sku} trend does not show the same "
            f"fulfillment signal, making {dc} a localized issue."
        )

        # -----------------------------
        # Current inventory context
        # -----------------------------

        inventory_status = diagnostic.get("inventory_status")
        weeks_on_hand = diagnostic.get("estimated_weeks_on_hand")
        weeks_text = format_weeks(weeks_on_hand)

        action_context = None

        if inventory_status == "action":
            action_context = (
                f"{dc} currently requires inventory action"
                + (
                    f", with approximately {weeks_text} weeks on hand."
                    if weeks_text
                    else "."
                )
            )

        elif inventory_status == "monitor":
            action_context = (
                f"{dc} is currently being monitored for inventory risk"
                + (
                    f", with approximately {weeks_text} weeks on hand."
                    if weeks_text
                    else "."
                )
            )

        elif inventory_status == "healthy":
            action_context = (
                f"{dc} currently has healthy inventory"
                + (
                    f" at approximately {weeks_text} weeks on hand, "
                    f"suggesting the historical fulfillment issue is not "
                    f"a current inventory shortage."
                    if weeks_text
                    else "."
                )
            )

        return {
            "headline": headline,
            "summary": summary,
            "detail": detail,
            "action_context": action_context,
        }

    raise ValueError(
        f"Unknown story_grain: {story.get('story_grain')}"
    )



def main():
    org_id = "default_org"
    org_dir = Path("backend/data") / org_id

    # =====================================================
    # LOAD DATA
    # =====================================================

    features_df = load_org_tables(org_id)
    active_pods_df = load_active_pods(org_id)
    fill_rate_df = load_fill_rate_df(org_id)

    inventory_assessments = _load_cached_inventory_assessments(
        org_dir=org_dir,
        org_id=org_id,
    )

    # =====================================================
    # BUILD STRUCTURED INSIGHTS
    # =====================================================

    result = build_fill_rate_insights(
        features_df=features_df,
        active_pods_df=active_pods_df,
        fill_rate_df=fill_rate_df,
        inventory_assessments=inventory_assessments,
        period="L3M",
        comparison="PP",
        end_month="2026-07",
    )

    # =====================================================
    # NARRATE SELECTED STORIES
    # =====================================================

    stories = result["stories"]

    print("\n")
    print("=" * 80)
    print("FILL-RATE INSIGHTS")
    print("=" * 80)

    print(f"\n{len(stories)} stories selected.")

    if not stories:
        print("\nNo fill-rate stories found.")
        return

    for i, story in enumerate(stories, start=1):

        narrative = narrate_fill_rate_story(story)

        print("\n")
        print("=" * 80)
        print(f"STORY {i}")
        print("=" * 80)

        print(f"\n{narrative['headline']}")

        print("\nSUMMARY")
        print(narrative["summary"])

        if narrative.get("detail"):
            print("\nDETAIL")
            print(narrative["detail"])

        if narrative.get("action_context"):
            print("\nCURRENT INVENTORY")
            print(narrative["action_context"])

        # -------------------------------------------------
        # STRUCTURED CONTEXT
        # -------------------------------------------------

        print("\n--- Structured context ---")

        print(f"Grain: {story['story_grain']}")
        print(f"Chain: {story['chain']}")
        print(f"SKU: {story['sku']}")
        print(f"Driver: {story['primary_driver']}")

        if story["story_grain"] == "chain":

            diagnostic = story["chain_diagnostic"]

            print(
                f"Diagnostic period: "
                f"{diagnostic.get('diagnostic_period')}"
            )

            print(
                f"Supporting DCs: "
                f"{story['supporting_dc_count']}"
            )

            if story["supporting_dcs"]:
                print(
                    "DCs: "
                    + ", ".join(
                        str(dc.get("dc"))
                        for dc in story["supporting_dcs"]
                        if pd.notna(dc.get("dc"))
                    )
                )

        else:

            diagnostic = story["dc_diagnostic"]

            print(f"Distributor: {story['distributor']}")
            print(f"DC: {story['dc']}")

            print(
                f"Diagnostic period: "
                f"{diagnostic.get('diagnostic_period')}"
            )

    print("\n")
    print("=" * 80)
    print("END")
    print("=" * 80)

if __name__ == "__main__":
    main()
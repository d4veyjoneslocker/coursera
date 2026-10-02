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

def build_localized_dc_story(chain_row, supporting_dcs):
    return {
        "story_grain": "localized_dc",
        "chain": chain_row["chain"],
        "sku": chain_row["sku"],
        "primary_driver": "localized_fulfillment",
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
            valid_fill_rate_dcs = fill_rate_dcs[
                fill_rate_dcs["dc"].notna()
            ]

            if not valid_fill_rate_dcs.empty:
                stories.append(
                    build_localized_dc_story(
                        chain_row=chain_row,
                        supporting_dcs=valid_fill_rate_dcs,
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
    Turn a selected fill-rate story into concise user-facing narrative.

    This function does NOT make analytical decisions.
    Eligibility, driver classification, story grain, and materiality
    should already be determined upstream.
    """

    def format_pct(value):
        if pd.isna(value):
            return None
        return f"{abs(value) * 100:.0f}%"

    def format_weeks(value):
        if pd.isna(value):
            return None
        return f"{value:.1f}"

    def format_dc_list(dc_names):
        if not dc_names:
            return ""
        if len(dc_names) == 1:
            return dc_names[0]
        if len(dc_names) == 2:
            return f"{dc_names[0]} and {dc_names[1]}"
        return f"{', '.join(dc_names[:-1])}, and {dc_names[-1]}"

    def period_text(period):
        if period == "L3M":
            return "over the last 3 months"
        if period == "L2M":
            return "over the last 2 months"
        return "over the comparison period"

    # =====================================================
    # CHAIN STORY
    # =====================================================

    if story["story_grain"] == "chain":

        diagnostic = story["chain_diagnostic"]
        supporting_dcs = story.get("supporting_dcs", [])

        chain = story["chain"]
        sku = story["sku"]
        driver = story["primary_driver"]

        velocity_text = format_pct(
            diagnostic.get("velocity_pct_change")
        )
        order_text = format_pct(
            diagnostic.get("order_velocity_pct_change")
        )
        fill_text = format_pct(
            diagnostic.get("fill_rate_pct_change")
        )
        timeframe = period_text(
            diagnostic.get("diagnostic_period")
        )

        dc_names = [
            str(row.get("dc"))
            for row in supporting_dcs
            if pd.notna(row.get("dc"))
        ]
        dc_list = format_dc_list(dc_names)

        # -----------------------------
        # Headline
        # -----------------------------

        headline = (
            f"{sku} velocity at {chain} is down {velocity_text}"
        )

        # -----------------------------
        # Summary
        # -----------------------------

        if driver == "ordering_and_fulfillment":
            summary = (
                f"Ordering and fulfillment both weakened {timeframe}: "
                f"order velocity fell {order_text} and fill rate fell "
                f"{fill_text}."
            )

        elif driver == "fulfillment":
            summary = (
                f"Fulfillment stands out as the main pressure point "
                f"{timeframe}, with fill rate down {fill_text}."
            )

        else:
            summary = (
                f"Sales velocity declined {velocity_text} {timeframe}."
            )

        # -----------------------------
        # Supporting DC evidence
        # -----------------------------

        detail = None

        if len(supporting_dcs) == 1:
            row = supporting_dcs[0]

            dc = row.get("dc")
            dc_velocity_text = format_pct(
                row.get("diagnostic_velocity_pct_change")
            )
            dc_fill_text = format_pct(
                row.get("diagnostic_fill_rate_pct_change")
            )

            detail = (
                f"The fulfillment issue is concentrated at {dc}, "
                f"where fill rate fell {dc_fill_text} alongside a "
                f"{dc_velocity_text} decline in sales velocity."
            )

        elif len(supporting_dcs) > 1:
            dc_details = []

            for row in supporting_dcs:
                dc = row.get("dc")
                dc_fill_text = format_pct(
                    row.get("diagnostic_fill_rate_pct_change")
                )
                dc_velocity_text = format_pct(
                    row.get("diagnostic_velocity_pct_change")
                )

                dc_details.append(
                    f"{dc} (fill rate -{dc_fill_text}, "
                    f"sales velocity -{dc_velocity_text})"
                )

            detail = (
                f"The fulfillment pressure is concentrated in "
                f"{dc_list}: "
                + "; ".join(dc_details)
                + "."
            )

        # -----------------------------
        # Current inventory
        # -----------------------------

        inventory_details = []

        for row in supporting_dcs:
            dc = row.get("dc")
            inventory_status = row.get("inventory_status")
            weeks_text = format_weeks(
                row.get("estimated_weeks_on_hand")
            )

            if inventory_status == "action":
                text = f"{dc} needs inventory attention now"
            elif inventory_status == "monitor":
                text = f"{dc} should be monitored"
            elif inventory_status == "healthy":
                text = f"{dc} inventory is currently healthy"
            else:
                continue

            if weeks_text:
                text += f" at {weeks_text} weeks on hand"

            inventory_details.append(text)

        action_context = None

        if inventory_details:
            action_context = ". ".join(inventory_details) + "."

        return {
            "headline": headline,
            "summary": summary,
            "detail": detail,
            "action_context": action_context,
        }

    # =====================================================
    # LOCALIZED DC STORY
    # =====================================================

    if story["story_grain"] == "localized_dc":

        chain = story["chain"]
        sku = story["sku"]
        supporting_dcs = story["supporting_dcs"]

        dc_names = [
            str(row.get("dc"))
            for row in supporting_dcs
            if pd.notna(row.get("dc"))
        ]
        dc_list = format_dc_list(dc_names)

        # -----------------------------
        # Headline
        # -----------------------------

        if len(dc_names) == 1:
            headline = (
                f"{sku} has a localized fulfillment issue at "
                f"{dc_list}"
            )
        else:
            headline = (
                f"{sku} has localized fulfillment issues at "
                f"{dc_list}"
            )

        # -----------------------------
        # Summary
        # -----------------------------

        summary = (
            f"The issue is not broad across {chain}; fulfillment "
            f"pressure is concentrated at {dc_list}."
        )

        # -----------------------------
        # Supporting DC evidence
        # -----------------------------

        dc_details = []

        for row in supporting_dcs:
            dc = row.get("dc")

            velocity_text = format_pct(
                row.get("diagnostic_velocity_pct_change")
            )
            order_text = format_pct(
                row.get("diagnostic_order_velocity_pct_change")
            )
            fill_text = format_pct(
                row.get("diagnostic_fill_rate_pct_change")
            )
            timeframe = period_text(
                row.get("diagnostic_period")
            )

            dc_details.append(
                f"{dc}: sales velocity fell {velocity_text} "
                f"{timeframe}, with ordering down {order_text} "
                f"and fill rate down {fill_text}"
            )

        detail = ". ".join(dc_details) + "."

        # -----------------------------
        # Current inventory
        # -----------------------------

        inventory_details = []

        for row in supporting_dcs:
            dc = row.get("dc")
            inventory_status = row.get("inventory_status")
            weeks_text = format_weeks(
                row.get("estimated_weeks_on_hand")
            )

            if inventory_status == "action":
                text = f"{dc} needs inventory attention now"
            elif inventory_status == "monitor":
                text = f"{dc} should be monitored"
            elif inventory_status == "healthy":
                text = f"{dc} inventory is currently healthy"
            else:
                continue

            if weeks_text:
                text += f" at {weeks_text} weeks on hand"

            inventory_details.append(text)

        action_context = None

        if inventory_details:
            action_context = ". ".join(inventory_details) + "."

        return {
            "headline": headline,
            "summary": summary,
            "detail": detail,
            "action_context": action_context,
        }

    # =====================================================
    # LEGACY SINGLE-DC STORY
    # =====================================================

    if story["story_grain"] == "dc":

        diagnostic = story["dc_diagnostic"]

        chain = story["chain"]
        sku = story["sku"]
        dc = story["dc"]
        driver = story["primary_driver"]

        velocity_text = format_pct(
            diagnostic.get("velocity_pct_change")
        )
        order_text = format_pct(
            diagnostic.get("order_velocity_pct_change")
        )
        fill_text = format_pct(
            diagnostic.get("fill_rate_pct_change")
        )
        timeframe = period_text(
            diagnostic.get("diagnostic_period")
        )

        headline = (
            f"{sku} has a localized fulfillment issue at {dc}"
        )

        if driver == "ordering_and_fulfillment":
            summary = (
                f"Sales velocity through {dc} fell {velocity_text} "
                f"{timeframe}, with ordering down {order_text} and "
                f"fill rate down {fill_text}."
            )
        else:
            summary = (
                f"Sales velocity through {dc} fell {velocity_text} "
                f"{timeframe}, while fill rate declined {fill_text}."
            )

        detail = (
            f"The broader {chain} trend does not show the same "
            f"fulfillment pressure, making {dc} the localized issue."
        )

        inventory_status = diagnostic.get("inventory_status")
        weeks_text = format_weeks(
            diagnostic.get("estimated_weeks_on_hand")
        )

        action_context = None

        if inventory_status == "action":
            action_context = f"{dc} needs inventory attention now"
        elif inventory_status == "monitor":
            action_context = f"{dc} should be monitored"
        elif inventory_status == "healthy":
            action_context = f"{dc} inventory is currently healthy"

        if action_context and weeks_text:
            action_context += f" at {weeks_text} weeks on hand."

        elif action_context:
            action_context += "."

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

        if story["story_grain"] in {"chain", "localized_dc"}:

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
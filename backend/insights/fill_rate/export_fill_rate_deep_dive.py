from pathlib import Path

import pandas as pd

from backend.data_pipeline.table_loader import (
    load_org_tables,
    load_active_pods,
    load_fill_rate_df,
)

from backend.serving.routes.inventory.inventory import (
    _load_cached_inventory_assessments,
)

from backend.insights.fill_rate.build_fill_rate_insights import (
    build_fill_rate_insights,
    narrate_fill_rate_story,
)


# =========================================================
# CONFIG
# =========================================================

ORG_ID = "67a96381-5014-4a9b-bfe8-a14e6da5affe"
END_MONTH = "2026-09"

OUTPUT_PATH = (
    Path("backend/insights/fill_rate")
    / "fill_rate_deep_dive_export.xlsx"
)

FILL_RATE_DRIVERS = {
    "fulfillment",
    "ordering_and_fulfillment",
}


# =========================================================
# HELPERS
# =========================================================

def reorder_columns(df, preferred_columns):
    """
    Put useful audit columns first without dropping any columns.
    """

    if df.empty:
        return df

    first = [
        col
        for col in preferred_columns
        if col in df.columns
    ]

    remaining = [
        col
        for col in df.columns
        if col not in first
    ]

    return df[first + remaining]


def stories_to_dataframe(stories):
    """
    Flatten selected stories and their rendered narratives into
    a simple audit table.
    """

    rows = []

    for i, story in enumerate(stories, start=1):

        narrative = narrate_fill_rate_story(story)

        row = {
            "story_number": i,
            "story_grain": story.get("story_grain"),
            "chain": story.get("chain"),
            "sku": story.get("sku"),
            "distributor": story.get("distributor"),
            "dc": story.get("dc"),
            "primary_driver": story.get("primary_driver"),

            "headline": narrative.get("headline"),
            "summary": narrative.get("summary"),
            "detail": narrative.get("detail"),
            "action_context": narrative.get("action_context"),
        }

        # -------------------------------------------------
        # Chain diagnostic context
        # -------------------------------------------------

        chain_diagnostic = story.get("chain_diagnostic")

        if chain_diagnostic:
            row.update({
                "chain_diagnostic_period":
                    chain_diagnostic.get("diagnostic_period"),

                "chain_velocity_pct_change":
                    chain_diagnostic.get(
                        "diagnostic_velocity_pct_change",
                        chain_diagnostic.get("velocity_pct_change"),
                    ),

                "chain_order_velocity_pct_change":
                    chain_diagnostic.get(
                        "diagnostic_order_velocity_pct_change",
                        chain_diagnostic.get(
                            "order_velocity_pct_change"
                        ),
                    ),

                "chain_fill_rate_pct_change":
                    chain_diagnostic.get(
                        "diagnostic_fill_rate_pct_change",
                        chain_diagnostic.get(
                            "fill_rate_pct_change"
                        ),
                    ),
            })

        # -------------------------------------------------
        # Supporting DC context
        # -------------------------------------------------

        supporting_dcs = story.get("supporting_dcs", [])

        row["supporting_dc_count"] = len(supporting_dcs)

        row["supporting_dcs"] = ", ".join(
            str(dc.get("dc"))
            for dc in supporting_dcs
            if pd.notna(dc.get("dc"))
        )

        rows.append(row)

    return pd.DataFrame(rows)


def build_candidate_tables(chain_sku, dc_sku):
    """
    Return every diagnostic currently classified as having
    meaningful fulfillment involvement.

    This lets us compare:
        all candidates
            vs
        selected/consolidated stories
    """

    chain_candidates = chain_sku[
        chain_sku["primary_driver"].isin(FILL_RATE_DRIVERS)
    ].copy()

    dc_candidates = dc_sku[
        dc_sku["primary_driver"].isin(FILL_RATE_DRIVERS)
    ].copy()

    return chain_candidates, dc_candidates


# =========================================================
# MAIN
# =========================================================

def main():

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 300)

    org_id = ORG_ID
    org_dir = Path("backend/data") / org_id

    # =====================================================
    # LOAD EXACT SAME INPUTS AS CURRENT INSIGHT PIPELINE
    # =====================================================

    print("\nLoading data...")

    features_df = load_org_tables(org_id)
    active_pods_df = load_active_pods(org_id)
    fill_rate_df = load_fill_rate_df(org_id)

    inventory_assessments = _load_cached_inventory_assessments(
        org_dir=org_dir,
        org_id=org_id,
    )

    print(f"Features rows: {len(features_df):,}")
    print(f"Active POD rows: {len(active_pods_df):,}")
    print(f"Fill-rate rows: {len(fill_rate_df):,}")
    print(f"Inventory assessment rows: {len(inventory_assessments):,}")

    # =====================================================
    # RUN FULL FILL-RATE PIPELINE
    # =====================================================

    print("\nBuilding fill-rate insights...")

    result = build_fill_rate_insights(
        features_df=features_df,
        active_pods_df=active_pods_df,
        fill_rate_df=fill_rate_df,
        inventory_assessments=inventory_assessments,
        period="L3M",
        comparison="PP",
        end_month=END_MONTH,
    )

    stories = result["stories"]

    chain_sku = result["chain_sku"].copy()
    dc_sku = result["dc_sku"].copy()

    chain_monthly = result["chain_sku_monthly"].copy()
    dc_monthly = result["dc_sku_monthly"].copy()

    # =====================================================
    # DEBUG: FRESH THYME MONTHLY ORDER VELOCITY
    # =====================================================

    print("\n" + "=" * 80)
    print("DEBUG: FRESH THYME ORDER VELOCITY")
    print("=" * 80)

    # -----------------------------------------------------
    # 1. Raw Fresh Thyme fill-rate/order data
    # -----------------------------------------------------

    fresh_thyme_fill = fill_rate_df[
        fill_rate_df["chain"]
        .astype(str)
        .str.contains(
            "FRESH THYME",
            case=False,
            na=False,
        )
    ].copy()

    print("\n1) RAW FILL-RATE INPUT")

    print(
        fresh_thyme_fill
        .groupby(
            ["month_year", "sku"],
            dropna=False,
        )
        .agg(
            ordered_units=("ordered_units", "sum"),
            ordered_cases=("ordered_cases", "sum"),
            shipped_cases=("shipped_cases", "sum"),
        )
        .reset_index()
        .sort_values(
            ["month_year", "sku"]
        )
        .tail(24)
        .to_string(index=False)
    )


    # -----------------------------------------------------
    # 2. Fresh Thyme active / covered PODs
    # -----------------------------------------------------

    fresh_thyme_pods = active_pods_df[
        active_pods_df["chain"]
        .astype(str)
        .str.contains(
            "FRESH THYME",
            case=False,
            na=False,
        )
    ].copy()

    print("\n2) ACTIVE / COVERED PODS")

    print(
        fresh_thyme_pods
        .groupby(
            ["month_year", "sku"],
            dropna=False,
        )
        .agg(
            pods=("pod_helper", "nunique"),
            covered=("has_fill_rate_data", "sum"),
        )
        .reset_index()
        .sort_values(
            ["month_year", "sku"]
        )
        .tail(24)
        .to_string(index=False)
    )


    # -----------------------------------------------------
    # 3. Actual chain_monthly returned by pipeline
    # -----------------------------------------------------

    fresh_thyme_monthly = chain_monthly[
        chain_monthly["chain"]
        .astype(str)
        .str.contains(
            "FRESH THYME",
            case=False,
            na=False,
        )
    ].copy()

    print("\n3) CHAIN MONTHLY OUTPUT FROM PIPELINE")

    debug_cols = [
        col
        for col in [
            "month_year",
            "chain",
            "sku",
            "velocity",
            "order_velocity",
            "fill_rate",
        ]
        if col in fresh_thyme_monthly.columns
    ]

    print(
        fresh_thyme_monthly[
            debug_cols
        ]
        .sort_values(
            ["month_year", "sku"]
        )
        .tail(24)
        .to_string(index=False)
    )


    # -----------------------------------------------------
    # 4. September specifically
    # -----------------------------------------------------

    print("\n4) FRESH THYME SEPTEMBER OUTPUT ONLY")

    september_rows = fresh_thyme_monthly[
        fresh_thyme_monthly["month_year"].astype(str)
        == "2026-09"
    ].copy()

    if september_rows.empty:
        print(
            "❌ NO SEPTEMBER ROWS IN chain_sku_monthly"
        )

    else:
        print(
            september_rows[
                debug_cols
            ]
            .sort_values("sku")
            .to_string(index=False)
        )


    print("=" * 80 + "\n")

    # =====================================================
    # SELECTED STORIES
    # =====================================================

    story_df = stories_to_dataframe(stories)

    # =====================================================
    # ALL FILL-RATE CANDIDATES
    # =====================================================

    chain_candidates, dc_candidates = build_candidate_tables(
        chain_sku=chain_sku,
        dc_sku=dc_sku,
    )

    # =====================================================
    # ORGANIZE DIAGNOSTIC TABLES
    # =====================================================

    chain_sku = reorder_columns(
        chain_sku,
        [
            "chain",
            "sku",

            "diagnostic_period",
            "diagnostic_comparison",
            "primary_driver",

            "diagnostic_velocity_pct_change",
            "diagnostic_order_velocity_pct_change",
            "diagnostic_fill_rate_pct_change",

            "ordering_relationship",
            "ordering_relative_magnitude",
            "ordering_meaningful",

            "fulfillment_relationship",
            "fulfillment_relative_magnitude",
            "fulfillment_meaningful",

            "velocity_current",
            "velocity_comparison",
            "velocity_abs_change",
            "velocity_pct_change",

            "order_velocity_current",
            "order_velocity_comparison",
            "order_velocity_abs_change",
            "order_velocity_pct_change",

            "fill_rate_current",
            "fill_rate_comparison",
            "fill_rate_abs_change",
            "fill_rate_pct_change",

            "velocity_comparison_eligible",
            "order_velocity_comparison_eligible",
            "fill_rate_comparison_eligible",

            "coverage_current",
            "coverage_comparison",

            "covered_pod_months_current",
            "covered_pod_months_comparison",

            "pod_months_current",
            "pod_months_comparison",
        ],
    )

    dc_sku = reorder_columns(
        dc_sku,
        [
            "chain",
            "distributor",
            "dc",
            "sku",

            "diagnostic_period",
            "diagnostic_comparison",
            "primary_driver",

            "diagnostic_velocity_pct_change",
            "diagnostic_order_velocity_pct_change",
            "diagnostic_fill_rate_pct_change",

            "ordering_relationship",
            "ordering_relative_magnitude",
            "ordering_meaningful",

            "fulfillment_relationship",
            "fulfillment_relative_magnitude",
            "fulfillment_meaningful",

            "velocity_current",
            "velocity_comparison",
            "velocity_abs_change",
            "velocity_pct_change",

            "order_velocity_current",
            "order_velocity_comparison",
            "order_velocity_abs_change",
            "order_velocity_pct_change",

            "fill_rate_current",
            "fill_rate_comparison",
            "fill_rate_abs_change",
            "fill_rate_pct_change",

            "velocity_comparison_eligible",
            "order_velocity_comparison_eligible",
            "fill_rate_comparison_eligible",

            "coverage_current",
            "coverage_comparison",

            "inventory_assessment_available",
            "inventory_status",
            "estimated_weeks_on_hand",
        ],
    )

    chain_candidates = reorder_columns(
        chain_candidates,
        [
            "chain",
            "sku",

            "diagnostic_period",
            "primary_driver",

            "diagnostic_velocity_pct_change",
            "diagnostic_order_velocity_pct_change",
            "diagnostic_fill_rate_pct_change",

            "ordering_relative_magnitude",
            "fulfillment_relative_magnitude",
        ],
    )

    dc_candidates = reorder_columns(
        dc_candidates,
        [
            "chain",
            "distributor",
            "dc",
            "sku",

            "diagnostic_period",
            "primary_driver",

            "diagnostic_velocity_pct_change",
            "diagnostic_order_velocity_pct_change",
            "diagnostic_fill_rate_pct_change",

            "ordering_relative_magnitude",
            "fulfillment_relative_magnitude",

            "inventory_status",
            "estimated_weeks_on_hand",
        ],
    )

    chain_monthly = reorder_columns(
        chain_monthly,
        [
            "month_year",
            "chain",
            "sku",
        ],
    )

    dc_monthly = reorder_columns(
        dc_monthly,
        [
            "month_year",
            "chain",
            "distributor",
            "dc",
            "sku",
        ],
    )

    # =====================================================
    # SUMMARY / README
    # =====================================================

    summary_df = pd.DataFrame(
        [
            {
                "field": "org_id",
                "value": ORG_ID,
            },
            {
                "field": "end_month",
                "value": END_MONTH,
            },
            {
                "field": "selected_story_count",
                "value": len(stories),
            },
            {
                "field": "chain_fill_rate_candidates",
                "value": len(chain_candidates),
            },
            {
                "field": "dc_fill_rate_candidates",
                "value": len(dc_candidates),
            },
            {
                "field": "all_chain_diagnostic_rows",
                "value": len(chain_sku),
            },
            {
                "field": "all_dc_diagnostic_rows",
                "value": len(dc_sku),
            },
            {
                "field": "chain_monthly_rows",
                "value": len(chain_monthly),
            },
            {
                "field": "dc_monthly_rows",
                "value": len(dc_monthly),
            },
            {
                "field": "fill_rate_input_rows",
                "value": len(fill_rate_df),
            },
        ]
    )

    # =====================================================
    # WRITE EXCEL WORKBOOK
    # =====================================================

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with pd.ExcelWriter(
        OUTPUT_PATH,
        engine="openpyxl",
    ) as writer:

        summary_df.to_excel(
            writer,
            sheet_name="README",
            index=False,
        )

        story_df.to_excel(
            writer,
            sheet_name="Selected Stories",
            index=False,
        )

        chain_candidates.to_excel(
            writer,
            sheet_name="Chain Candidates",
            index=False,
        )

        dc_candidates.to_excel(
            writer,
            sheet_name="DC Candidates",
            index=False,
        )

        chain_sku.to_excel(
            writer,
            sheet_name="All Chain Diagnostics",
            index=False,
        )

        dc_sku.to_excel(
            writer,
            sheet_name="All DC Diagnostics",
            index=False,
        )

        chain_monthly.to_excel(
            writer,
            sheet_name="Chain Monthly",
            index=False,
        )

        dc_monthly.to_excel(
            writer,
            sheet_name="DC Monthly",
            index=False,
        )

        # Raw transformed fill-rate input as an extra sanity check.
        fill_rate_df.to_excel(
            writer,
            sheet_name="Fill Rate Input",
            index=False,
        )

    # =====================================================
    # TERMINAL SUMMARY
    # =====================================================

    print("\n")
    print("=" * 80)
    print("FILL-RATE DEEP DIVE EXPORT COMPLETE")
    print("=" * 80)

    print(f"\nOutput:")
    print(OUTPUT_PATH)

    print("\nAUDIT COUNTS")
    print(f"Selected stories:       {len(stories)}")
    print(f"Chain candidates:       {len(chain_candidates)}")
    print(f"DC candidates:          {len(dc_candidates)}")
    print(f"All chain diagnostics:  {len(chain_sku)}")
    print(f"All DC diagnostics:     {len(dc_sku)}")
    print(f"Fill-rate input rows:   {len(fill_rate_df)}")

    print("\nSELECTED STORIES")

    if story_df.empty:
        print("None")
    else:
        for _, row in story_df.iterrows():
            print(
                f"{int(row['story_number'])}. "
                f"{row['headline']}"
            )

    print("\nDone.\n")


if __name__ == "__main__":
    main()
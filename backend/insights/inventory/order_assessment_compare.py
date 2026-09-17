from pathlib import Path
import traceback

import numpy as np
import pandas as pd

import sys
from contextlib import redirect_stdout

class Tee:
    """
    Write stdout to both the terminal and a text file.
    """

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            stream.flush()

    def flush(self):
        for stream in self.streams:
            stream.flush()

from backend.metrics.inventory.expected_orders import (
    build_kehe_expected_order_events,
    build_unfi_expected_order_events,
)
from backend.insights.inventory.order_assessment_3 import (
    assess_inventory, get_inventory_relevance
)
from backend.insights.inventory.order_assessment import (
    run_inventory_risk,
)
from backend.metrics.inventory.replenishment_metrics import (
    calculate_replenishment_lead_time,
    resolve_replenishment_lead_time,
)
from backend.transforms.inventory.kehe import (
    transform_kehe_order_projections,
)
from backend.transforms.inventory.unfi import (
    transform_unfi_projected_orders,
    transform_unfi_purchase_orders,
)


# =============================================================================
# HELPERS
# =============================================================================

def _latest_inventory_rows(
    inventory: pd.DataFrame,
) -> pd.DataFrame:
    """
    Return the latest inventory observation for every distributor × DC × SKU.
    """

    df = inventory.copy()

    df["report_date"] = pd.to_datetime(
        df["report_date"],
        errors="coerce",
    )

    return (
        df.sort_values("report_date")
        .groupby(
            ["distributor", "dc", "sku"],
            as_index=False,
        )
        .tail(1)
        .reset_index(drop=True)
    )


def _build_lead_time_lookup(
    inventory: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build the same observed DC lead-time lookup used by the Strawberry test.
    """

    lead_times = calculate_replenishment_lead_time(
        inventory
    ).copy()

    lead_times["median_replenishment_days"] = pd.to_numeric(
        lead_times["median_replenishment_days"],
        errors="coerce",
    )

    return lead_times



def _summarize_new_engine(
    assessment: dict,
) -> dict:
    """
    Flatten the breach-level inventory outlook enough for comparison
    against the existing order assessment.
    """

    baseline = assessment["baseline"]
    breaches = assessment["breaches"]

    material_breaches = [
        breach
        for breach in breaches
        if breach.get("breaches_tolerance")
    ]

    actions = []

    for breach in material_breaches:
        intervention = breach.get(
            "intervention",
            {},
        )

        actions.append({
            "breach_start": breach.get("start_date"),
            "tolerance_breach_date": breach.get(
                "first_tolerance_breach_date"
            ),
            "lowest_woh": breach.get("lowest_woh"),
            "reaches_oos": breach.get("reaches_oos"),
            "oos_date": breach.get("first_oos_date"),

            "action": intervention.get(
                "intervention_type"
            ),
            "recommended_cases": intervention.get(
                "recommended_cases",
                0,
            ),

            "po_cases": intervention.get("po_cases"),
            "po_receipt_date": intervention.get(
                "current_po_receipt_date"
            ),
            "po_needed_by_date": intervention.get(
                "needed_by_date"
            ),

            "new_order_date": intervention.get(
                "order_date"
            ),
            "new_order_delivery_date": intervention.get(
                "expected_delivery_date"
            ),

            "required_coverage_weeks": intervention.get(
                "required_coverage_weeks"
            ),

            "reason": intervention.get("reason"),
        })

    action_types = [
        action["action"]
        for action in actions
        if action["action"] is not None
    ]

    recommended_cases = sum(
        float(action["recommended_cases"])
        for action in actions
        if pd.notna(action["recommended_cases"])
    )

    return {
        "new_estimated_qoh_today": baseline[
            "estimated_cases_today"
        ],

        "new_velocity_cases_per_week": baseline[
            "velocity_cases_per_week"
        ],

        "new_breach_count": len(breaches),
        "new_material_breach_count": len(
            material_breaches
        ),

        "new_actions": action_types,
        "new_recommended_cases": recommended_cases,

        "new_narrative": assessment["narrative"],

        # Keep the complete breach objects so we can inspect
        # interesting rows after finding differences.
        "new_breaches": breaches,
        "new_action_details": actions,
    }


def _normalize_old_action(
    row: pd.Series,
) -> str:
    """
    Give the old engine a compact action label for comparison.

    This does not reinterpret its business logic; it only summarizes
    the fields it already returned.
    """

    recommended = pd.to_numeric(
        row.get("recommended_order_cases"),
        errors="coerce",
    )

    po_status = row.get("po_status")
    inventory_status = row.get("inventory_status")

    if pd.notna(recommended) and recommended > 0:
        return "new_order"

    if po_status in {
        "follow_up_po",
        "po_overdue",
    }:
        return "follow_up_po"

    if inventory_status in {
        "healthy",
        "monitor",
    }:
        return str(inventory_status)

    return str(inventory_status)


def _actions_differ(
    old_action: str,
    new_actions: list,
) -> bool:
    """
    Flag meaningful active-action differences.

    future_replenishment is an internal planning state, not an active
    user-facing action, so it is ignored for action comparison.
    """

    active_new_actions = [
        action
        for action in new_actions
        if action != "future_replenishment"
    ]

    if len(active_new_actions) > 1:
        return True

    if not active_new_actions:
        return old_action not in {
            "healthy",
            "monitor",
        }

    new_action = active_new_actions[0]

    equivalent_actions = {
        "expedite_po": {
            "follow_up_po",
            "po_overdue",
        },
        "monitor_projected_order": {
            "monitor",
        },
        "none": {
            "healthy",
            "monitor",
        },
        "new_order": {
            "new_order",
        },
    }

    allowed_old = equivalent_actions.get(
        new_action,
        {new_action},
    )

    return old_action not in allowed_old


def _print_inventory_audit(
    example: pd.Series,
    latest_inventory: pd.DataFrame,
    purchase_orders: pd.DataFrame,
    expected_orders: pd.DataFrame,
    as_of_date: pd.Timestamp,
) -> None:
    """
    Print the complete factual audit trail for one DC × SKU disagreement.

    This is diagnostic only. It does not perform or change inventory
    business logic.
    """

    distributor = example["distributor"]
    dc = example["dc"]
    sku = example["sku"]

    print("\n" + "=" * 100)
    print(f"AUDIT — {distributor} / {dc} / {sku}")
    print("=" * 100)

    # ------------------------------------------------------------------
    # INPUTS
    # ------------------------------------------------------------------

    inventory_match = latest_inventory[
        (latest_inventory["distributor"] == distributor)
        & (latest_inventory["dc"] == dc)
        & (latest_inventory["sku"] == sku)
    ]

    print("\nINPUTS")

    if inventory_match.empty:
        print("  Latest inventory row: NOT FOUND")
    else:
        inventory_row = inventory_match.iloc[0]

        print(
            "  Report date:",
            inventory_row.get("report_date"),
        )
        print(
            "  Observed QOH cases:",
            inventory_row.get("quantity_on_hand_cases"),
        )
        print(
            "  Observed WOH:",
            inventory_row.get("weeks_on_hand"),
        )

        print(
            "  Velocity cases/week:",
            example.get("new_velocity_cases_per_week"),
        )

        print(
            "  Planning lead time days:",
            example.get("planning_lead_time_days"),
        )

    # ------------------------------------------------------------------
    # CONFIRMED POs
    # ------------------------------------------------------------------

    print("\nCONFIRMED / OPEN POs")

    po_match = purchase_orders[
        (purchase_orders["distributor"] == distributor)
        & (purchase_orders["dc"] == dc)
        & (purchase_orders["sku"] == sku)
    ].copy()

    if po_match.empty:
        print("  None")
    else:
        print(
            po_match.to_string(index=False)
        )

    # ------------------------------------------------------------------
    # BASELINE
    # ------------------------------------------------------------------

    print("\nBASELINE")

    print(
        "  Estimated QOH today:",
        example.get("new_estimated_qoh_today"),
    )

    material_breaches = [
        breach
        for breach in example["new_breaches"]
        if breach.get("breaches_tolerance")
    ]

    all_breaches = example["new_breaches"]

    floor_dates = [
        breach.get("start_date")
        for breach in all_breaches
        if breach.get("start_date") is not None
    ]

    tolerance_dates = [
        breach.get("first_tolerance_breach_date")
        for breach in material_breaches
        if breach.get("first_tolerance_breach_date") is not None
    ]

    oos_dates = [
        breach.get("first_oos_date")
        for breach in all_breaches
        if breach.get("first_oos_date") is not None
    ]

    lowest_woh_values = [
        breach.get("lowest_woh")
        for breach in all_breaches
        if breach.get("lowest_woh") is not None
    ]

    print(
        "  First floor breach:",
        min(floor_dates) if floor_dates else None,
    )
    print(
        "  First tolerance breach:",
        min(tolerance_dates) if tolerance_dates else None,
    )
    print(
        "  First OOS:",
        min(oos_dates) if oos_dates else None,
    )
    print(
        "  Lowest WOH:",
        min(lowest_woh_values)
        if lowest_woh_values
        else None,
    )

    # ------------------------------------------------------------------
    # PROJECTED ORDERS
    # ------------------------------------------------------------------

    print("\nPROJECTED ORDERS")

    projected_match = expected_orders[
        (expected_orders["distributor"] == distributor)
        & (expected_orders["dc"] == dc)
        & (expected_orders["sku"] == sku)
    ].copy()

    if projected_match.empty:
        print("  None")
    else:
        print(
            projected_match.to_string(index=False)
        )

    # ------------------------------------------------------------------
    # BREACH-BY-BREACH DECISION AUDIT
    # ------------------------------------------------------------------

    print("\nBREACH / INTERVENTION AUDIT")

    if not material_breaches:
        print("  No material breaches.")

    for i, breach in enumerate(
        material_breaches,
        start=1,
    ):
        intervention = breach.get(
            "intervention",
            {},
        )

        projected_order = breach.get(
            "projected_order",
            {},
        )

        print("\n" + "-" * 80)
        print(f"  BREACH {i}")
        print("-" * 80)

        print(
            "  Start date:",
            breach.get("start_date"),
        )
        print(
            "  End date:",
            breach.get("end_date"),
        )
        print(
            "  First tolerance breach:",
            breach.get("first_tolerance_breach_date"),
        )
        print(
            "  Lowest WOH:",
            breach.get("lowest_woh"),
        )
        print(
            "  Lowest WOH date:",
            breach.get("lowest_woh_date"),
        )
        print(
            "  Reaches OOS:",
            breach.get("reaches_oos"),
        )
        print(
            "  First OOS date:",
            breach.get("first_oos_date"),
        )

        print("\n  PROJECTED ORDER EVALUATION")

        orders = projected_order.get(
            "orders",
            [],
        )

        if not orders:
            print("    No projected orders evaluated.")
        else:
            for j, order in enumerate(
                orders,
                start=1,
            ):
                print(f"\n    Projected order {j}")

                for key in [
                    "cases",
                    "order_date",
                    "expected_delivery_date",
                    "arrives_in_time",
                    "resolves_breach",
                    "reason",
                ]:
                    if key in order:
                        print(
                            f"      {key}:",
                            order.get(key),
                        )

        print(
            "    Resolves breach:",
            projected_order.get("resolves_breach"),
        )

        resolving_order = projected_order.get(
            "resolving_order"
        )

        if resolving_order is not None:
            print(
                "    Resolving order:",
                resolving_order,
            )

        print("\n  INTERVENTION")

        audit_fields = [
            "intervention_required",
            "intervention_type",
            "reason",
            "needed_by_date",
            "order_by_date",
            "surface_date",
            "order_date",
            "expected_delivery_date",
            "recommended_cases",
            "po_cases",
            "current_po_receipt_date",
            "required_coverage_weeks",
            "projected_cases_at_delivery",
            "projected_weeks_at_delivery",
            "target_cases_at_delivery",
        ]

        for key in audit_fields:
            if key in intervention:
                print(
                    f"    {key}:",
                    intervention.get(key),
                )

    # ------------------------------------------------------------------
    # FINAL USER-FACING RESULT
    # ------------------------------------------------------------------

    print("\nFINAL NEW-ENGINE RESULT")

    print(
        "  Actions:",
        example.get("new_actions"),
    )
    print(
        "  Recommended cases:",
        example.get("new_recommended_cases"),
    )
    print(
        "  Narrative:",
        example.get("new_narrative"),
    )


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    output_path = Path(
        "backend/data/default_org/inventory_engine_audit.txt"
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as audit_file:
        tee = Tee(
            sys.stdout,
            audit_file,
        )

        with redirect_stdout(tee):
            org_id = "default_org"
                
        org_dir = Path("backend/data") / org_id

        # Match the existing order-assessment test exactly.
        as_of_date = pd.Timestamp("2026-09-15")

        # ------------------------------------------------------------------
        # Load inputs
        # ------------------------------------------------------------------

        inventory = pd.read_csv(
            org_dir / "inventory_features_test.csv"
        )

        unfi_projected_orders = transform_unfi_projected_orders(
            pd.read_csv(
                org_dir
                / "raw/inventory/unfi/Projected Orders Detail.csv"
            ),
            org_id=org_id,
        )

        kehe_projected_orders = transform_kehe_order_projections(
            pd.read_csv(
                org_dir
                / "raw/inventory/kehe/Order Projections Report.csv"
            ),
            org_id=org_id,
        )

        purchase_orders = transform_unfi_purchase_orders(
            pd.read_csv(
                org_dir
                / "raw/inventory/unfi/Purchase Orders.csv"
            ),
            org_id=org_id,
        )

        expected_orders = pd.concat(
            [
                build_unfi_expected_order_events(
                    unfi_projected_orders
                ),
                build_kehe_expected_order_events(
                    kehe_projected_orders
                ),
            ],
            ignore_index=True,
        )

        # ------------------------------------------------------------------
        # OLD ENGINE
        # ------------------------------------------------------------------

        old_result = run_inventory_risk(
            df=inventory.copy(),
            inventory_history=inventory,
            expected_orders=expected_orders,
            purchase_orders=purchase_orders,
            as_of_date=as_of_date,
        ).copy()

        old_result["old_action"] = old_result.apply(
            _normalize_old_action,
            axis=1,
        )

        # ------------------------------------------------------------------
        # NEW ENGINE
        # ------------------------------------------------------------------

        latest_inventory = _latest_inventory_rows(
            inventory
        )

        lead_times = _build_lead_time_lookup(
            inventory
        )

        print("\nLEAD TIMES")
        print(
            lead_times[
                (lead_times["dc"] == "SRQ")
                | (lead_times["dc"] == "__DEFAULT__")
            ].to_string(index=False)
        )

        new_rows = []
        errors = []

        for _, inventory_row in latest_inventory.iterrows():
            row = inventory_row.copy()

            relevance = get_inventory_relevance(
                row=row,
                purchase_orders=purchase_orders,
            )

            if not relevance["is_relevant"]:
                continue

            lead_time = resolve_replenishment_lead_time(
                distributor=row["distributor"],
                dc=row["dc"],
                lead_times=lead_times,
            )

            lead_days = lead_time["lead_time_days"]

            if lead_days is None:
                errors.append({
                    "distributor": row["distributor"],
                    "dc": row["dc"],
                    "sku": row["sku"],
                    "error": "missing_lead_time",
                })
                continue

            row["planning_lead_time_days"] = float(
                lead_days
            )

            row["planning_lead_time_source"] = (
                lead_time["lead_time_source"]
            )

            try:
                assessment = assess_inventory(
                    row=row,
                    purchase_orders=purchase_orders,
                    expected_orders=expected_orders,
                    as_of_date=as_of_date,
                    lookahead_days=42,
                    floor_weeks=3,
                    buffer_weeks=0.5,
                    target_weeks=5,
                )

            except Exception as exc:
                print("\n" + "!" * 100)
                print(
                    "ERROR:",
                    row["distributor"],
                    "/",
                    row["dc"],
                    "/",
                    row["sku"],
                )
                traceback.print_exc()
                print("!" * 100)

                errors.append({
                    "distributor": row["distributor"],
                    "dc": row["dc"],
                    "sku": row["sku"],
                    "error": repr(exc),
                })
                continue

            summary = _summarize_new_engine(
                assessment
            )

            new_rows.append({
                "distributor": row["distributor"],
                "dc": row["dc"],
                "sku": row["sku"],
                **summary,
            })

        new_result = pd.DataFrame(new_rows)

        # ------------------------------------------------------------------
        # JOIN OLD + NEW
        # ------------------------------------------------------------------

        old_columns = [
            "distributor",
            "dc",
            "sku",

            "calculated_weeks_on_hand",
            "planning_lead_time_days",

            "next_inbound_date",
            "next_inbound_cases",
            "next_inbound_type",

            "lowest_woh_before_coverage",

            "recommended_order_cases",
            "inventory_status",
            "po_status",
            "inventory_urgency",

            "days_until_oos",
            "days_of_cushion",

            "classification_reason",
            "old_action",
        ]

        old_compare = old_result[
            old_columns
        ].copy()

        comparison = old_compare.merge(
            new_result,
            on=[
                "distributor",
                "dc",
                "sku",
            ],
            how="inner",
        )

        # ------------------------------------------------------------------
        # Difference flags
        # ------------------------------------------------------------------

        comparison["action_differs"] = comparison.apply(
            lambda r: _actions_differ(
                old_action=r["old_action"],
                new_actions=r["new_actions"],
            ),
            axis=1,
        )

        old_qty = pd.to_numeric(
            comparison["recommended_order_cases"],
            errors="coerce",
        ).fillna(0)

        new_qty = pd.to_numeric(
            comparison["new_recommended_cases"],
            errors="coerce",
        ).fillna(0)

        comparison["quantity_differs"] = (
            old_qty != new_qty
        )

        comparison["multiple_new_breaches"] = (
            comparison["new_material_breach_count"] > 1
        )

        comparison["any_difference"] = (
            comparison["action_differs"]
            | comparison["quantity_differs"]
            | comparison["multiple_new_breaches"]
        )

        differences = comparison[
            comparison["any_difference"]
        ].copy()

        # ------------------------------------------------------------------
        # Summary
        # ------------------------------------------------------------------

        print("\n" + "=" * 100)
        print("OLD VS NEW INVENTORY ENGINE")
        print("=" * 100)

        print(
            "\nDC × SKU combinations compared:",
            len(comparison),
        )

        print(
            "Combinations with differences:",
            len(differences),
        )

        print(
            "Different action:",
            int(comparison["action_differs"].sum()),
        )

        print(
            "Different quantity:",
            int(comparison["quantity_differs"].sum()),
        )

        print(
            "Multiple material breaches:",
            int(
                comparison[
                    "multiple_new_breaches"
                ].sum()
            ),
        )

        # ------------------------------------------------------------------
        # Compact difference table
        # ------------------------------------------------------------------

        print("\n" + "=" * 100)
        print("DIFFERENCES")
        print("=" * 100)

        display_columns = [
            "distributor",
            "dc",
            "sku",

            "calculated_weeks_on_hand",

            "old_action",
            "recommended_order_cases",

            "new_material_breach_count",
            "new_actions",
            "new_recommended_cases",

            "action_differs",
            "quantity_differs",
        ]

        if differences.empty:
            print("\nNo differences found.")

        else:
            print(
                differences[
                    display_columns
                ]
                .sort_values(
                    [
                        "action_differs",
                        "quantity_differs",
                        "distributor",
                        "dc",
                        "sku",
                    ],
                    ascending=[
                        False,
                        False,
                        True,
                        True,
                        True,
                    ],
                )
                .to_string(index=False)
            )

        # ------------------------------------------------------------------
    # COMPLETE DIFFERENCE AUDIT
    #
    # Print every disagreement so each one can be manually validated
    # against the raw inputs and the new engine's decision trail.
    # ------------------------------------------------------------------

    print("\n" + "=" * 100)
    print("COMPLETE DIFFERENCE AUDIT")
    print("=" * 100)

    if differences.empty:
        print("\nNo differences to audit.")

    else:
        for _, example in differences.iterrows():
            _print_inventory_audit(
                example=example,
                latest_inventory=latest_inventory,
                purchase_orders=purchase_orders,
                expected_orders=expected_orders,
                as_of_date=as_of_date,
            )

        # ------------------------------------------------------------------
        # Errors
        # ------------------------------------------------------------------

        if errors:
            print("\n" + "=" * 100)
            print("NEW ENGINE ERRORS / SKIPPED ROWS")
            print("=" * 100)

            print(
                pd.DataFrame(errors).to_string(
                    index=False
                )
            )
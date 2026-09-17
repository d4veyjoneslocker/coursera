import numpy as np
import pandas as pd

from backend.metrics.inventory.recommended_orders import calculate_recommended_order_for_date
from backend.metrics.inventory.replenishment_metrics import calculate_replenishment_lead_time


def get_current_inventory_state(row: pd.Series, floor_weeks: float = 3) -> str:
    if pd.isna(row["dc_weekly_velocity"]) or row["dc_weekly_velocity"] <= 0:
        return "no_active_demand"
    if row["is_out_of_stock"]:
        return "oos"
    if pd.notna(row["calculated_weeks_on_hand"]) and row["calculated_weeks_on_hand"] < floor_weeks:
        return "low"
    return "healthy"


def build_inbound_events(
    row: pd.Series,
    expected_orders: pd.DataFrame,
    purchase_orders: pd.DataFrame,
    as_of_date,
) -> pd.DataFrame:
    distributor, dc, sku = row["distributor"], row["dc"], row["sku"]
    lead_days = row["planning_lead_time_days"]
    events = []

    # ---------------------------------------------------------------
    # Confirmed POs
    # Purchase Orders file is the source of truth for committed supply.
    # For now, preserve the existing receipt-date logic:
    # PO create date + planning lead time.
    # ---------------------------------------------------------------
    po = purchase_orders[
        (purchase_orders["distributor"] == distributor)
        & (purchase_orders["dc"] == dc)
        & (purchase_orders["sku"] == sku)
        & purchase_orders["open_quantity_cases"].gt(0)
    ].copy()

    if not po.empty:
        po["expected_receipt_date"] = (
            pd.to_datetime(po["po_create_date"]).dt.normalize()
            + pd.to_timedelta(lead_days, unit="D")
        )

        # Combine POs expected on the same date.
        po = (
            po.groupby("expected_receipt_date", as_index=False)["open_quantity_cases"]
            .sum()
            .sort_values("expected_receipt_date")
        )

        for _, po_event in po.iterrows():
            expected_receipt_date = pd.Timestamp(
                po_event["expected_receipt_date"]
            ).normalize()

            is_overdue = expected_receipt_date < pd.Timestamp(as_of_date)

            events.append({
                "receipt_date": max(
                    expected_receipt_date,
                    pd.Timestamp(as_of_date),
                ),
                "expected_receipt_date": expected_receipt_date,
                "inbound_cases": float(po_event["open_quantity_cases"]),
                "inbound_type": "committed_po",
                "is_overdue": is_overdue,
                "timing_known": True,
            })

    # ---------------------------------------------------------------
    # Projected orders
    # ---------------------------------------------------------------
    expected = expected_orders[
        (expected_orders["distributor"] == distributor)
        & (expected_orders["dc"] == dc)
        & (expected_orders["sku"] == sku)
    ].copy()

    if not expected.empty:
        expected["receipt_date"] = (
            pd.to_datetime(expected["expected_order_date"])
            + pd.to_timedelta(lead_days, unit="D")
        )

        for _, event in expected[
            expected["receipt_date"] >= as_of_date
        ].iterrows():
            events.append({
                "receipt_date": event["receipt_date"],
                "expected_receipt_date": event["receipt_date"],
                "inbound_cases": event["expected_order_cases"],
                "inbound_type": "projected_order",
                "is_overdue": False,
                "timing_known": True,
            })

    if not events:
        return pd.DataFrame(
            columns=[
                "receipt_date",
                "expected_receipt_date",
                "inbound_cases",
                "inbound_type",
                "is_overdue",
                "timing_known",
            ]
        )

    return (
        pd.DataFrame(events)
        .sort_values(["receipt_date", "inbound_type"])
        .reset_index(drop=True)
    )

def run_inventory_risk(
    df: pd.DataFrame,
    inventory_history: pd.DataFrame,
    expected_orders: pd.DataFrame,
    purchase_orders: pd.DataFrame,
    floor_weeks: float = 3,
    target_weeks: float = 5,
    tolerance_weeks: float = 0.5,
    monitor_weeks: float = 2,
    lead_time_overrides: pd.DataFrame | None = None,
    as_of_date=None,
) -> pd.DataFrame:
    df = df.copy()
    as_of_date = pd.Timestamp.today().normalize() if as_of_date is None else pd.Timestamp(as_of_date).normalize()
    today = pd.Timestamp(as_of_date).normalize() if as_of_date is not None else pd.Timestamp.today().normalize()

    df = df[df["is_relevant_dc_sku"]].copy()
    df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
    df = df.sort_values("report_date").groupby(["distributor", "dc", "sku"], as_index=False).tail(1).reset_index(drop=True)
    df["current_inventory_state"] = df.apply(get_current_inventory_state, axis=1, floor_weeks=floor_weeks)

    # ------------------------------------------------------------------
    # Lead times — preserve the old hierarchy
    # ------------------------------------------------------------------

    lead_times = calculate_replenishment_lead_time(inventory_history)

    if not lead_times.empty:
        lead_times = lead_times.copy()
        lead_times["median_replenishment_days"] = pd.to_numeric(lead_times["median_replenishment_days"], errors="coerce")
        df = df.merge(lead_times[["distributor", "dc", "median_replenishment_days", "average_replenishment_days", "replenishment_event_count"]], on=["distributor", "dc"], how="left")

        distributor_defaults = lead_times.groupby("distributor", as_index=False)["median_replenishment_days"].median().rename(columns={"median_replenishment_days": "distributor_default_lead_time_days"})
        df = df.merge(distributor_defaults, on="distributor", how="left")
        network_default_lead_time_days = lead_times["median_replenishment_days"].dropna().median()
    else:
        df["median_replenishment_days"] = pd.NA
        df["average_replenishment_days"] = pd.NA
        df["replenishment_event_count"] = pd.NA
        df["distributor_default_lead_time_days"] = pd.NA
        network_default_lead_time_days = pd.NA

    df["network_default_lead_time_days"] = network_default_lead_time_days
    df["dc_lead_time_override_days"] = pd.NA
    df["distributor_lead_time_override_days"] = pd.NA

    if lead_time_overrides is not None and not lead_time_overrides.empty:
        overrides = lead_time_overrides.copy()
        overrides["lead_time_override_days"] = pd.to_numeric(overrides["lead_time_override_days"], errors="coerce")

        dc_overrides = overrides[overrides["dc"].notna()][["distributor", "dc", "lead_time_override_days"]].drop_duplicates(["distributor", "dc"]).rename(columns={"lead_time_override_days": "dc_lead_time_override_days"})
        if not dc_overrides.empty:
            df = df.drop(columns=["dc_lead_time_override_days"]).merge(dc_overrides, on=["distributor", "dc"], how="left")

        distributor_overrides = overrides[overrides["dc"].isna()][["distributor", "lead_time_override_days"]].drop_duplicates(["distributor"]).rename(columns={"lead_time_override_days": "distributor_lead_time_override_days"})
        if not distributor_overrides.empty:
            df = df.drop(columns=["distributor_lead_time_override_days"]).merge(distributor_overrides, on="distributor", how="left")

    df["planning_lead_time_days"] = (
        df["dc_lead_time_override_days"]
        .fillna(df["distributor_lead_time_override_days"])
        .fillna(df["median_replenishment_days"])
        .fillna(df["distributor_default_lead_time_days"])
        .fillna(df["network_default_lead_time_days"])
    )

    df["lead_time_source"] = np.select(
        [
            df["dc_lead_time_override_days"].notna(),
            df["distributor_lead_time_override_days"].notna(),
            df["median_replenishment_days"].notna(),
            df["distributor_default_lead_time_days"].notna(),
            df["network_default_lead_time_days"].notna(),
        ],
        ["dc_user_override", "distributor_user_override", "observed_history", "distributor_default", "network_default"],
        default="missing",
    )

    # ------------------------------------------------------------------
    # Inventory assessment
    # ------------------------------------------------------------------

    rows = []

    for _, row in df.iterrows():
        result = row.to_dict()
        velocity_cases = row["dc_weekly_velocity"] / row["units_per_case"] if pd.notna(row["dc_weekly_velocity"]) and pd.notna(row["units_per_case"]) else np.nan
        current_cases = row["quantity_on_hand_cases"]
        current_woh = row["calculated_weeks_on_hand"]
        lead_days = row["planning_lead_time_days"]

        result.update({
            "inventory_status": "healthy",
            "action_type": "no_action",
            "inventory_urgency": "normal",
            "next_inbound_date": pd.NaT,
            "next_inbound_expected_date": pd.NaT,
            "next_inbound_cases": pd.NA,
            "next_inbound_type": None,
            "next_inbound_timing_known": True,
            "next_inbound_overdue": False,
            "days_until_oos": pd.NA,
            "days_of_cushion": pd.NA,
            "lowest_woh_before_coverage": pd.NA,
            "recommended_order_cases": pd.NA,
            "recommended_order_deadline": pd.NaT,
            "classification_reason": None,
            "po_status": None,
        })

        if pd.isna(velocity_cases) or velocity_cases <= 0 or pd.isna(current_cases) or pd.isna(lead_days):
            result["inventory_status"] = "forecast_required"
            result["inventory_urgency"] = "review"
            result["classification_reason"] = "Missing velocity, inventory, or lead-time assumption"
            rows.append(result)
            continue

        # How long until current inventory reaches the 3-WOH floor?
        weeks_until_floor = max(current_woh - floor_weeks, 0)
        days_until_floor = weeks_until_floor * 7
        floor_date = today + pd.to_timedelta(days_until_floor, unit="D")

        # Build inbound state before any inventory-status early exits.
        # Build inbound state before any inventory-status early exits.
        events = build_inbound_events(row, expected_orders, purchase_orders, today)

        debug_grw_strawberry = (
            row["distributor"] == "UNFI"
            and row["dc"] == "GRW"
            and row["sku"] == "STRAWBERRY"
        )

        if debug_grw_strawberry:
            print("\n" + "=" * 80)
            print("GRW STRAWBERRY — INBOUND EVENTS")
            print("=" * 80)
            print("as_of_date:", today)
            print("report_date:", row.get("report_date"))
            print("on_hand_cases:", row.get("quantity_on_hand_cases"))
            print("weeks_on_hand:", row.get("calculated_weeks_on_hand"))
            print("planning_lead_time_days:", row.get("planning_lead_time_days"))

            if events.empty:
                print("\nNO INBOUND EVENTS")
            else:
                print("\n", events.to_string(index=False))
                
        committed_po_events = events[events["inbound_type"] == "committed_po"]

        # Purchase Orders file is the source of truth for current open PO quantity.
        open_po_cases = pd.to_numeric(
            committed_po_events["inbound_cases"],
            errors="coerce",
        ).sum()

        result["quantity_on_po_cases"] = float(open_po_cases)

        result["quantity_on_po_units"] = (
            float(open_po_cases * row["units_per_case"])
            if pd.notna(row["units_per_case"]) and row["units_per_case"] > 0
            else pd.NA
        )

        if not committed_po_events.empty:
            result["po_status"] = "po_outstanding"

        if not committed_po_events.empty:
            result["po_status"] = "po_outstanding"

        if not events.empty:
            next_event = events.iloc[0]
            result["next_inbound_date"] = next_event["receipt_date"] if next_event["timing_known"] else pd.NaT
            result["next_inbound_expected_date"] = next_event["expected_receipt_date"]
            result["next_inbound_cases"] = next_event["inbound_cases"]
            result["next_inbound_type"] = next_event["inbound_type"]
            result["next_inbound_timing_known"] = bool(next_event["timing_known"])
            result["next_inbound_overdue"] = bool(next_event["is_overdue"])

        # Comfortably covered for more than two weeks.
        if current_woh >= floor_weeks and days_until_floor > monitor_weeks * 7:
            result["classification_reason"] = f"Current inventory is {current_woh:.1f} WOH with more than {monitor_weeks:g} weeks before reaching the {floor_weeks:g}-WOH floor"
            rows.append(result)
            continue

        # Getting close, but inventory can still cover a fresh replenishment cycle.
        if current_woh >= floor_weeks and days_until_floor > lead_days:
            result["inventory_status"] = "monitor"
            result["classification_reason"] = f"Current inventory is {current_woh:.1f} WOH and approaching the {floor_weeks:g}-WOH floor"
            rows.append(result)
            continue

       # Inventory now depends on replenishment.
        projected_cases = current_cases
        previous_date = today
        lowest_woh = current_woh
        covered = False
        inbound_too_late = False

        debug_grw_strawberry = (
            row["distributor"] == "UNFI"
            and row["dc"] == "GRW"
            and row["sku"] == "STRAWBERRY"
        )

        if debug_grw_strawberry:
            print("\n" + "=" * 80)
            print("GRW STRAWBERRY — INVENTORY SIMULATION")
            print("=" * 80)
            print("as_of_date:", today)
            print("report_date:", row.get("report_date"))
            print("current_cases:", current_cases)
            print("current_woh:", current_woh)
            print("velocity_cases/week:", velocity_cases)
            print("floor_weeks:", floor_weeks)
            print("tolerance_weeks:", tolerance_weeks)
            print("lead_days:", lead_days)

            print("\n--- INBOUND EVENTS ---")
            if events.empty:
                print("NO INBOUND EVENTS")
            else:
                print(events.to_string(index=False))


        for _, event in events.iterrows():

            if debug_grw_strawberry:
                print("\n" + "-" * 60)
                print("PROCESSING INBOUND")
                print("-" * 60)
                print("type:", event["inbound_type"])
                print("receipt_date:", event["receipt_date"])
                print("cases:", event["inbound_cases"])
                print("timing_known:", event["timing_known"])
                print("inventory at previous event:", projected_cases)
                print("previous_date:", previous_date)

            elapsed_weeks = max(
                (event["receipt_date"] - previous_date).total_seconds()
                / (7 * 24 * 60 * 60),
                0,
            )

            projected_cases = max(
                projected_cases - velocity_cases * elapsed_weeks,
                0,
            )

            woh_before_receipt = projected_cases / velocity_cases
            lowest_woh = min(lowest_woh, woh_before_receipt)

            if debug_grw_strawberry:
                print("elapsed_weeks:", elapsed_weeks)
                print("inventory BEFORE receipt:", projected_cases)
                print("WOH BEFORE receipt:", woh_before_receipt)
                print("lowest WOH so far:", lowest_woh)

            if (
                woh_before_receipt < floor_weeks - tolerance_weeks
                and event["receipt_date"] > today
            ):
                inbound_too_late = True

            projected_cases += event["inbound_cases"]

            woh_after_receipt = projected_cases / velocity_cases
            previous_date = event["receipt_date"]

            if debug_grw_strawberry:
                print("inventory AFTER receipt:", projected_cases)
                print("WOH AFTER receipt:", woh_after_receipt)
                print("inbound_too_late:", inbound_too_late)

            # Receipt sequence has restored a healthy inventory position.
            if woh_after_receipt >= floor_weeks:
                covered = True

                if event["inbound_type"] == "projected_order":
                    result["po_status"] = "po_expected"

                if debug_grw_strawberry:
                    print("COVERED = True")
                    print(
                        "BREAKING LOOP because this inbound restored "
                        f"inventory to {woh_after_receipt:.2f} WOH"
                    )

                break


        if debug_grw_strawberry:
            print("\n--- FINAL SIMULATION RESULT ---")
            print("covered:", covered)
            print("lowest_woh:", lowest_woh)
            print("inbound_too_late:", inbound_too_late)
            print("=" * 80)

        result["lowest_woh_before_coverage"] = lowest_woh

        # Allow a temporary dip of up to 0.5 WOH below the floor.
        if covered and lowest_woh >= floor_weeks - tolerance_weeks:
            result["inventory_status"] = "monitor"
            unknown_committed = events["inbound_type"].eq("committed_po") & ~events["timing_known"]
            overdue_committed = events["inbound_type"].eq("committed_po") & events["is_overdue"]

            if unknown_committed.any():
                result["action_type"] = "follow_up_po"
                result["classification_reason"] = f"{events.loc[unknown_committed, 'inbound_cases'].sum():.0f} cases are on an outstanding PO and provide adequate inventory if received; confirm expected receipt timing"
            elif overdue_committed.any():
                overdue_event = events[overdue_committed].iloc[0]
                result["action_type"] = "follow_up_po"
                result["classification_reason"] = f"Outstanding PO expected {pd.Timestamp(overdue_event['expected_receipt_date']).strftime('%Y-%m-%d')} is overdue but provides adequate inventory if received; follow up on the PO"
            else:
                result["classification_reason"] = "Inventory depends on upcoming replenishment, but expected inbound maintains adequate coverage"

            rows.append(result)
            continue

        # ------------------------------------------------------------------
        # Action
        # ------------------------------------------------------------------

        result["inventory_status"] = "action"
        result["action_type"] = "send_inventory"

        recommendation_input = pd.DataFrame([row]).copy()
        recommendation_input["median_replenishment_days"] = lead_days
        unknown_committed_cases = events.loc[events["inbound_type"].eq("committed_po") & ~events["timing_known"], "inbound_cases"].sum()
        if unknown_committed_cases > 0:
            recommendation_input["quantity_on_hand_cases"] = recommendation_input["quantity_on_hand_cases"] + unknown_committed_cases
        recommendation = calculate_recommended_order_for_date(recommendation_input, purchase_orders=purchase_orders, order_date=as_of_date, target_weeks=target_weeks)
        result["recommended_order_cases"] = recommendation.iloc[0]["recommended_order_cases"]
        result["recommended_order_deadline"] = floor_date - pd.to_timedelta(lead_days, unit="D")

        if pd.notna(result["recommended_order_cases"]) and result["recommended_order_cases"] == 0:
            result["inventory_status"] = "monitor"
            result["action_type"] = "no_action"

        days_until_oos = current_woh * 7
        days_of_cushion = days_until_oos - lead_days

        result["days_until_oos"] = days_until_oos
        result["days_of_cushion"] = days_of_cushion

        if days_of_cushion <= 3:
            result["inventory_urgency"] = "critical"
        elif days_of_cushion <= 7:
            result["inventory_urgency"] = "high"
        else:
            result["inventory_urgency"] = "normal"


        if result["inventory_status"] == "monitor":
            result["classification_reason"] = f"Inventory is projected to dip to {lowest_woh:.1f} WOH, but no additional order is recommended"
        elif events.empty:
            result["classification_reason"] = f"Inventory needs replenishment; {result['recommended_order_cases']:.0f} additional cases are recommended"
        elif inbound_too_late:
            result["classification_reason"] = f"Upcoming inbound arrives too late to prevent the inventory gap; {result['recommended_order_cases']:.0f} additional cases are recommended"
        else:
            result["classification_reason"] = f"Upcoming inbound is insufficient; {result['recommended_order_cases']:.0f} additional cases are recommended"

        rows.append(result)

    return pd.DataFrame(rows)


if __name__ == "__main__":
    from pathlib import Path

    from backend.metrics.inventory.expected_orders import build_unfi_expected_order_events, build_kehe_expected_order_events
    from backend.transforms.inventory.unfi import transform_unfi_projected_orders, transform_unfi_purchase_orders
    from backend.transforms.inventory.kehe import transform_kehe_order_projections

    org_id = "default_org"
    org_dir = Path("backend/data") / org_id
    as_of_date = "2026-09-15"

    inventory = pd.read_csv(org_dir / "inventory_features_test.csv")

    unfi_projected_orders = transform_unfi_projected_orders(
        pd.read_csv(org_dir / "raw/inventory/unfi/Projected Orders Detail.csv"),
        org_id=org_id,
    )

    kehe_projected_orders = transform_kehe_order_projections(
        pd.read_csv(org_dir / "raw/inventory/kehe/Order Projections Report.csv"),
        org_id=org_id,
    )

    purchase_orders = transform_unfi_purchase_orders(
        pd.read_csv(org_dir / "raw/inventory/unfi/Purchase Orders.csv"),
        org_id=org_id,
    )

    expected_orders = pd.concat([
        build_unfi_expected_order_events(unfi_projected_orders),
        build_kehe_expected_order_events(kehe_projected_orders),
    ], ignore_index=True)

    result = run_inventory_risk(
        df=inventory.copy(),
        inventory_history=inventory,
        expected_orders=expected_orders,
        purchase_orders=purchase_orders,
        as_of_date=as_of_date,
    )

    columns = [
        "distributor",
        "dc",
        "sku",
        "calculated_weeks_on_hand",
        "planning_lead_time_days",
        "next_inbound_date",
        "next_inbound_expected_date",
        "next_inbound_timing_known",
        "next_inbound_overdue",
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
    ]

    print("\n=== INVENTORY ASSESSMENT ===\n")
    print(result[columns].sort_values(["distributor", "dc", "sku"]).to_string(index=False))
from __future__ import annotations

import numpy as np
import pandas as pd

from backend.forecasting.inventory_projection import project_inventory_trajectory


# =============================================================================
# HELPERS
# =============================================================================

def _velocity_cases_per_week(row: pd.Series) -> float:
    units = pd.to_numeric(row.get("dc_weekly_velocity"), errors="coerce")
    case_pack = pd.to_numeric(row.get("units_per_case"), errors="coerce")

    if pd.isna(units) or pd.isna(case_pack) or case_pack <= 0:
        return np.nan

    return float(units / case_pack)


def _get_po_delivery_date(
    po: pd.Series,
    report_date: pd.Timestamp,
    lead_days: float,
) -> tuple[pd.Timestamp, str]:
    """
    Determine when a confirmed PO is expected to arrive.

    Priority:
        1. Distributor-provided projected delivery date
        2. PO create date + observed lead time
        3. Report date + observed lead time

    The final option is explicitly flagged because PO creation timing
    is unknown.
    """

    distributor_dates = [
        "delivery_appointment_date",
        "revised_eta_date",
        "original_eta_date",
    ]

    for column in distributor_dates:
        if column in po.index:
            date = pd.to_datetime(po.get(column), errors="coerce")

            if pd.notna(date):
                return date.normalize(), "distributor_delivery_date"

    po_create_date = pd.to_datetime(
        po.get("po_create_date"),
        errors="coerce",
    )

    if pd.notna(po_create_date):
        return (
            po_create_date.normalize()
            + pd.to_timedelta(lead_days, unit="D"),
            "po_create_date_plus_lead_time",
        )

    return (
        report_date + pd.to_timedelta(lead_days, unit="D"),
        "report_date_plus_lead_time_missing_po_create_date",
    )


def _get_confirmed_po_events(
    row: pd.Series,
    purchase_orders: pd.DataFrame,
    as_of_date: pd.Timestamp,
) -> pd.DataFrame:
    """
    Return confirmed/open POs for this DC × SKU.

    Purchase Orders file is the source of truth for committed supply.

    Open POs remain valid committed supply unless they are more than
    4 planning lead times past their expected delivery date.

    Stale POs are retained in the returned data for visibility/narrative,
    but their receipt_date is set to NaT so they can be excluded from
    inventory trajectory calculations.
    """

    columns = [
        "receipt_date",
        "expected_delivery_date",
        "cases",
        "po_status",
        "is_stale",
        "overdue_days",
        "timing_source",
        "timing_flag",
    ]

    if purchase_orders is None or purchase_orders.empty:
        return pd.DataFrame(columns=columns)

    po = purchase_orders[
        (purchase_orders["distributor"] == row["distributor"])
        & (purchase_orders["dc"] == row["dc"])
        & (purchase_orders["sku"] == row["sku"])
    ].copy()

    if po.empty:
        return pd.DataFrame(columns=columns)

    po["open_quantity_cases"] = pd.to_numeric(
        po["open_quantity_cases"],
        errors="coerce",
    )

    po = po[
        (po["open_quantity_cases"] > 0)
        & (po["po_status"].astype(str).str.upper() == "OPEN")
    ].copy()

    if po.empty:
        return pd.DataFrame(columns=columns)

    report_date = pd.Timestamp(row["report_date"]).normalize()
    as_of_date = pd.Timestamp(as_of_date).normalize()
    lead_days = float(row["planning_lead_time_days"])

    stale_after_days = 4 * lead_days

    events = []

    for _, p in po.iterrows():
        expected_delivery_date, timing_source = _get_po_delivery_date(
            p,
            report_date=report_date,
            lead_days=lead_days,
        )

        expected_delivery_date = pd.Timestamp(
            expected_delivery_date
        ).normalize()

        timing_flag = (
            "missing_po_create_date"
            if timing_source
            == "report_date_plus_lead_time_missing_po_create_date"
            else None
        )

        # Determine whether the open PO is active, overdue, or stale.
        if expected_delivery_date >= as_of_date:
            po_status = "active"
            overdue_days = 0
            is_stale = False
            receipt_date = expected_delivery_date

        else:
            overdue_days = (as_of_date - expected_delivery_date).days
            is_stale = overdue_days > stale_after_days

            if is_stale:
                po_status = "stale"

                # Keep the PO for visibility/narrative, but prevent it
                # from participating in inventory trajectory math.
                receipt_date = pd.NaT
            else:
                po_status = "overdue"

                # Preserve existing behavior for legitimate overdue POs.
                receipt_date = expected_delivery_date

        events.append({
            "receipt_date": receipt_date,
            "expected_delivery_date": expected_delivery_date,
            "cases": float(p["open_quantity_cases"]),
            "po_status": po_status,
            "is_stale": is_stale,
            "overdue_days": overdue_days,
            "timing_source": timing_source,
            "timing_flag": timing_flag,
        })

    return (
        pd.DataFrame(events, columns=columns)
        .sort_values(
            "expected_delivery_date",
            na_position="last",
        )
        .reset_index(drop=True)
    )


def _simulate_trajectory(
    start_date,
    start_cases: float,
    velocity_cases_per_week: float,
    end_date,
    inbound_events: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Simulate inventory one day at a time.

    This is intentionally generic so the exact same inventory math can
    be used for:
        - baseline projection
        - projected-order counterfactuals
        - intervention counterfactuals
    """

    start_date = pd.Timestamp(start_date).normalize()
    end_date = pd.Timestamp(end_date).normalize()

    daily_velocity = velocity_cases_per_week / 7
    inventory = float(start_cases)

    if inbound_events is None or inbound_events.empty:
        inbound_by_date = {}
    else:
        events = inbound_events.copy()
        events["receipt_date"] = pd.to_datetime(
            events["receipt_date"],
            errors="coerce",
        ).dt.normalize()

        events["cases"] = pd.to_numeric(
            events["cases"],
            errors="coerce",
        ).fillna(0)

        inbound_by_date = (
            events.groupby("receipt_date")["cases"]
            .sum()
            .to_dict()
        )

    rows = []

    for date in pd.date_range(start_date, end_date, freq="D"):
        # Starting date represents inventory at the beginning of the
        # projection. Consumption begins after that point.
        if date > start_date:
            inventory = max(inventory - daily_velocity, 0)

        inbound_cases = float(inbound_by_date.get(date, 0))
        inventory += inbound_cases

        rows.append({
            "date": date,
            "inventory_cases": inventory,
            "weeks_on_hand": (
                inventory / velocity_cases_per_week
                if velocity_cases_per_week > 0
                else np.nan
            ),
            "inbound_cases": inbound_cases,
        })

    return pd.DataFrame(rows)


# =============================================================================
# 1. BASELINE PROJECTION
# =============================================================================

def project_baseline_inventory(
    row: pd.Series,
    purchase_orders: pd.DataFrame,
    as_of_date,
    lookahead_days: int = 42,
) -> dict:
    """
    Answer:

        "How many cases do we think we have today, and what happens
        over the next six weeks if nothing changes?"

    Only confirmed/open POs are counted as inbound inventory.

    Projected/unplaced orders are NOT included.
    """

    as_of_date = pd.Timestamp(as_of_date).normalize()
    report_date = pd.Timestamp(row["report_date"]).normalize()

    velocity = _velocity_cases_per_week(row)

    if pd.isna(velocity) or velocity <= 0:
        raise ValueError("Cannot project inventory without positive velocity.")

    observed_cases = pd.to_numeric(
        row.get("quantity_on_hand_cases"),
        errors="coerce",
    )

    if pd.isna(observed_cases):
        raise ValueError("Cannot project inventory without observed QOH.")

    po_events = _get_confirmed_po_events(
        row=row,
        purchase_orders=purchase_orders,
        as_of_date=as_of_date,
    )

    planning_po_events = po_events[
        po_events["is_stale"].eq(False)
    ].copy()

    # ------------------------------------------------------------------
    # Age the last observed inventory forward to today.
    # ------------------------------------------------------------------

    events_since_report = planning_po_events[
        (planning_po_events["receipt_date"] > report_date)
        & (planning_po_events["receipt_date"] <= as_of_date)
    ].copy()

    historical_projection = _simulate_trajectory(
        start_date=report_date,
        start_cases=float(observed_cases),
        velocity_cases_per_week=velocity,
        end_date=as_of_date,
        inbound_events=events_since_report,
    )

    estimated_cases_today = float(
        historical_projection.iloc[-1]["inventory_cases"]
    )

    # ------------------------------------------------------------------
    # Project today through the lookahead using confirmed supply only.
    # ------------------------------------------------------------------
    
    future_po_events = planning_po_events[
        planning_po_events["receipt_date"] > as_of_date
    ].copy()

    projection_end = (
        as_of_date
        + pd.to_timedelta(lookahead_days, unit="D")
    )

    trajectory = _simulate_trajectory(
        start_date=as_of_date,
        start_cases=estimated_cases_today,
        velocity_cases_per_week=velocity,
        end_date=projection_end,
        inbound_events=future_po_events,
    )

    return {
        "as_of_date": as_of_date,
        "report_date": report_date,

        "observed_cases": float(observed_cases),
        "estimated_cases_today": estimated_cases_today,

        "velocity_cases_per_week": velocity,

        "confirmed_po_events": po_events,
        "trajectory": trajectory,
    }


# =============================================================================
# 2. BREACH ANALYSIS
# =============================================================================

def analyze_inventory_breaches(
    baseline: dict,
    floor_weeks: float = 3,
    buffer_weeks: float = 0.5,
) -> dict:
    """
    Answer:

        "At what points does the confirmed-supply trajectory become
        unacceptable?"

    We track:
        floor      = 3 WOH
        buffer     = 0.5 WOH
        tolerance  = 2.5 WOH
        OOS        = 0 cases

    A floor breach is worth monitoring.
    A tolerance breach represents a problem requiring resolution.
    """

    trajectory = baseline["trajectory"].copy()

    tolerance_weeks = floor_weeks - buffer_weeks

    trajectory["below_floor"] = (
        trajectory["weeks_on_hand"] < floor_weeks
    )

    trajectory["below_tolerance"] = (
        trajectory["weeks_on_hand"] < tolerance_weeks
    )

    trajectory["oos"] = (
        trajectory["inventory_cases"] <= 0
    )

    # ------------------------------------------------------------------
    # Identify continuous breach episodes.
    # ------------------------------------------------------------------

    episodes = []

    in_episode = False
    start_index = None

    for i, row in trajectory.iterrows():
        breached = bool(row["below_floor"])

        if breached and not in_episode:
            in_episode = True
            start_index = i

        is_last_row = i == trajectory.index[-1]

        if in_episode and (not breached or is_last_row):
            end_index = i if breached and is_last_row else i - 1

            episode = trajectory.loc[start_index:end_index].copy()

            lowest_idx = episode["weeks_on_hand"].idxmin()
            lowest = episode.loc[lowest_idx]

            tolerance_rows = episode[
                episode["below_tolerance"]
            ]

            oos_rows = episode[
                episode["oos"]
            ]

            recovery_date = None

            if end_index < trajectory.index[-1]:
                recovery_date = trajectory.loc[
                    end_index + 1,
                    "date",
                ]

            episodes.append({
                "start_date": episode.iloc[0]["date"],
                "end_date": episode.iloc[-1]["date"],
                "recovery_date": recovery_date,

                "lowest_woh": float(lowest["weeks_on_hand"]),
                "lowest_woh_date": lowest["date"],

                "breaches_tolerance": not tolerance_rows.empty,
                "first_tolerance_breach_date": (
                    tolerance_rows.iloc[0]["date"]
                    if not tolerance_rows.empty
                    else None
                ),

                "reaches_oos": not oos_rows.empty,
                "first_oos_date": (
                    oos_rows.iloc[0]["date"]
                    if not oos_rows.empty
                    else None
                ),
            })

            in_episode = False
            start_index = None

    lowest_idx = trajectory["weeks_on_hand"].idxmin()
    lowest = trajectory.loc[lowest_idx]

    tolerance_rows = trajectory[
        trajectory["below_tolerance"]
    ]

    oos_rows = trajectory[
        trajectory["oos"]
    ]

    return {
        "floor_weeks": floor_weeks,
        "buffer_weeks": buffer_weeks,
        "tolerance_weeks": tolerance_weeks,

        "has_floor_breach": bool(
            trajectory["below_floor"].any()
        ),

        "has_tolerance_breach": bool(
            trajectory["below_tolerance"].any()
        ),

        "has_oos": bool(
            trajectory["oos"].any()
        ),

        "first_floor_breach_date": (
            trajectory.loc[
                trajectory["below_floor"],
                "date",
            ].iloc[0]
            if trajectory["below_floor"].any()
            else None
        ),

        "first_tolerance_breach_date": (
            tolerance_rows.iloc[0]["date"]
            if not tolerance_rows.empty
            else None
        ),

        "first_oos_date": (
            oos_rows.iloc[0]["date"]
            if not oos_rows.empty
            else None
        ),

        "lowest_woh": float(lowest["weeks_on_hand"]),
        "lowest_woh_date": lowest["date"],

        "episodes": episodes,
    }


# =============================================================================
# 3. PROJECTED ORDER EVALUATION
# =============================================================================

def evaluate_projected_orders(
    row: pd.Series,
    baseline: dict,
    breaches: dict,
    expected_orders: pd.DataFrame,
) -> dict:
    """
    Evaluate projected/uncommitted distributor orders against each
    individual material breach.

    Projected orders are tested as counterfactuals.

    They are never added to the canonical baseline and never reduce a
    later recommended quantity.
    """

    orders = expected_orders[
        (expected_orders["distributor"] == row["distributor"])
        & (expected_orders["dc"] == row["dc"])
        & (expected_orders["sku"] == row["sku"])
    ].copy()

    if not orders.empty:
        orders["expected_order_date"] = pd.to_datetime(
            orders["expected_order_date"],
            errors="coerce",
        ).dt.normalize()

        orders["expected_order_cases"] = pd.to_numeric(
            orders["expected_order_cases"],
            errors="coerce",
        )

        orders = orders[
            orders["expected_order_date"].notna()
            & orders["expected_order_cases"].gt(0)
        ].sort_values("expected_order_date")

    lead_days = float(row["planning_lead_time_days"])
    velocity = baseline["velocity_cases_per_week"]

    as_of_date = baseline["as_of_date"]
    trajectory_end = baseline["trajectory"]["date"].max()

    confirmed = baseline["confirmed_po_events"].copy()

    confirmed = confirmed[
        confirmed["receipt_date"] > as_of_date
    ][["receipt_date", "cases"]]

    enriched_breaches = []

    for breach in breaches["episodes"]:
        breach = breach.copy()

        # A floor breach that stays inside the allowed buffer does not
        # require an intervention.
        if not breach["breaches_tolerance"]:
            breach["projected_order"] = {
                "projected_order_exists": False,
                "resolves_breach": False,
                "reason": "no_intervention_required",
                "orders": [],
            }

            enriched_breaches.append(breach)
            continue

        if orders.empty:
            breach["projected_order"] = {
                "projected_order_exists": False,
                "resolves_breach": False,
                "reason": "no_projected_order",
                "orders": [],
            }

            enriched_breaches.append(breach)
            continue

        evaluated_orders = []
        projected_events = []

        for _, order in orders.iterrows():
            receipt_date = (
                order["expected_order_date"]
                + pd.to_timedelta(lead_days, unit="D")
            )

            cases = float(order["expected_order_cases"])

            if receipt_date > trajectory_end:
                evaluated_orders.append({
                    "expected_order_date": order["expected_order_date"],
                    "expected_receipt_date": receipt_date,
                    "cases": cases,
                    "within_lookahead": False,
                    "resolves_breach": False,
                    "reason": "outside_lookahead",
                })
                continue

            projected_events.append({
                "receipt_date": receipt_date,
                "cases": cases,
            })

            counterfactual_events = pd.concat(
                [
                    confirmed,
                    pd.DataFrame(projected_events),
                ],
                ignore_index=True,
            )

            counterfactual = _simulate_trajectory(
                start_date=as_of_date,
                start_cases=baseline["estimated_cases_today"],
                velocity_cases_per_week=velocity,
                end_date=trajectory_end,
                inbound_events=counterfactual_events,
            )

            # ----------------------------------------------------------
            # Evaluate THIS breach only.
            #
            # A projected order resolves this breach if the inventory
            # trajectory stays at or above the tolerance threshold for
            # the dates belonging to this breach episode.
            # ----------------------------------------------------------

            breach_window = counterfactual[
                (counterfactual["date"] >= breach["start_date"])
                & (counterfactual["date"] <= breach["end_date"])
            ]

            tolerance_weeks = breaches["tolerance_weeks"]

            resolves_breach = (
                not breach_window.empty
                and (
                    breach_window["weeks_on_hand"]
                    >= tolerance_weeks
                ).all()
            )

            baseline_row = baseline["trajectory"][
                baseline["trajectory"]["date"] == receipt_date
            ]

            counterfactual_row = counterfactual[
                counterfactual["date"] == receipt_date
            ]

            woh_before_order = (
                float(baseline_row.iloc[0]["weeks_on_hand"])
                if not baseline_row.empty
                else np.nan
            )

            woh_after_order = (
                float(counterfactual_row.iloc[0]["weeks_on_hand"])
                if not counterfactual_row.empty
                else np.nan
            )

            problem_date = breach[
                "first_tolerance_breach_date"
            ]

            arrives_before_problem = (
                receipt_date <= problem_date
                if problem_date is not None
                else True
            )

            if resolves_breach:
                reason = "resolves_breach"
            elif not arrives_before_problem:
                reason = "arrives_too_late"
            else:
                reason = "insufficient_to_resolve_breach"

            evaluated_orders.append({
                "expected_order_date": order["expected_order_date"],
                "expected_receipt_date": receipt_date,
                "cases": cases,
                "within_lookahead": True,

                "woh_at_receipt_without_projected_order": woh_before_order,
                "woh_at_receipt_with_projected_order": woh_after_order,

                "arrives_before_problem": arrives_before_problem,
                "resolves_breach": resolves_breach,
                "reason": reason,
            })

            if resolves_breach:
                break

        resolving_orders = [
            order
            for order in evaluated_orders
            if order.get("resolves_breach")
        ]

        breach["projected_order"] = {
            "projected_order_exists": True,
            "resolves_breach": bool(resolving_orders),
            "reason": (
                "projected_orders_resolve_breach"
                if resolving_orders
                else "projected_orders_do_not_resolve_breach"
            ),
            "orders": evaluated_orders,
            "resolving_order": (
                resolving_orders[0]
                if resolving_orders
                else None
            ),
        }

        enriched_breaches.append(breach)

    return {
        "projected_order_exists": not orders.empty,
        "breaches": enriched_breaches,
    }


# =============================================================================
# 4. REQUIRED INTERVENTION
# =============================================================================

def calculate_required_intervention(
    row: pd.Series,
    baseline: dict,
    breaches: dict,
    projected_order_analysis: dict,
    target_weeks: float = 5,
    surface_warning_days = 7,
) -> dict:
    """
    Determine the appropriate intervention for each individual breach.

    Confirmed POs are already included in the baseline.

    Projected orders NEVER reduce recommended quantity.

    For a new order, required inventory coverage at delivery is:

        max(target WOH, lead time in weeks)

    The idea is that when the new inventory arrives, we can reassess
    the inventory position and immediately place another order if
    necessary. The delivered inventory therefore needs to cover at
    least one full additional lead time, or the normal target WOH,
    whichever is larger.
    """

    velocity = baseline["velocity_cases_per_week"]
    as_of_date = baseline["as_of_date"]
    trajectory = baseline["trajectory"]

    lead_days = float(row["planning_lead_time_days"])
    lead_weeks = lead_days / 7

    required_coverage_weeks = max(
        target_weeks,
        lead_weeks,
    )

    confirmed_pos = baseline["confirmed_po_events"].copy()

    future_pos = confirmed_pos[
        confirmed_pos["receipt_date"] > as_of_date
    ].copy()

    enriched_breaches = []

    for breach in projected_order_analysis["breaches"]:
        breach = breach.copy()

        # --------------------------------------------------------------
        # Breach remains inside allowed tolerance.
        # --------------------------------------------------------------

        if not breach["breaches_tolerance"]:
            breach["intervention"] = {
                "intervention_required": False,
                "intervention_type": "none",
                "recommended_cases": 0,
                "reason": "within_allowed_buffer",
            }

            enriched_breaches.append(breach)
            continue

        projected_order = breach["projected_order"]

        # --------------------------------------------------------------
        # Projected order resolves this specific breach.
        # --------------------------------------------------------------

        if projected_order.get("resolves_breach"):
            breach["intervention"] = {
                "intervention_required": False,
                "intervention_type": "monitor_projected_order",
                "recommended_cases": 0,
                "reason": "projected_order_resolves_breach",
            }

            enriched_breaches.append(breach)
            continue

        problem_date = breach[
            "first_tolerance_breach_date"
        ]

        # --------------------------------------------------------------
        # Can an existing confirmed PO solve THIS breach if it arrives
        # sooner?
        # --------------------------------------------------------------

        expedite_candidate = None

        for _, po in future_pos.iterrows():
            original_receipt_date = po["receipt_date"]

            # This PO is already scheduled before the material breach.
            if original_receipt_date <= problem_date:
                continue

            test_events = future_pos[
                ["receipt_date", "cases"]
            ].copy()

            # Move only this PO to the first tolerance-breach date.
            matching_indexes = test_events[
                test_events.index == po.name
            ].index

            if len(matching_indexes) == 0:
                continue

            test_events.loc[
                matching_indexes[0],
                "receipt_date",
            ] = problem_date

            expedited_trajectory = _simulate_trajectory(
                start_date=as_of_date,
                start_cases=baseline["estimated_cases_today"],
                velocity_cases_per_week=velocity,
                end_date=trajectory["date"].max(),
                inbound_events=test_events,
            )

            # Evaluate only this breach episode.
            breach_window = expedited_trajectory[
                (
                    expedited_trajectory["date"]
                    >= breach["start_date"]
                )
                & (
                    expedited_trajectory["date"]
                    <= breach["end_date"]
                )
            ]

            resolves_this_breach = (
                not breach_window.empty
                and (
                    breach_window["weeks_on_hand"]
                    >= breaches["tolerance_weeks"]
                ).all()
            )

            if resolves_this_breach:
                expedite_candidate = {
                    "cases": float(po["cases"]),
                    "current_receipt_date": original_receipt_date,
                    "needed_by_date": problem_date,
                    "timing_source": po["timing_source"],
                }
                break

        if expedite_candidate is not None:
            breach["intervention"] = {
                "intervention_required": True,
                "intervention_type": "expedite_po",
                "recommended_cases": 0,

                "po_cases": expedite_candidate["cases"],
                "current_po_receipt_date": (
                    expedite_candidate["current_receipt_date"]
                ),
                "needed_by_date": (
                    expedite_candidate["needed_by_date"]
                ),

                "reason": (
                    "confirmed_po_quantity_is_adequate_"
                    "but_arrives_too_late"
                ),
            }

            enriched_breaches.append(breach)
            continue


        # --------------------------------------------------------------
        # No projected order or confirmed PO resolves this breach.
        # Determine when a new order needs to be placed.
        # --------------------------------------------------------------

        needed_by_date = pd.Timestamp(
            breach["first_tolerance_breach_date"]
        )

        order_by_date = (
            needed_by_date
            - pd.Timedelta(days=lead_days)
        )

        surface_date = (
            order_by_date
            - pd.Timedelta(days=7)
        )

        # --------------------------------------------------------------
        # The problem is real, but it is too early to surface an
        # actionable recommendation.
        # --------------------------------------------------------------

        if as_of_date < surface_date:
            breach["intervention"] = {
                "intervention_required": False,
                "intervention_type": "future_replenishment",
                "recommended_cases": 0,
                "needed_by_date": needed_by_date,
                "order_by_date": order_by_date,
                "surface_date": surface_date,
                "reason": "outside_recommendation_window",
            }

            enriched_breaches.append(breach)
            continue

        # --------------------------------------------------------------
        # We are inside the recommendation window.
        #
        # Before the order-by date, size the recommendation using the
        # planned order-by date so the recommended quantity remains
        # stable rather than changing every day.
        #
        # If the order-by date has already passed, use today.
        # --------------------------------------------------------------

        planned_order_date = max(
            as_of_date,
            order_by_date,
        )

        expected_delivery_date = (
            planned_order_date
            + pd.Timedelta(days=lead_days)
        )

        # If a normal new order cannot arrive before this breach episode
        # is already over, it cannot solve this particular breach.
        if expected_delivery_date > breach["end_date"]:
            breach["intervention"] = {
                "intervention_required": True,
                "intervention_type": "review",
                "recommended_cases": np.nan,
                "expected_delivery_date": expected_delivery_date,
                "reason": "new_order_cannot_arrive_in_time_for_breach",
            }

            enriched_breaches.append(breach)
            continue

        delivery_row = trajectory[
            trajectory["date"] == expected_delivery_date
        ]

        if delivery_row.empty:
            breach["intervention"] = {
                "intervention_required": True,
                "intervention_type": "review",
                "recommended_cases": np.nan,
                "reason": "delivery_date_outside_projection",
            }

            enriched_breaches.append(breach)
            continue

        projected_cases_at_delivery = float(
            delivery_row.iloc[0]["inventory_cases"]
        )

        target_cases_at_delivery = (
            velocity * required_coverage_weeks
        )

        raw_recommended_cases = max(
            target_cases_at_delivery
            - projected_cases_at_delivery,
            0,
        )

        recommended_cases = int(
            max(
                15,
                np.floor(raw_recommended_cases / 15 + 0.5) * 15,
            )
        )

        breach["intervention"] = {
            "intervention_required": True,
            "intervention_type": "new_order",

            "recommended_cases": recommended_cases,
            "expected_delivery_date": expected_delivery_date,

            "order_date": planned_order_date,
            "order_by_date": order_by_date,
            "surface_date": surface_date,
            "needed_by_date": needed_by_date,

            "projected_cases_at_delivery": (
                projected_cases_at_delivery
            ),

            "target_cases_at_delivery": (
                target_cases_at_delivery
            ),

            "target_weeks": target_weeks,
            "lead_time_weeks": lead_weeks,
            "required_coverage_weeks": (
                required_coverage_weeks
            ),

            "reason": "additional_inventory_required",
        }

        enriched_breaches.append(breach)

    return {
        "breaches": enriched_breaches,
    }


# =============================================================================
# 5. CLASSIFICATION
# =============================================================================

def classify_inventory_assessment(
    row: pd.Series,
    baseline: dict,
    breaches: dict,
    projected_order_analysis: dict,
    intervention: dict,
) -> dict:
    """
    Classify the completed inventory assessment into three independent
    operational dimensions:

        inventory_status
            healthy
            monitor
            action

        inventory_urgency
            normal
            high
            critical

        po_status
            none
            po_outstanding
            po_overdue
            po_stale
            po_expected

    This function performs no inventory projection and makes no
    replenishment decisions. It only classifies facts already established
    by the baseline, breach, projected-order, and intervention stages.

    Stale POs remain visible here even though they have already been
    excluded from inventory planning upstream.
    """

    velocity = float(
        baseline["velocity_cases_per_week"]
    )

    current_cases = float(
        baseline["estimated_cases_today"]
    )

    current_woh = (
        current_cases / velocity
        if velocity > 0
        else np.nan
    )

    lead_days = float(
        row["planning_lead_time_days"]
    )

    # ------------------------------------------------------------------
    # Inventory status
    # ------------------------------------------------------------------

    material_breaches = [
        breach
        for breach in intervention["breaches"]
        if breach.get("breaches_tolerance")
    ]

    active_interventions = [
        breach.get("intervention", {})
        for breach in material_breaches
        if breach.get(
            "intervention",
            {},
        ).get(
            "intervention_required"
        )
    ]

    monitor_projected_order = any(
        breach.get(
            "intervention",
            {},
        ).get(
            "intervention_type"
        ) == "monitor_projected_order"
        for breach in material_breaches
    )

    if active_interventions:
        inventory_status = "action"

    elif (
        material_breaches
        or breaches.get("has_floor_breach")
        or monitor_projected_order
    ):
        inventory_status = "monitor"

    else:
        inventory_status = "healthy"

    # ------------------------------------------------------------------
    # Inventory urgency
    #
    # Preserve the old SKUba definition:
    #
    #     days_until_oos = current WOH * 7
    #     days_of_cushion = days_until_oos - lead time
    #
    #     <= 3 days  -> critical
    #     <= 7 days  -> high
    #     >  7 days  -> normal
    # ------------------------------------------------------------------

    days_until_oos = (
        current_woh * 7
        if pd.notna(current_woh)
        else np.nan
    )

    days_of_cushion = (
        days_until_oos - lead_days
        if pd.notna(days_until_oos)
        else np.nan
    )

    if inventory_status != "action":
        inventory_urgency = "normal"

    elif pd.isna(days_of_cushion):
        inventory_urgency = "normal"

    elif days_of_cushion <= 1:
        inventory_urgency = "critical"

    elif days_of_cushion <= 7:
        inventory_urgency = "high"

    else:
        inventory_urgency = "normal"

    # ------------------------------------------------------------------
    # Confirmed PO state
    # ------------------------------------------------------------------

    confirmed_pos = baseline.get(
        "confirmed_po_events"
    )

    has_active_po = False
    has_overdue_po = False
    has_stale_po = False

    if (
        confirmed_pos is not None
        and not confirmed_pos.empty
    ):
        has_active_po = bool(
            confirmed_pos[
                "po_status"
            ].eq("active").any()
        )

        has_overdue_po = bool(
            confirmed_pos[
                "po_status"
            ].eq("overdue").any()
        )

        has_stale_po = bool(
            confirmed_pos[
                "is_stale"
            ].eq(True).any()
        )

    # ------------------------------------------------------------------
    # Projected-order state
    # ------------------------------------------------------------------

    has_projected_order = bool(
        projected_order_analysis.get(
            "projected_order_exists",
            False,
        )
    )

    has_resolving_projected_order = any(
        breach.get(
            "projected_order",
            {},
        ).get(
            "resolves_breach",
            False,
        )
        for breach in material_breaches
    )

    # ------------------------------------------------------------------
    # Primary PO status
    #
    # A SKU can have a valid active PO and an old stale PO at the same
    # time. In that case po_outstanding remains the primary operational
    # state while has_stale_po preserves the stale-PO context.
    # ------------------------------------------------------------------

    if has_active_po:
        po_status = "po_outstanding"

    elif has_overdue_po:
        po_status = "po_overdue"

    elif has_resolving_projected_order:
        po_status = "po_expected"

    elif has_stale_po:
        po_status = "po_stale"

    else:
        po_status = "none"

    return {
        "inventory_status": inventory_status,
        "inventory_urgency": inventory_urgency,
        "po_status": po_status,

        "has_active_po": has_active_po,
        "has_overdue_po": has_overdue_po,
        "has_stale_po": has_stale_po,

        "has_projected_order": (
            has_projected_order
        ),
        "has_resolving_projected_order": (
            has_resolving_projected_order
        ),

        "current_woh": (
            float(current_woh)
            if pd.notna(current_woh)
            else np.nan
        ),

        "days_until_oos": (
            float(days_until_oos)
            if pd.notna(days_until_oos)
            else np.nan
        ),

        "days_of_cushion": (
            float(days_of_cushion)
            if pd.notna(days_of_cushion)
            else np.nan
        ),
    }


# =============================================================================
# 6. NARRATIVE
# =============================================================================

def build_inventory_narrative(
    baseline: dict,
    breaches: dict,
    projected_order_analysis: dict,
    intervention: dict,
    classification: dict,
) -> str:
    """
    Explain the completed inventory assessment in plain English.

    IMPORTANT:
    This function performs no inventory calculations and makes no
    inventory decisions.

    It only narrates facts already established by:
        1. baseline projection
        2. breach analysis
        3. projected-order evaluation
        4. required intervention
        5. classification
    """

    inventory_status = classification["inventory_status"]
    urgency = classification["inventory_urgency"]
    po_status = classification["po_status"]

    has_active_po = classification.get(
        "has_active_po",
        False,
    )
    has_overdue_po = classification.get(
        "has_overdue_po",
        False,
    )
    has_stale_po = classification.get(
        "has_stale_po",
        False,
    )

    current_woh = classification.get(
        "current_woh",
        np.nan,
    )

    confirmed_pos = baseline.get(
        "confirmed_po_events"
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def fmt_date(value):
        if value is None or pd.isna(value):
            return None

        return pd.Timestamp(
            value
        ).strftime("%b %-d")

    def usable_confirmed_pos():
        if (
            confirmed_pos is None
            or confirmed_pos.empty
        ):
            return pd.DataFrame()

        return confirmed_pos[
            confirmed_pos["is_stale"].eq(False)
            & confirmed_pos["receipt_date"].notna()
        ].copy()

    def stale_confirmed_pos():
        if (
            confirmed_pos is None
            or confirmed_pos.empty
        ):
            return pd.DataFrame()

        return confirmed_pos[
            confirmed_pos["is_stale"].eq(True)
        ].copy()

    def confirmed_po_description():
        """
        Describe the next usable confirmed PO without making any
        judgment about whether it solves the inventory problem.
        """

        pos = usable_confirmed_pos()

        if pos.empty:
            return None

        pos = pos.sort_values(
            "receipt_date"
        )

        po = pos.iloc[0]

        cases = float(po["cases"])

        receipt_date = fmt_date(
            po["receipt_date"]
        )

        if po.get("po_status") == "overdue":
            return (
                f"An open {cases:.0f}-case PO is overdue"
            )

        return (
            f"A confirmed {cases:.0f}-case PO is expected "
            f"{receipt_date}"
        )

    # ------------------------------------------------------------------
    # No floor breach
    # ------------------------------------------------------------------

    if not breaches["has_floor_breach"]:

        narrative = (
            f"Inventory is projected to remain above the "
            f"{breaches['floor_weeks']:g}-WOH floor over the "
            "six-week outlook."
        )

        if has_stale_po:
            stale = stale_confirmed_pos()

            if not stale.empty:
                stale_cases = float(
                    stale["cases"].sum()
                )

                narrative += (
                    f" {stale_cases:.0f} cases remain on stale "
                    "open POs and are excluded from the inventory plan."
                )

        return narrative

    # ------------------------------------------------------------------
    # Floor breach, but still inside allowed buffer
    # ------------------------------------------------------------------

    material_breaches = [
        breach
        for breach in intervention["breaches"]
        if breach["breaches_tolerance"]
    ]

    if not material_breaches:

        narrative = (
            f"Inventory is projected to temporarily fall below the "
            f"{breaches['floor_weeks']:g}-WOH floor, but remain within "
            "the allowed buffer."
        )

        if has_stale_po:
            narrative += (
                " Stale open POs are excluded from the inventory plan."
            )

        return narrative

    # ------------------------------------------------------------------
    # Material breaches
    # ------------------------------------------------------------------

    narratives = []

    # ------------------------------------------------------------------
    # Current inventory + confirmed PO context
    # ------------------------------------------------------------------

    if (
        pd.notna(current_woh)
        and current_woh < breaches["floor_weeks"]
    ):
        narratives.append(
            f"Inventory is already below the "
            f"{breaches['floor_weeks']:g}-WOH floor at "
            f"{current_woh:.1f} WOH."
        )

    usable_pos = usable_confirmed_pos()

    if not usable_pos.empty:

        overdue_pos = usable_pos[
            usable_pos["po_status"].eq("overdue")
        ]

        active_pos = usable_pos[
            usable_pos["po_status"].eq("active")
        ]

        total_cases = float(
            usable_pos["cases"].sum()
        )

        # Multiple confirmed POs: explain them together so it is clear
        # they are separate orders.
        if len(usable_pos) > 1:

            po_parts = []

            if not overdue_pos.empty:
                overdue_cases = float(
                    overdue_pos["cases"].sum()
                )

                po_parts.append(
                    f"{overdue_cases:.0f} cases are overdue"
                )

            if not active_pos.empty:
                active_pos = active_pos.sort_values(
                    "receipt_date"
                )

                for _, po in active_pos.iterrows():
                    po_parts.append(
                        f"{float(po['cases']):.0f} cases are expected "
                        f"{fmt_date(po['receipt_date'])}"
                    )

            if po_parts:
                narratives.append(
                    f"Of the {total_cases:.0f} cases currently on PO, "
                    + ", and ".join(po_parts)
                    + "."
                )
        else:
            po = usable_pos.iloc[0]

            po_cases = float(
                po["cases"]
            )

            receipt_date = fmt_date(
                po["receipt_date"]
            )

            if po["po_status"] == "overdue":
                narratives.append(
                    f"A confirmed {po_cases:.0f}-case PO is overdue, "
                    "but confirmed supply does not eliminate the need "
                    "for additional inventory."
                )

            else:
                narratives.append(
                    f"A confirmed {po_cases:.0f}-case PO is expected "
                    f"{receipt_date}, but confirmed supply does not "
                    "eliminate the need for additional inventory."
                )

    for breach in material_breaches:

        action = breach["intervention"]

        action_type = action[
            "intervention_type"
        ]

        breach_date = fmt_date(
            breach.get(
                "first_tolerance_breach_date"
            )
        )

        # --------------------------------------------------------------
        # PROJECTED ORDER RESOLVES THE BREACH
        # --------------------------------------------------------------

        if action_type == "monitor_projected_order":

            order = breach[
                "projected_order"
            ].get(
                "resolving_order"
            )

            if order is not None:

                order_cases = float(
                    order["cases"]
                )

                receipt_date = fmt_date(
                    order.get(
                        "expected_receipt_date"
                    )
                )

                narratives.append(
                    f"Inventory is projected to fall below the "
                    f"acceptable inventory level beginning "
                    f"{breach_date}, but the projected "
                    f"{order_cases:.0f}-case order expected "
                    f"{receipt_date} resolves the gap. "
                    "No additional order is recommended."
                )

            else:
                narratives.append(
                    f"Inventory is projected to fall below the "
                    f"acceptable inventory level beginning "
                    f"{breach_date}, but the projected ordering plan "
                    "resolves the gap. No additional order is "
                    "recommended."
                )

        # --------------------------------------------------------------
        # CONFIRMED PO IS ADEQUATE, BUT NEEDS TO ARRIVE SOONER
        # --------------------------------------------------------------

        elif action_type == "expedite_po":

            po_cases = float(
                action["po_cases"]
            )

            current_receipt = fmt_date(
                action.get(
                    "current_po_receipt_date"
                )
            )

            needed_by = fmt_date(
                action.get(
                    "needed_by_date"
                )
            )

            narratives.append(
                f"Inventory is projected to fall below the "
                f"acceptable inventory level beginning "
                f"{breach_date}. The confirmed "
                f"{po_cases:.0f}-case PO"
                + (
                    f" expected {current_receipt}"
                    if current_receipt
                    else ""
                )
                + " provides enough inventory for this gap, "
                + (
                    f"but it needs to arrive by {needed_by}."
                    if needed_by
                    else "but it needs to arrive sooner."
                )
            )

        # --------------------------------------------------------------
        # NEW ORDER REQUIRED
        # --------------------------------------------------------------

        elif action_type == "new_order":

            recommended_cases = float(
                action["recommended_cases"]
            )

            projected_orders = breach[
                "projected_order"
            ].get(
                "orders",
                [],
            )

            projected_too_late = any(
                order.get("reason") == "arrives_too_late"
                for order in projected_orders
            )

            projected_insufficient = any(
                order.get("reason")
                == "insufficient_to_resolve_breach"
                for order in projected_orders
            )

            # ----------------------------------------------------------
            # Describe the inventory problem.
            #
            # If this is a later breach, make that explicit rather than
            # making it sound like we're describing the current problem
            # again.
            # ----------------------------------------------------------

            breach_index = material_breaches.index(breach)

            if breach_index > 0:
                opening = (
                    f"Even with confirmed supply, inventory is projected "
                    f"to fall below acceptable coverage again beginning "
                    f"{breach_date}."
                )

            elif (
                pd.notna(current_woh)
                and current_woh < breaches["tolerance_weeks"]
            ):
                opening = (
                    f"Inventory is already below the acceptable "
                    f"coverage level at {current_woh:.1f} WOH."
                )

            elif (
                pd.notna(current_woh)
                and current_woh < breaches["floor_weeks"]
            ):
                opening = (
                    f"Inventory is already below the "
                    f"{breaches['floor_weeks']:g}-WOH floor at "
                    f"{current_woh:.1f} WOH."
                )

            else:
                opening = (
                    f"Inventory is projected to fall below the "
                    f"acceptable inventory level beginning "
                    f"{breach_date}."
                )

            parts = [opening]

            # ----------------------------------------------------------
            # Projected distributor orders are secondary context.
            #
            # Confirmed supply is already incorporated into the baseline,
            # so if Function 4 still recommends a new order, we already
            # know confirmed supply does not eliminate this breach.
            # ----------------------------------------------------------

            if projected_orders:

                if projected_insufficient:
                    parts.append(
                        "The distributor's projected ordering plan does "
                        "not provide enough inventory to resolve this gap."
                    )

                elif projected_too_late:
                    parts.append(
                        "The distributor's projected ordering plan is "
                        "expected too late to resolve this gap."
                    )

            parts.append(
                f"{recommended_cases:.0f} additional cases are "
                "recommended."
            )

            narratives.append(
                " ".join(parts)
            )

        # --------------------------------------------------------------
        # FUTURE REPLENISHMENT
        #
        # Deliberately silent. Function 4 has determined that no action
        # needs to surface yet.
        # --------------------------------------------------------------

        elif action_type == "future_replenishment":
            continue

        # --------------------------------------------------------------
        # REVIEW / FALLBACK
        # --------------------------------------------------------------

        else:

            narratives.append(
                f"Inventory requires review for the gap beginning "
                f"{breach_date}."
            )

    # ------------------------------------------------------------------
    # Stale PO context
    #
    # Add once, rather than repeating it for every breach.
    # ------------------------------------------------------------------

    if has_stale_po:

        stale = stale_confirmed_pos()

        if not stale.empty:

            stale_cases = float(
                stale["cases"].sum()
            )

            narratives.append(
                f"{stale_cases:.0f} cases remain on stale open POs "
                "and are excluded from the inventory plan."
            )

    return " ".join(narratives)


# RELEVANCE (REMOVES DCS THAT AREN'T ACTUALLY ORDERING)

def get_inventory_relevance(
    row: pd.Series,
    purchase_orders: pd.DataFrame,
) -> dict:
    """
    Determine whether a DC × SKU is operationally relevant.

    Relevance is distributor-specific because inventory reporting
    differs between KeHE and UNFI.

    KeHE:
    - Presence in the current inventory snapshot establishes relevance.
    - This includes SKUs with zero inventory on hand.

    UNFI:
    - UNFI may report theoretical DC × SKU combinations that are not
      actually active.
    - A combination is relevant if it has any evidence of activity:
        - physical inventory on hand
        - open PO quantity
        - observed sales velocity

    Purchase Orders is the source of truth for open PO quantity.
    """

    distributor = str(
        row.get("distributor", "")
    ).strip().upper()

    qoh_cases = pd.to_numeric(
        row.get("quantity_on_hand_cases", 0),
        errors="coerce",
    )

    velocity_cases_per_week = pd.to_numeric(
        row.get("velocity_cases_per_week", 0),
        errors="coerce",
    )

    qoh_cases = (
        float(qoh_cases)
        if pd.notna(qoh_cases)
        else 0.0
    )

    velocity_cases_per_week = (
        float(velocity_cases_per_week)
        if pd.notna(velocity_cases_per_week)
        else 0.0
    )

    open_po_cases = 0.0

    if (
        purchase_orders is not None
        and not purchase_orders.empty
    ):
        po = purchase_orders[
            (
                purchase_orders["distributor"]
                == row["distributor"]
            )
            & (
                purchase_orders["dc"]
                == row["dc"]
            )
            & (
                purchase_orders["sku"]
                == row["sku"]
            )
        ].copy()

        if not po.empty:
            open_po_cases = pd.to_numeric(
                po["open_quantity_cases"],
                errors="coerce",
            ).fillna(0).clip(lower=0).sum()

    # --------------------------------------------------------------
    # Distributor-specific relevance
    # --------------------------------------------------------------

    if distributor == "KEHE":
        # KeHE only reports DC × SKU combinations present in its
        # inventory snapshot, so the row itself establishes relevance.
        is_relevant = True

    else:
        # UNFI can contain theoretical DC × SKU combinations.
        # Require evidence that the combination is operationally active.
        is_relevant = (
            qoh_cases > 0
            or open_po_cases > 0
            or velocity_cases_per_week > 0
        )

    return {
        "is_relevant": bool(is_relevant),
        "has_positive_velocity": (
            velocity_cases_per_week > 0
        ),
        "quantity_on_hand_cases": qoh_cases,
        "quantity_on_po_cases": float(
            open_po_cases
        ),
        "velocity_cases_per_week": (
            velocity_cases_per_week
        ),
    }
# =============================================================================
# WRAPPER
# =============================================================================

def assess_inventory(
    row: pd.Series,
    purchase_orders: pd.DataFrame,
    expected_orders: pd.DataFrame,
    as_of_date,
    lookahead_days: int = 42,
    floor_weeks: float = 3,
    buffer_weeks: float = 0.5,
    target_weeks: float = 5,
) -> dict:
    """
    Complete inventory outlook.

    1. Build the confirmed-supply baseline.
    2. Identify individual breach episodes.
    3. Evaluate projected orders against each breach.
    4. Determine the appropriate intervention for each breach.
    5. Narrate the resulting breach-level assessment.
    """

    baseline = project_baseline_inventory(
        row=row,
        purchase_orders=purchase_orders,
        as_of_date=as_of_date,
        lookahead_days=lookahead_days,
    )

    breaches = analyze_inventory_breaches(
        baseline=baseline,
        floor_weeks=floor_weeks,
        buffer_weeks=buffer_weeks,
    )

    projected_orders = evaluate_projected_orders(
        row=row,
        baseline=baseline,
        breaches=breaches,
        expected_orders=expected_orders,
    )

    intervention = calculate_required_intervention(
        row=row,
        baseline=baseline,
        breaches=breaches,
        projected_order_analysis=projected_orders,
        target_weeks=target_weeks,
    )

    classification = classify_inventory_assessment(
        row=row,
        baseline=baseline,
        breaches=breaches,
        projected_order_analysis=projected_orders,
        intervention=intervention,
    )

    narrative = build_inventory_narrative(
        baseline=baseline,
        breaches=breaches,
        projected_order_analysis=projected_orders,
        intervention=intervention,
        classification=classification,
    )
    
    skuba_trajectory = project_inventory_with_interventions(
        baseline=baseline,
        breaches=intervention["breaches"],
    )

    return {
        "baseline": baseline,
        "breaches": intervention["breaches"],
        "classification": classification,
        "skuba_trajectory": skuba_trajectory,
        "narrative": narrative,
    }


def project_inventory_with_interventions(
    baseline: dict,
    breaches: list[dict],
) -> pd.DataFrame:
    """
    Project inventory assuming SKUba's active interventions
    are followed.

    Intervention decisions have already been made.
    This function only converts those decisions into supply-event
    changes and passes them to the shared trajectory projector.
    """

    trajectory = baseline["trajectory"]

    if trajectory.empty:
        return trajectory.copy()

    start_date = pd.Timestamp(
        baseline["as_of_date"]
    ).normalize()

    end_date = pd.Timestamp(
        trajectory["date"].max()
    ).normalize()

    start_inventory_cases = float(
        baseline["estimated_cases_today"]
    )

    velocity_cases_per_week = float(
        baseline["velocity_cases_per_week"]
    )

    # Start with exactly the confirmed supply used
    # by the baseline.
    confirmed_po_events = (
        baseline["confirmed_po_events"]
        .copy()
    )

    supply_events = (
        confirmed_po_events[
            confirmed_po_events[
                "receipt_date"
            ].notna()
            & confirmed_po_events[
                "is_stale"
            ].eq(False)
            & (
                confirmed_po_events[
                    "receipt_date"
                ]
                > start_date
            )
        ][
            [
                "receipt_date",
                "cases",
            ]
        ]
        .copy()
        .reset_index(drop=True)
    )

    # Apply only interventions already chosen by
    # calculate_required_intervention().
    for breach in breaches:
        intervention = (
            breach.get(
                "intervention"
            )
            or {}
        )

        if not intervention.get(
            "intervention_required"
        ):
            continue

        intervention_type = (
            intervention.get(
                "intervention_type"
            )
        )

        if (
            intervention_type
            == "new_order"
        ):
            cases = float(
                intervention[
                    "recommended_cases"
                ]
            )

            delivery_date = (
                pd.Timestamp(
                    intervention[
                        "expected_delivery_date"
                    ]
                ).normalize()
            )

            supply_events = pd.concat(
                [
                    supply_events,
                    pd.DataFrame(
                        [
                            {
                                "receipt_date":
                                    delivery_date,
                                "cases":
                                    cases,
                            }
                        ]
                    ),
                ],
                ignore_index=True,
            )

        elif intervention_type == "expedite_po":
            # Expedite is an operational recommendation, not a confirmed
            # change to the PO's receipt date.
            #
            # Keep the PO on its currently expected receipt date in the
            # modeled trajectory. We cannot assume that following up on
            # the PO will cause it to arrive by the needed-by date.
            continue

    return project_inventory_trajectory(
        start_date=start_date,
        end_date=end_date,
        start_inventory_cases=(
            start_inventory_cases
        ),
        velocity_cases_per_week=(
            velocity_cases_per_week
        ),
        supply_events=supply_events,
    )

# =============================================================================
# LOCAL TEST — GRW STRAWBERRY
# =============================================================================

if __name__ == "__main__":
    from pathlib import Path

    from backend.metrics.inventory.expected_orders import (
        build_kehe_expected_order_events,
        build_unfi_expected_order_events,
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

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)

    # ------------------------------------------------------------------
    # Inputs
    # ------------------------------------------------------------------

    org_id = "default_org"
    org_dir = Path("backend/data") / org_id

    # Use the date we're currently debugging.
    as_of_date = pd.Timestamp("2026-09-16")

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
    # Find GRW Strawberry
    # ------------------------------------------------------------------

    inventory["report_date"] = pd.to_datetime(
        inventory["report_date"],
        errors="coerce",
    )

    strawberry = inventory[
        (inventory["distributor"] == "UNFI")
        & (inventory["dc"] == "GRW")
        & (inventory["sku"] == "STRAWBERRY")
    ].copy()

    if strawberry.empty:
        raise ValueError(
            "Could not find UNFI / GRW / STRAWBERRY "
            "in inventory_features_test.csv"
        )

    # Use latest inventory observation.
    strawberry = (
        strawberry
        .sort_values("report_date")
        .iloc[-1]
        .copy()
    )

    # ------------------------------------------------------------------
    # Lead time
    # ------------------------------------------------------------------

    lead_times = calculate_replenishment_lead_time(
        inventory
    )

    dc_lead_time = lead_times[
        (lead_times["distributor"] == "UNFI")
        & (lead_times["dc"] == "GRW")
    ]

    if dc_lead_time.empty:
        raise ValueError(
            "Could not calculate a replenishment lead time "
            "for UNFI / GRW."
        )

    lead_days = pd.to_numeric(
        dc_lead_time.iloc[0]["median_replenishment_days"],
        errors="coerce",
    )

    if pd.isna(lead_days):
        raise ValueError(
            "GRW median replenishment lead time is missing."
        )

    strawberry["planning_lead_time_days"] = float(lead_days)

    # ------------------------------------------------------------------
    # Run the five stages separately.
    # ------------------------------------------------------------------

    baseline = project_baseline_inventory(
        row=strawberry,
        purchase_orders=purchase_orders,
        as_of_date=as_of_date,
        lookahead_days=42,
    )

    breaches = analyze_inventory_breaches(
        baseline=baseline,
        floor_weeks=3,
        buffer_weeks=0.5,
    )

    projected_order_analysis = evaluate_projected_orders(
        row=strawberry,
        baseline=baseline,
        breaches=breaches,
        expected_orders=expected_orders,
    )

    intervention = calculate_required_intervention(
        row=strawberry,
        baseline=baseline,
        breaches=breaches,
        projected_order_analysis=projected_order_analysis,
        target_weeks=5,
    )
    

    narrative = build_inventory_narrative(
        baseline=baseline,
        breaches=breaches,
        projected_order_analysis=projected_order_analysis,
        intervention=intervention,
    )

    # ------------------------------------------------------------------
    # Print inputs
    # ------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("GRW STRAWBERRY — INPUTS")
    print("=" * 80)

    print("As of date:             ", as_of_date.date())
    print("Inventory report date:  ", baseline["report_date"].date())
    print("Observed QOH:           ", baseline["observed_cases"])
    print(
        "Estimated QOH today:    ",
        round(baseline["estimated_cases_today"], 2),
    )
    print(
        "Velocity cases/week:    ",
        round(baseline["velocity_cases_per_week"], 2),
    )
    print(
        "Planning lead time:     ",
        strawberry["planning_lead_time_days"],
        "days",
    )

    # ------------------------------------------------------------------
    # 1. Baseline
    # ------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("1. BASELINE — CONFIRMED SUPPLY ONLY")
    print("=" * 80)

    confirmed_pos = baseline["confirmed_po_events"]

    print("\nCONFIRMED PO EVENTS")

    if confirmed_pos.empty:
        print("None")
    else:
        print(confirmed_pos.to_string(index=False))

    print("\nDAILY TRAJECTORY")

    print(
        baseline["trajectory"][
            [
                "date",
                "inventory_cases",
                "weeks_on_hand",
                "inbound_cases",
            ]
        ].to_string(
            index=False,
            formatters={
                "inventory_cases": lambda x: f"{x:.2f}",
                "weeks_on_hand": lambda x: f"{x:.2f}",
                "inbound_cases": lambda x: f"{x:.0f}",
            },
        )
    )

    # ------------------------------------------------------------------
    # 2. Breaches
    # ------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("2. BREACH ANALYSIS")
    print("=" * 80)

    print("Floor:                 ", breaches["floor_weeks"], "WOH")
    print("Buffer:                ", breaches["buffer_weeks"], "WOH")
    print(
        "Tolerance threshold:   ",
        breaches["tolerance_weeks"],
        "WOH",
    )

    print("Has floor breach:      ", breaches["has_floor_breach"])
    print(
        "First floor breach:    ",
        breaches["first_floor_breach_date"],
    )

    print(
        "Has tolerance breach:  ",
        breaches["has_tolerance_breach"],
    )
    print(
        "First tolerance breach:",
        breaches["first_tolerance_breach_date"],
    )

    print("Has OOS:               ", breaches["has_oos"])
    print("First OOS:             ", breaches["first_oos_date"])

    print(
        "Lowest WOH:            ",
        round(breaches["lowest_woh"], 2),
    )
    print(
        "Lowest WOH date:       ",
        breaches["lowest_woh_date"],
    )

    print("\nBREACH EPISODES")

    if not breaches["episodes"]:
        print("None")
    else:
        for i, episode in enumerate(
            breaches["episodes"],
            start=1,
        ):
            print(f"\nEpisode {i}")

            for key, value in episode.items():
                print(f"  {key}: {value}")

    # ------------------------------------------------------------------
    # 3. Projected orders
    # ------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("3. PROJECTED ORDER ANALYSIS")
    print("=" * 80)

    print(
        "Projected order exists:",
        projected_order_analysis["projected_order_exists"],
    )

    for i, breach in enumerate(
        projected_order_analysis["breaches"],
        start=1,
    ):
        print(f"\nBreach {i}")
        print(
            "  start_date:",
            breach["start_date"],
        )
        print(
            "  first_tolerance_breach_date:",
            breach["first_tolerance_breach_date"],
        )

        projected = breach["projected_order"]

        print(
            "  resolves_breach:",
            projected["resolves_breach"],
        )
        print(
            "  reason:",
            projected["reason"],
        )

        print("  projected_orders_tested:")

        if not projected["orders"]:
            print("    None")
        else:
            for order in projected["orders"]:
                print("   ", order)

    # ------------------------------------------------------------------
    # 4. Intervention
    # ------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("4. REQUIRED INTERVENTION")
    print("=" * 80)

    for i, breach in enumerate(
        intervention["breaches"],
        start=1,
    ):
        print(f"\nBreach {i}")
        print("  start_date:", breach["start_date"])
        print(
            "  first_tolerance_breach_date:",
            breach["first_tolerance_breach_date"],
        )

        print("  intervention:")

        for key, value in breach["intervention"].items():
            print(f"    {key}: {value}")

    # ------------------------------------------------------------------
    # 5. Narrative
    # ------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("5. NARRATIVE")
    print("=" * 80)

    print(narrative)

    print("\n" + "=" * 80)

import math
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from backend.insights.inventory.order_assessment_3 import (
    assess_inventory,
    get_inventory_relevance,
)
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
from backend.forecasting.inventory_projection import (
    _evidence_window_end
)

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
)

BASE_DATA_DIR = Path("backend/data")


# =============================================================================
# JSON HELPERS
# =============================================================================


def _safe_float(value):
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    return float(value)


def _safe_int(value):
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    return int(value)


def _safe_date(value):
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    return pd.Timestamp(value).strftime("%Y-%m-%d")


def _json_safe(value):
    """
    Recursively convert pandas / numpy objects into JSON-safe Python values.
    """

    if value is None:
        return None

    if isinstance(value, pd.DataFrame):
        return [
            _json_safe(record)
            for record in value.to_dict(orient="records")
        ]

    if isinstance(value, pd.Series):
        return _json_safe(value.to_dict())

    if isinstance(value, dict):
        return {
            key: _json_safe(val)
            for key, val in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            _json_safe(val)
            for val in value
        ]

    if isinstance(value, pd.Timestamp):
        return (
            None
            if pd.isna(value)
            else value.strftime("%Y-%m-%d")
        )

    if isinstance(value, np.datetime64):
        if np.isnat(value):
            return None

        return pd.Timestamp(value).strftime("%Y-%m-%d")

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        return (
            None
            if pd.isna(value)
            else float(value)
        )

    if isinstance(value, np.bool_):
        return bool(value)

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    return value


# =============================================================================
# INPUT LOADING
# =============================================================================


def _empty_purchase_orders() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "distributor",
            "dc",
            "sku",
            "open_quantity_cases",
            "po_create_date",
            "delivery_appointment_date",
            "revised_eta_date",
            "original_eta_date",
        ]
    )


def _empty_expected_orders() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "org_id",
            "distributor",
            "dc",
            "sku",
            "expected_order_date",
            "expected_order_units",
            "expected_order_cases",
            "source",
            "confidence",
        ]
    )


def _load_inventory_inputs(
    org_dir: Path,
    org_id: str,
):
    """
    Load the raw / processed inputs required by the inventory engine.

    This function performs no inventory assessment.
    """

    inventory_features_path = (
        org_dir
        / "inventory_features_test.csv"
    )

    inventory_history_path = (
        org_dir
        / "inventory_combined.parquet"
    )

    if not inventory_features_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Inventory features not found.",
        )

    if not inventory_history_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Inventory history not found.",
        )

    inventory_features = pd.read_csv(
        inventory_features_path
    )

    inventory_history = pd.read_parquet(
        inventory_history_path
    )

    # ------------------------------------------------------------------
    # Confirmed / open POs
    # ------------------------------------------------------------------

    purchase_orders = _empty_purchase_orders()

    unfi_po_path = (
        org_dir
        / "raw"
        / "inventory"
        / "unfi"
        / "Purchase Orders.csv"
    )

    if unfi_po_path.exists():
        purchase_orders = (
            transform_unfi_purchase_orders(
                pd.read_csv(unfi_po_path),
                org_id=org_id,
            )
        )

        purchase_orders = purchase_orders[
            purchase_orders["po_status"]
            .astype(str)
            .str.upper()
            .eq("OPEN")
        ].copy()

    # ------------------------------------------------------------------
    # Distributor projected / expected orders
    # ------------------------------------------------------------------

    expected_frames = []

    unfi_projection_path = (
        org_dir
        / "raw"
        / "inventory"
        / "unfi"
        / "Projected Orders Detail.csv"
    )

    if unfi_projection_path.exists():
        unfi_projected_orders = (
            transform_unfi_projected_orders(
                pd.read_csv(
                    unfi_projection_path
                ),
                org_id=org_id,
            )
        )

        expected_frames.append(
            build_unfi_expected_order_events(
                unfi_projected_orders
            )
        )

    kehe_projection_path = (
        org_dir
        / "raw"
        / "inventory"
        / "kehe"
        / "Order Projections Report.csv"
    )

    if kehe_projection_path.exists():
        kehe_projected_orders = (
            transform_kehe_order_projections(
                pd.read_csv(
                    kehe_projection_path
                ),
                org_id=org_id,
            )
        )

        expected_frames.append(
            build_kehe_expected_order_events(
                kehe_projected_orders
            )
        )

    expected_orders = (
        pd.concat(
            expected_frames,
            ignore_index=True,
        )
        if expected_frames
        else _empty_expected_orders()
    )

    return (
        inventory_features,
        inventory_history,
        expected_orders,
        purchase_orders,
    )


# =============================================================================
# INVENTORY ENGINE
# =============================================================================


def _latest_inventory_rows(
    inventory: pd.DataFrame,
) -> pd.DataFrame:
    """
    Return the latest inventory observation for every
    distributor × DC × SKU.
    """

    df = inventory.copy()

    df["report_date"] = pd.to_datetime(
        df["report_date"],
        errors="coerce",
    )

    return (
        df
        .sort_values("report_date")
        .groupby(
            [
                "distributor",
                "dc",
                "sku",
            ],
            as_index=False,
        )
        .tail(1)
        .reset_index(drop=True)
    )


def _build_lead_time_lookup(
    inventory: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build the observed replenishment lead-time lookup used by
    the inventory engine.
    """

    lead_times = (
        calculate_replenishment_lead_time(
            inventory
        )
        .copy()
    )

    if (
        "median_replenishment_days"
        in lead_times.columns
    ):
        lead_times[
            "median_replenishment_days"
        ] = pd.to_numeric(
            lead_times[
                "median_replenishment_days"
            ],
            errors="coerce",
        )

    return lead_times


def _get_velocity_cases_per_week(
    row: pd.Series,
) -> float | None:
    """
    Derive cases/week from the same source fields used by the
    inventory engine.
    """

    units_per_week = pd.to_numeric(
        row.get("dc_weekly_velocity"),
        errors="coerce",
    )

    units_per_case = pd.to_numeric(
        row.get("units_per_case"),
        errors="coerce",
    )

    if (
        pd.isna(units_per_week)
        or pd.isna(units_per_case)
        or units_per_case <= 0
    ):
        return None

    return float(
        units_per_week
        / units_per_case
    )


def _get_raw_expected_orders(
    row: pd.Series,
    expected_orders: pd.DataFrame,
) -> list:
    if (
        expected_orders is None
        or expected_orders.empty
    ):
        return []

    match = expected_orders[
        (
            expected_orders["distributor"]
            == row["distributor"]
        )
        & (
            expected_orders["dc"]
            == row["dc"]
        )
        & (
            expected_orders["sku"]
            == row["sku"]
        )
    ].copy()

    if match.empty:
        return []

    if "expected_order_date" in match.columns:
        match["expected_order_date"] = (
            pd.to_datetime(
                match["expected_order_date"],
                errors="coerce",
            )
        )

        match = match.sort_values(
            "expected_order_date"
        )

    return _json_safe(
        match.to_dict(
            orient="records"
        )
    )


def _get_raw_purchase_orders(
    row: pd.Series,
    purchase_orders: pd.DataFrame,
) -> list:
    if (
        purchase_orders is None
        or purchase_orders.empty
    ):
        return []

    match = purchase_orders[
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

    if match.empty:
        return []

    return _json_safe(
        match.to_dict(
            orient="records"
        )
    )


def _derive_inventory_status(
    assessment: dict,
) -> dict:
    """
    Create a compact SKU-level summary from the breach-level engine.

    This does not change engine decisions. It only summarizes them
    for overview / DC-level API consumers.
    """

    breaches = assessment["breaches"]

    material_breaches = [
        breach
        for breach in breaches
        if breach.get(
            "breaches_tolerance"
        )
    ]

    interventions = [
        breach.get(
            "intervention",
            {}
        )
        for breach in material_breaches
    ]

    intervention_types = [
        intervention.get(
            "intervention_type"
        )
        for intervention in interventions
        if intervention.get(
            "intervention_type"
        )
    ]

    # future_replenishment is intentionally not an active
    # user-facing recommendation yet.
    active_interventions = [
        intervention
        for intervention in interventions
        if intervention.get(
            "intervention_type"
        )
        not in {
            None,
            "none",
            "future_replenishment",
            "monitor_projected_order",
        }
    ]

    monitor_projected = any(
        intervention.get(
            "intervention_type"
        )
        == "monitor_projected_order"
        for intervention in interventions
    )

    future_replenishment = any(
        intervention.get(
            "intervention_type"
        )
        == "future_replenishment"
        for intervention in interventions
    )

    has_floor_breach = bool(
        breaches
    )

    has_material_breach = bool(
        material_breaches
    )

    if active_interventions:
        status = "action"

    elif monitor_projected:
        status = "monitor"

    elif has_material_breach:
        # This is normally a future replenishment outside its
        # recommendation window.
        status = "monitor"

    elif has_floor_breach:
        # Below floor but still inside allowed buffer.
        status = "monitor"

    else:
        status = "healthy"

    recommended_cases = sum(
        float(
            intervention.get(
                "recommended_cases",
                0,
            )
        )
        for intervention in active_interventions
        if pd.notna(
            intervention.get(
                "recommended_cases",
                0,
            )
        )
    )

    has_review = any(
        intervention.get(
            "intervention_type"
        )
        == "review"
        for intervention in interventions
    )

    has_expedite = any(
        intervention.get(
            "intervention_type"
        )
        == "expedite_po"
        for intervention in interventions
    )

    has_new_order = any(
        intervention.get(
            "intervention_type"
        )
        == "new_order"
        for intervention in interventions
    )

    return {
        "status": status,
        "intervention_types": (
            intervention_types
        ),
        "active_intervention_types": [
            intervention.get(
                "intervention_type"
            )
            for intervention
            in active_interventions
        ],
        "recommended_cases": (
            recommended_cases
        ),
        "has_active_action": bool(
            active_interventions
        ),
        "has_review": has_review,
        "has_expedite": has_expedite,
        "has_new_order": has_new_order,
        "monitor_projected_order": (
            monitor_projected
        ),
        "future_replenishment": (
            future_replenishment
        ),
        "has_floor_breach": (
            has_floor_breach
        ),
        "has_material_breach": (
            has_material_breach
        ),
    }


def _build_projection_unavailable(
    row: pd.Series,
    relevance: dict,
    lead_time: dict | None,
    purchase_orders: pd.DataFrame,
    expected_orders: pd.DataFrame,
) -> dict:
    """
    Preserve operationally relevant inventory that cannot be
    projected because positive velocity is unavailable.
    """

    velocity_cases = (
        _get_velocity_cases_per_week(
            row
        )
    )

    return {
        "distributor": row["distributor"],
        "dc": row["dc"],
        "sku": row["sku"],
        "product_name": row["sku"],

        "assessment_status": (
            "projection_unavailable"
        ),
        "inventory_status": (
            "projection_unavailable"
        ),

        "projection_available": False,
        "projection_unavailable_reason": (
            "positive_velocity_unavailable"
        ),

        "report_date": _safe_date(
            row.get("report_date")
        ),

        "observed_quantity_on_hand_cases": (
            relevance[
                "quantity_on_hand_cases"
            ]
        ),

        "observed_quantity_on_po_cases": (
            relevance[
                "quantity_on_po_cases"
            ]
        ),

        "velocity_cases_per_week": (
            velocity_cases
        ),

        "units_per_case": _safe_float(
            row.get("units_per_case")
        ),

        "planning_lead_time_days": (
            None
            if lead_time is None
            else lead_time.get(
                "lead_time_days"
            )
        ),

        "planning_lead_time_source": (
            None
            if lead_time is None
            else lead_time.get(
                "lead_time_source"
            )
        ),

        "summary": {
            "status": (
                "projection_unavailable"
            ),
            "intervention_types": [],
            "active_intervention_types": [],
            "recommended_cases": 0,
            "has_active_action": False,
            "has_review": True,
            "has_expedite": False,
            "has_new_order": False,
            "monitor_projected_order": False,
            "future_replenishment": False,
            "has_floor_breach": None,
            "has_material_breach": None,
        },

        "narrative": (
            "Inventory exists for this SKU, "
            "but a forward projection cannot "
            "be calculated because positive "
            "velocity is unavailable."
        ),

        "baseline": None,
        "breaches": [],

        "raw_purchase_orders": (
            _get_raw_purchase_orders(
                row=row,
                purchase_orders=(
                    purchase_orders
                ),
            )
        ),

        "raw_projected_orders": (
            _get_raw_expected_orders(
                row=row,
                expected_orders=(
                    expected_orders
                ),
            )
        ),
    }


def _build_assessment_record(
    row: pd.Series,
    relevance: dict,
    lead_time: dict,
    assessment: dict,
    purchase_orders: pd.DataFrame,
    expected_orders: pd.DataFrame,
) -> dict:
    """
    Convert one successful inventory-engine assessment into the
    canonical API record.
    """

    baseline = assessment["baseline"]

    summary = _derive_inventory_status(
        assessment
    )

    # --------------------------------------------------------------
    # Chart evidence window
    # --------------------------------------------------------------

    baseline_trajectory = baseline["trajectory"]

    skuba_trajectory = assessment.get(
        "skuba_trajectory"
    )

    floor_cases = (
        baseline["velocity_cases_per_week"] * 3
    )

    # Use the first material breach as the floor/risk date.
    material_breaches = [
        breach
        for breach in assessment["breaches"]
        if breach.get("breaches_tolerance")
    ]

    floor_date = (
        material_breaches[0].get(
            "first_tolerance_breach_date"
        )
        if material_breaches
        else None
    )

    # Find the first active new-order recommendation.
    recommendation_event = None

    for breach in material_breaches:
        intervention = breach.get(
            "intervention",
            {},
        )

        if (
            intervention.get(
                "intervention_type"
            ) == "new_order"
            and intervention.get(
                "intervention_required"
            )
        ):
            recommendation_event = intervention
            break

    # Convert confirmed PO events into the shape expected by
    # _evidence_window_end().
    current_path_inbounds = []

    confirmed_po_events = baseline.get(
        "confirmed_po_events"
    )

    if (
        confirmed_po_events is not None
        and not confirmed_po_events.empty
    ):
        for _, event in confirmed_po_events.iterrows():
            if event.get("is_stale"):
                continue

            event_date = event.get(
                "receipt_date"
            )

            if pd.isna(event_date):
                continue

            current_path_inbounds.append({
                "date": event_date,
                "cases": event.get(
                    "cases",
                    0,
                ),
            })

    current_path_inbounds.sort(
        key=lambda event: pd.Timestamp(
            event["date"]
        )
    )

    evidence_window_end = _evidence_window_end(
        as_of_date=baseline["as_of_date"],
        floor_date=floor_date,
        status=summary["status"],
        recommendation_event=recommendation_event,
        current_path_inbounds=current_path_inbounds,
        floor_cases=floor_cases,
        current_cases=baseline[
            "estimated_cases_today"
        ],
        velocity_cases_per_week=baseline[
            "velocity_cases_per_week"
        ],
    )

    baseline_trajectory = baseline_trajectory[
        pd.to_datetime(
            baseline_trajectory["date"]
        ).dt.normalize()
        <= evidence_window_end
    ].copy()

    if (
        skuba_trajectory is not None
        and not skuba_trajectory.empty
    ):
        skuba_trajectory = skuba_trajectory[
            pd.to_datetime(
                skuba_trajectory["date"]
            ).dt.normalize()
            <= evidence_window_end
        ].copy()

    velocity_units = pd.to_numeric(
        row.get("dc_weekly_velocity"),
        errors="coerce",
    )

    units_per_case = pd.to_numeric(
        row.get("units_per_case"),
        errors="coerce",
    )

    velocity_cases = (
        baseline[
            "velocity_cases_per_week"
        ]
    )

    estimated_cases_today = (
        baseline[
            "estimated_cases_today"
        ]
    )

    estimated_woh_today = (
        estimated_cases_today
        / velocity_cases
        if velocity_cases > 0
        else None
    )

    return {
        "distributor": row["distributor"],
        "dc": row["dc"],
        "sku": row["sku"],
        "product_name": row["sku"],

        "assessment_status": "available",
        "inventory_status": (
            summary["status"]
        ),
        "projection_available": True,
        "projection_unavailable_reason": None,

        # --------------------------------------------------------------
        # Current inventory state
        # --------------------------------------------------------------

        "as_of_date": _safe_date(
            baseline["as_of_date"]
        ),

        "report_date": _safe_date(
            baseline["report_date"]
        ),

        "observed_quantity_on_hand_cases": (
            _safe_float(
                baseline[
                    "observed_cases"
                ]
            )
        ),

        "estimated_quantity_on_hand_cases": (
            _safe_float(
                estimated_cases_today
            )
        ),

        "estimated_weeks_on_hand": (
            _safe_float(
                estimated_woh_today
            )
        ),

        "quantity_on_po_cases": (
            _safe_float(
                relevance[
                    "quantity_on_po_cases"
                ]
            )
        ),

        # --------------------------------------------------------------
        # Velocity / case pack
        # --------------------------------------------------------------

        "units_per_case": _safe_float(
            units_per_case
        ),

        "units_per_week": _safe_float(
            velocity_units
        ),

        "cases_per_week": _safe_float(
            velocity_cases
        ),

        # --------------------------------------------------------------
        # Planning parameters
        # --------------------------------------------------------------

        "planning_lead_time_days": (
            _safe_float(
                lead_time[
                    "lead_time_days"
                ]
            )
        ),

        "planning_lead_time_source": (
            lead_time[
                "lead_time_source"
            ]
        ),

        # --------------------------------------------------------------
        # Compact frontend summary
        # --------------------------------------------------------------

        "summary": summary,

        # --------------------------------------------------------------
        # Narrative
        # --------------------------------------------------------------

        "narrative": (
            assessment["narrative"]
        ),

        # --------------------------------------------------------------
        # Full engine output
        #
        # The frontend can choose what it wants to display without
        # reproducing inventory logic.
        # --------------------------------------------------------------

        "baseline": {
            "as_of_date": (
                baseline["as_of_date"]
            ),

            "report_date": (
                baseline["report_date"]
            ),

            "observed_cases": (
                baseline["observed_cases"]
            ),

            "estimated_cases_today": (
                baseline[
                    "estimated_cases_today"
                ]
            ),

            "velocity_cases_per_week": (
                baseline[
                    "velocity_cases_per_week"
                ]
            ),

            "confirmed_po_events": (
                baseline[
                    "confirmed_po_events"
                ]
            ),

            "trajectory": (
                baseline_trajectory
            ),
        },

        "skuba_trajectory": (
            skuba_trajectory
        ),

        "breaches": assessment[
            "breaches"
        ],

        # --------------------------------------------------------------
        # Raw source records
        #
        # Useful for future frontend detail views and debugging without
        # requiring another backend calculation path.
        # --------------------------------------------------------------

        "raw_purchase_orders": (
            _get_raw_purchase_orders(
                row=row,
                purchase_orders=(
                    purchase_orders
                ),
            )
        ),

        "raw_projected_orders": (
            _get_raw_expected_orders(
                row=row,
                expected_orders=(
                    expected_orders
                ),
            )
        ),
    }


def _run_inventory_engine(
    inventory_features: pd.DataFrame,
    purchase_orders: pd.DataFrame,
    expected_orders: pd.DataFrame,
    as_of_date=None,
) -> list[dict]:
    """
    Run the new inventory engine across every operationally relevant
    distributor × DC × SKU.

    This is the single source of truth for all inventory API endpoints.
    """

    if as_of_date is None:
        as_of_date = (
            pd.Timestamp.today()
            .normalize()
        )
    else:
        as_of_date = (
            pd.Timestamp(as_of_date)
            .normalize()
        )

    latest_inventory = (
        _latest_inventory_rows(
            inventory_features
        )
    )

    lead_times = (
        _build_lead_time_lookup(
            inventory_features
        )
    )

    results = []

    for _, inventory_row in (
        latest_inventory.iterrows()
    ):
        row = inventory_row.copy()

        relevance = (
            get_inventory_relevance(
                row=row,
                purchase_orders=(
                    purchase_orders
                ),
            )
        )

        if not relevance[
            "is_relevant"
        ]:
            continue

        # --------------------------------------------------------------
        # Resolve planning lead time
        # --------------------------------------------------------------

        lead_time = (
            resolve_replenishment_lead_time(
                distributor=(
                    row["distributor"]
                ),
                dc=row["dc"],
                lead_times=lead_times,
            )
        )

        lead_days = lead_time.get(
            "lead_time_days"
        )

        # --------------------------------------------------------------
        # Relevant inventory with no usable velocity is preserved,
        # but cannot run through the projection engine.
        # --------------------------------------------------------------

        velocity_cases = (
            _get_velocity_cases_per_week(
                row
            )
        )

        if (
            velocity_cases is None
            or velocity_cases <= 0
        ):
            results.append(
                _build_projection_unavailable(
                    row=row,
                    relevance=relevance,
                    lead_time=lead_time,
                    purchase_orders=(
                        purchase_orders
                    ),
                    expected_orders=(
                        expected_orders
                    ),
                )
            )

            continue

        # --------------------------------------------------------------
        # Missing lead time also prevents a valid projection.
        # --------------------------------------------------------------

        if lead_days is None:
            unavailable = (
                _build_projection_unavailable(
                    row=row,
                    relevance=relevance,
                    lead_time=lead_time,
                    purchase_orders=(
                        purchase_orders
                    ),
                    expected_orders=(
                        expected_orders
                    ),
                )
            )

            unavailable[
                "projection_unavailable_reason"
            ] = "missing_lead_time"

            unavailable[
                "narrative"
            ] = (
                "Inventory is operationally "
                "relevant, but a forward "
                "projection cannot be calculated "
                "because replenishment lead time "
                "is unavailable."
            )

            results.append(
                unavailable
            )

            continue

        # --------------------------------------------------------------
        # Supply the resolved planning lead time to Functions 1–5.
        # --------------------------------------------------------------

        row[
            "planning_lead_time_days"
        ] = float(lead_days)

        row[
            "planning_lead_time_source"
        ] = lead_time.get(
            "lead_time_source"
        )

        # --------------------------------------------------------------
        # Run canonical inventory assessment.
        # --------------------------------------------------------------

        try:
            assessment = (
                assess_inventory(
                    row=row,
                    purchase_orders=(
                        purchase_orders
                    ),
                    expected_orders=(
                        expected_orders
                    ),
                    as_of_date=(
                        as_of_date
                    ),
                    lookahead_days=42,
                    floor_weeks=3,
                    buffer_weeks=0.5,
                    target_weeks=5,
                )
            )

        except ValueError as exc:
            results.append({
                "distributor": (
                    row["distributor"]
                ),
                "dc": row["dc"],
                "sku": row["sku"],
                "product_name": (
                    row["sku"]
                ),

                "assessment_status": (
                    "projection_unavailable"
                ),
                "inventory_status": (
                    "projection_unavailable"
                ),
                "projection_available": (
                    False
                ),
                "projection_unavailable_reason": (
                    str(exc)
                ),

                "report_date": _safe_date(
                    row.get(
                        "report_date"
                    )
                ),

                "observed_quantity_on_hand_cases": (
                    relevance[
                        "quantity_on_hand_cases"
                    ]
                ),

                "quantity_on_po_cases": (
                    relevance[
                        "quantity_on_po_cases"
                    ]
                ),

                "planning_lead_time_days": (
                    _safe_float(
                        lead_days
                    )
                ),

                "planning_lead_time_source": (
                    lead_time.get(
                        "lead_time_source"
                    )
                ),

                "summary": {
                    "status": (
                        "projection_unavailable"
                    ),
                    "intervention_types": [],
                    "active_intervention_types": [],
                    "recommended_cases": 0,
                    "has_active_action": False,
                    "has_review": True,
                    "has_expedite": False,
                    "has_new_order": False,
                    "monitor_projected_order": False,
                    "future_replenishment": False,
                    "has_floor_breach": None,
                    "has_material_breach": None,
                },

                "narrative": (
                    "Inventory projection is "
                    f"unavailable: {exc}"
                ),

                "baseline": None,
                "breaches": [],

                "raw_purchase_orders": (
                    _get_raw_purchase_orders(
                        row=row,
                        purchase_orders=(
                            purchase_orders
                        ),
                    )
                ),

                "raw_projected_orders": (
                    _get_raw_expected_orders(
                        row=row,
                        expected_orders=(
                            expected_orders
                        ),
                    )
                ),
            })

            continue

        results.append(
            _build_assessment_record(
                row=row,
                relevance=relevance,
                lead_time=lead_time,
                assessment=assessment,
                purchase_orders=(
                    purchase_orders
                ),
                expected_orders=(
                    expected_orders
                ),
            )
        )

    return _json_safe(results)


def _load_and_assess_inventory(
    org_dir: Path,
    org_id: str,
    as_of_date=None,
):
    """
    Load inventory inputs and run the canonical inventory engine.
    """

    (
        inventory_features,
        inventory_history,
        expected_orders,
        purchase_orders,
    ) = _load_inventory_inputs(
        org_dir=org_dir,
        org_id=org_id,
    )

    assessments = (
        _run_inventory_engine(
            inventory_features=(
                inventory_features
            ),
            purchase_orders=(
                purchase_orders
            ),
            expected_orders=(
                expected_orders
            ),
            as_of_date=as_of_date,
        )
    )

    return (
        assessments,
        inventory_features,
        inventory_history,
        expected_orders,
        purchase_orders,
    )


# =============================================================================
# DC SUMMARY
# =============================================================================


def _build_dc_summary(
    dc_inventory: list[dict],
) -> dict:
    """
    Aggregate SKU-level engine outputs into one DC summary.
    """

    if not dc_inventory:
        return {}

    distributor = (
        dc_inventory[0][
            "distributor"
        ]
    )

    dc = dc_inventory[0]["dc"]

    actionable = [
        row
        for row in dc_inventory
        if row.get(
            "summary",
            {}
        ).get(
            "has_active_action",
            False,
        )
    ]

    monitoring = [
        row
        for row in dc_inventory
        if row.get(
            "inventory_status"
        )
        == "monitor"
    ]

    healthy = [
        row
        for row in dc_inventory
        if row.get(
            "inventory_status"
        )
        == "healthy"
    ]

    unavailable = [
        row
        for row in dc_inventory
        if not row.get(
            "projection_available",
            False,
        )
    ]

    review = [
        row
        for row in dc_inventory
        if row.get(
            "summary",
            {}
        ).get(
            "has_review",
            False,
        )
    ]

    expedite = [
        row
        for row in dc_inventory
        if row.get(
            "summary",
            {}
        ).get(
            "has_expedite",
            False,
        )
    ]

    new_orders = [
        row
        for row in dc_inventory
        if row.get(
            "summary",
            {}
        ).get(
            "has_new_order",
            False,
        )
    ]

    projected_order_monitors = [
        row
        for row in dc_inventory
        if row.get(
            "summary",
            {}
        ).get(
            "monitor_projected_order",
            False,
        )
    ]

    recommended_cases = sum(
        float(
            row.get(
                "summary",
                {},
            ).get(
                "recommended_cases",
                0,
            )
            or 0
        )
        for row in dc_inventory
    )

    return {
        "distributor": distributor,
        "dc": dc,

        "sku_count": len(
            {
                row["sku"]
                for row in dc_inventory
            }
        ),

        "skus_needing_action": len(
            actionable
        ),

        "skus_monitoring": len(
            monitoring
        ),

        "skus_healthy": len(
            healthy
        ),

        "skus_needing_review": len(
            review
        ),

        "skus_projection_unavailable": (
            len(unavailable)
        ),

        "skus_to_expedite": len(
            expedite
        ),

        "skus_needing_new_order": len(
            new_orders
        ),

        "skus_monitoring_projected_order": (
            len(
                projected_order_monitors
            )
        ),

        "quantity_needed_cases": (
            recommended_cases
        ),

        "recommendation_complete": (
            len(review) == 0
            and len(unavailable) == 0
        ),
    }


# =============================================================================
# OVERVIEW
# =============================================================================


@router.get("/overview")
def get_inventory_overview(
    org_id: str,
):
    org_dir = (
        BASE_DATA_DIR
        / org_id
    )

    (
        inventory,
        _,
        _,
        _,
        _,
    ) = _load_and_assess_inventory(
        org_dir=org_dir,
        org_id=org_id,
    )

    if not inventory:
        return {
            "summary": {
                "dc_count": 0,
                "dcs_needing_action": 0,
                "dcs_monitoring": 0,
                "dcs_needing_review": 0,
                "dcs_with_projection_unavailable": 0,
                "known_recommended_cases": 0,
            },
            "distribution_centers": [],
        }

    grouped = {}

    for row in inventory:
        distributor = row.get(
            "distributor"
        )

        dc = row.get("dc")

        if (
            distributor is None
            or dc is None
        ):
            continue

        key = (
            distributor,
            dc,
        )

        grouped.setdefault(
            key,
            [],
        ).append(row)

    distribution_centers = [
        _build_dc_summary(rows)
        for rows in grouped.values()
    ]

    distribution_centers.sort(
        key=lambda row: (
            -row[
                "skus_needing_action"
            ],
            -row[
                "skus_to_expedite"
            ],
            -row[
                "skus_needing_new_order"
            ],
            -(
                row[
                    "quantity_needed_cases"
                ]
                or 0
            ),
            row["distributor"],
            row["dc"],
        )
    )

    return _json_safe({
        "summary": {
            "dc_count": len(
                distribution_centers
            ),

            "dcs_needing_action": sum(
                row[
                    "skus_needing_action"
                ] > 0
                for row
                in distribution_centers
            ),

            "dcs_monitoring": sum(
                row[
                    "skus_monitoring"
                ] > 0
                for row
                in distribution_centers
            ),

            "dcs_needing_review": sum(
                row[
                    "skus_needing_review"
                ] > 0
                for row
                in distribution_centers
            ),

            "dcs_with_projection_unavailable": (
                sum(
                    row[
                        "skus_projection_unavailable"
                    ] > 0
                    for row
                    in distribution_centers
                )
            ),

            "known_recommended_cases": (
                sum(
                    row[
                        "quantity_needed_cases"
                    ]
                    or 0
                    for row
                    in distribution_centers
                )
            ),
        },

        "distribution_centers": (
            distribution_centers
        ),
    })


# =============================================================================
# STORE MAP HELPERS
# =============================================================================


def _get_active_stores(
    features_df: pd.DataFrame,
    distributor: str,
    dc: str,
) -> pd.DataFrame:
    df = features_df.copy()

    df["month_year"] = (
        pd.PeriodIndex(
            df["month_year"],
            freq="M",
        )
    )

    complete_end = (
        pd.Timestamp.today()
        .to_period("M")
        - 1
    )

    recent_start = (
        complete_end - 2
    )

    df = df[
        (
            df["distributor"]
            == distributor
        )
        & (
            df["dc"]
            == dc
        )
        & (
            df["month_year"]
            .between(
                recent_start,
                complete_end,
            )
        )
        & (
            df["units"] > 0
        )
    ].copy()

    if df.empty:
        return pd.DataFrame()

    store_columns = [
        column
        for column in [
            "coded_customer",
            "chain",
            "channel",
            "state",
        ]
        if column in df.columns
    ]

    if (
        "coded_customer"
        not in store_columns
    ):
        return pd.DataFrame()

    return (
        df[store_columns]
        .drop_duplicates(
            "coded_customer"
        )
        .reset_index(drop=True)
    )


def _add_store_coordinates(
    stores: pd.DataFrame,
    coordinates_path: Path,
) -> pd.DataFrame:
    stores = stores.copy()

    stores["latitude"] = pd.NA
    stores["longitude"] = pd.NA

    if (
        stores.empty
        or not coordinates_path.exists()
    ):
        return stores

    coordinates = pd.read_csv(
        coordinates_path
    )

    required_columns = {
        "coded_customer",
        "latitude",
        "longitude",
    }

    if not required_columns.issubset(
        coordinates.columns
    ):
        return stores

    coordinates = coordinates[
        [
            "coded_customer",
            "latitude",
            "longitude",
        ]
    ].copy()

    coordinates["latitude"] = (
        pd.to_numeric(
            coordinates["latitude"],
            errors="coerce",
        )
    )

    coordinates["longitude"] = (
        pd.to_numeric(
            coordinates["longitude"],
            errors="coerce",
        )
    )

    coordinates = (
        coordinates
        .drop_duplicates(
            "coded_customer",
            keep="last",
        )
        .reset_index(drop=True)
    )

    return (
        stores
        .drop(
            columns=[
                "latitude",
                "longitude",
            ],
            errors="ignore",
        )
        .merge(
            coordinates,
            on="coded_customer",
            how="left",
        )
    )


# =============================================================================
# DC DETAIL
# =============================================================================


@router.get("/dc-detail")
def get_inventory_dc_detail(
    org_id: str,
    distributor: str,
    dc: str,
):
    distributor = (
        distributor
        .upper()
        .strip()
    )

    dc = (
        dc
        .upper()
        .strip()
    )

    org_dir = (
        BASE_DATA_DIR
        / org_id
    )

    features_path = (
        org_dir
        / "processed"
        / "features_df.parquet"
    )

    coordinates_path = (
        org_dir
        / "maps"
        / "store_coordinates.csv"
    )

    if not features_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "Sales features not found."
            ),
        )

    (
        inventory,
        _,
        _,
        _,
        _,
    ) = _load_and_assess_inventory(
        org_dir=org_dir,
        org_id=org_id,
    )

    features_df = pd.read_parquet(
        features_path
    )

    dc_inventory = [
        row
        for row in inventory
        if (
            row.get(
                "distributor"
            )
            == distributor
            and row.get("dc") == dc
        )
    ]

    if not dc_inventory:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No inventory found for "
                f"{distributor} {dc}."
            ),
        )

    stores = (
        _add_store_coordinates(
            _get_active_stores(
                features_df=features_df,
                distributor=distributor,
                dc=dc,
            ),
            coordinates_path=(
                coordinates_path
            ),
        )
    )

    dc_summary = (
        _build_dc_summary(
            dc_inventory
        )
    )

    # Active actions first, then monitor, healthy,
    # then unavailable.
    status_priority = {
        "action": 0,
        "monitor": 1,
        "healthy": 2,
        "projection_unavailable": 3,
    }

    dc_inventory.sort(
        key=lambda row: (
            status_priority.get(
                row.get(
                    "inventory_status"
                ),
                99,
            ),
            -float(
                row.get(
                    "summary",
                    {},
                ).get(
                    "recommended_cases",
                    0,
                )
                or 0
            ),
            row.get(
                "sku",
                "",
            ),
        )
    )

    store_rows = []

    if not stores.empty:
        for _, row in (
            stores.iterrows()
        ):
            store_rows.append({
                "coded_customer": (
                    row.get(
                        "coded_customer"
                    )
                ),
                "chain": row.get(
                    "chain"
                ),
                "channel": row.get(
                    "channel"
                ),
                "state": row.get(
                    "state"
                ),
                "latitude": _safe_float(
                    row.get(
                        "latitude"
                    )
                ),
                "longitude": _safe_float(
                    row.get(
                        "longitude"
                    )
                ),
            })

    return _json_safe({
        "distributor": distributor,
        "dc": dc,
        "dc_name": dc,

        "dc_latitude": None,
        "dc_longitude": None,

        **dc_summary,

        "active_store_count": (
            len(stores)
        ),

        "skus": dc_inventory,

        "stores": store_rows,
    })


# =============================================================================
# SKU PROJECTION / FULL INVENTORY OUTLOOK
# =============================================================================


@router.get("/projection")
def get_inventory_projection(
    org_id: str = Query(...),
    distributor: str = Query(...),
    dc: str = Query(...),
    sku: str = Query(...),
):
    """
    Return the complete new-engine inventory outlook for one
    distributor × DC × SKU.

    This is the same assessment used by /overview and /dc-detail.
    No independent projection or recommendation logic is run here.
    """

    distributor = (
        distributor
        .upper()
        .strip()
    )

    dc = (
        dc
        .upper()
        .strip()
    )

    sku = (
        sku
        .upper()
        .strip()
    )

    org_dir = (
        BASE_DATA_DIR
        / org_id
    )

    (
        inventory,
        _,
        _,
        _,
        _,
    ) = _load_and_assess_inventory(
        org_dir=org_dir,
        org_id=org_id,
    )

    selected = [
        row
        for row in inventory
        if (
            row.get(
                "distributor"
            )
            == distributor
            and row.get(
                "dc"
            )
            == dc
            and row.get(
                "sku"
            )
            == sku
        )
    ]

    if not selected:
        raise HTTPException(
            status_code=404,
            detail=(
                "Inventory assessment not "
                f"found for {distributor} / "
                f"{dc} / {sku}"
            ),
        )

    return _json_safe(
        selected[0]
    )
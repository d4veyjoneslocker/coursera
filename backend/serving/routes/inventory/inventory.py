import math
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException

from backend.insights.inventory.inventory_risk import run_inventory_risk


router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
)


BASE_DATA_DIR = Path("backend/data")


def _safe_float(value):
    if pd.isna(value):
        return None

    return float(value)


def _safe_int(value):
    if pd.isna(value):
        return None

    return int(value)


def _get_dc_status(df: pd.DataFrame) -> str:
    if df.empty:
        return "unknown"

    if df["inventory_urgency"].eq("critical").any():
        return "critical"

    if df["inventory_urgency"].eq("high").any():
        return "needs_attention"

    if df["inventory_urgency"].eq("review").any():
        return "review"

    return "healthy"


def _get_dc_coverage(
    df: pd.DataFrame,
    inventory_column: str,
) -> float | None:
    velocity = df["dc_weekly_velocity"].dropna()

    if velocity.empty:
        return None

    total_velocity = df["dc_weekly_velocity"].fillna(0).sum()

    if total_velocity <= 0:
        return None

    total_inventory = df[inventory_column].fillna(0).sum()

    return total_inventory / total_velocity

def _build_dc_summary(
    dc_inventory: pd.DataFrame,
) -> dict:
    distributor = dc_inventory["distributor"].iloc[0]
    dc = dc_inventory["dc"].iloc[0]

    quantity_on_hand_cases = (
        dc_inventory["quantity_on_hand_cases"]
        .fillna(0)
        .sum()
    )

    quantity_on_po_cases = (
        dc_inventory[
            "quantity_on_purchase_order_cases"
        ]
        .fillna(0)
        .sum()
    )

    weeks_on_hand = _get_dc_coverage(
        dc_inventory,
        "quantity_on_hand_units",
    )

    weeks_with_inbound = _get_dc_coverage(
        dc_inventory,
        "inventory_units_with_inbound",
    )

    total_units_per_week = (
        dc_inventory["dc_weekly_velocity"]
        .fillna(0)
        .sum()
    )

    total_cases_per_week = (
        (
            dc_inventory["dc_weekly_velocity"]
            / dc_inventory["units_per_case"]
        )
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
        .sum()
    )

    recommendations = pd.to_numeric(
        dc_inventory["recommended_cases_to_send"],
        errors="coerce",
    )

    known_recommendations = recommendations.dropna()

    known_recommended_cases = (
        known_recommendations.sum()
        if not known_recommendations.empty
        else None
    )
    recommendation_complete = bool(
        recommendations.notna().all()
    )

    lead_time_days = (
        dc_inventory["planning_lead_time_days"]
        .dropna()
    )

    planning_lead_time_days = (
        lead_time_days.iloc[0]
        if not lead_time_days.empty
        else None
    )

    monitor_inbound = bool(
        dc_inventory["monitor_inbound"]
        .fillna(False)
        .any()
    )

    order_needed = bool(
        dc_inventory["order_needed"]
        .fillna(False)
        .any()
    )

    skus_needing_order = int(
        dc_inventory.loc[
            dc_inventory["order_needed"].fillna(False),
            "sku",
        ].nunique()
    )

    return {
        "distributor": distributor,
        "dc": dc,

        "status": _get_dc_status(
            dc_inventory
        ),

        "quantity_needed_cases": _safe_float(
            known_recommended_cases
        ),

        "recommendation_complete": (
            recommendation_complete
        ),

        "weeks_on_hand": _safe_float(
            weeks_on_hand
        ),

        "weeks_with_inbound": _safe_float(
            weeks_with_inbound
        ),

        "planning_lead_time_days": _safe_float(
            planning_lead_time_days
        ),

        "monitor_inbound": monitor_inbound,
        "order_needed": order_needed,

        "sku_count": int(
            dc_inventory["sku"].nunique()
        ),

        "skus_needing_order": (
            skus_needing_order
        ),

        "quantity_on_hand_cases": _safe_float(
            quantity_on_hand_cases
        ),

        "quantity_on_po_cases": _safe_float(
            quantity_on_po_cases
        ),

        "units_per_week": _safe_float(
            total_units_per_week
        ),

        "cases_per_week": _safe_float(
            total_cases_per_week
        ),
    }

@router.get("/overview")
def get_inventory_overview(
    org_id: str,
):
    org_dir = BASE_DATA_DIR / "default_org"

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

    inventory = run_inventory_risk(
        inventory_features,
        inventory_history=inventory_history,
    )

    if inventory.empty:
        return {
            "summary": {
                "dc_count": 0,
                "dcs_needing_action": 0,
                "dcs_monitoring_inbound": 0,
                "dcs_needing_review": 0,
                "known_recommended_cases": 0,
            },
            "distribution_centers": [],
        }

    distribution_centers = []

    for (
        distributor,
        dc,
    ), dc_inventory in inventory.groupby(
        ["distributor", "dc"],
        dropna=False,
    ):
        if pd.isna(distributor) or pd.isna(dc):
            continue

        distribution_centers.append(
            _build_dc_summary(
                dc_inventory.copy()
            )
        )

    status_priority = {
        "critical": 0,
        "needs_attention": 1,
        "review": 2,
        "healthy": 3,
        "unknown": 4,
    }

    distribution_centers.sort(
        key=lambda row: (
            status_priority.get(
                row["status"],
                99,
            ),
            -(
                row["quantity_needed_cases"]
                or 0
            ),
        )
    )

    dcs_needing_action = sum(
        1
        for row in distribution_centers
        if row["order_needed"]
    )

    dcs_monitoring_inbound = sum(
        1
        for row in distribution_centers
        if row["monitor_inbound"]
    )
    
    dcs_needing_review = sum(
        1
        for row in distribution_centers
        if row["status"] == "review"
    )

    known_recommended_cases = sum(
        row["quantity_needed_cases"] or 0
        for row in distribution_centers
    )

    return {
        "summary": {
            "dc_count": len(
                distribution_centers
            ),
            "dcs_needing_action": (
                dcs_needing_action
            ),
            "dcs_monitoring_inbound": (
                dcs_monitoring_inbound
            ),
            "dcs_needing_review": (
                dcs_needing_review
            ),
            "known_recommended_cases": (
                _safe_float(
                    known_recommended_cases
                )
            ),
        },
        "distribution_centers": (
            distribution_centers
        ),
    }


def _get_active_stores(
    features_df: pd.DataFrame,
    distributor: str,
    dc: str,
) -> pd.DataFrame:
    df = features_df.copy()

    df["month_year"] = pd.PeriodIndex(
        df["month_year"],
        freq="M",
    )

    current_month = pd.Timestamp.today().to_period("M")
    complete_end = current_month - 1
    recent_start = complete_end - 2

    df = df[
        (df["distributor"] == distributor)
        & (df["dc"] == dc)
        & (df["month_year"].between(recent_start, complete_end))
        & (df["units"] > 0)
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

    stores = (
        df[store_columns]
        .drop_duplicates("coded_customer")
        .reset_index(drop=True)
    )

    return stores


def _add_store_coordinates(
    stores: pd.DataFrame,
    coordinates_path: Path,
) -> pd.DataFrame:
    stores = stores.copy()

    stores["latitude"] = pd.NA
    stores["longitude"] = pd.NA

    if stores.empty or not coordinates_path.exists():
        return stores

    coordinates = pd.read_csv(coordinates_path)

    required_columns = {
        "coded_customer",
        "latitude",
        "longitude",
    }

    if not required_columns.issubset(coordinates.columns):
        return stores

    coordinates = coordinates[
        [
            "coded_customer",
            "latitude",
            "longitude",
        ]
    ].copy()

    coordinates["latitude"] = pd.to_numeric(
        coordinates["latitude"],
        errors="coerce",
    )

    coordinates["longitude"] = pd.to_numeric(
        coordinates["longitude"],
        errors="coerce",
    )

    coordinates = (
        coordinates
        .drop_duplicates(
            "coded_customer",
            keep="last",
        )
        .reset_index(drop=True)
    )

    stores = stores.drop(
        columns=[
            "latitude",
            "longitude",
        ],
        errors="ignore",
    )

    return stores.merge(
        coordinates,
        on="coded_customer",
        how="left",
    )


@router.get("/dc-detail")
def get_inventory_dc_detail(
    org_id: str,
    distributor: str,
    dc: str,
):
    distributor = distributor.upper().strip()
    dc = dc.upper().strip()

    org_dir = BASE_DATA_DIR / org_id

    inventory_features_path = (
        org_dir
        / "inventory_features_test.csv"
    )

    inventory_history_path = (
        org_dir
        / "inventory_combined.parquet"
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

    # ---------------------------------------------------------
    # Load required data
    # ---------------------------------------------------------

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

    if not features_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Sales features not found.",
        )

    inventory_features = pd.read_csv(
        inventory_features_path
    )

    inventory_history = pd.read_parquet(
        inventory_history_path
    )

    features_df = pd.read_parquet(
        features_path
    )

    # ---------------------------------------------------------
    # Run current inventory decision logic
    # ---------------------------------------------------------

    inventory = run_inventory_risk(
        inventory_features,
        inventory_history=inventory_history,
    )

    dc_inventory = inventory[
        (inventory["distributor"] == distributor)
        & (inventory["dc"] == dc)
    ].copy()

    if dc_inventory.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No inventory found for {distributor} {dc}.",
        )

    # ---------------------------------------------------------
    # Active stores
    # ---------------------------------------------------------

    stores = _get_active_stores(
        features_df,
        distributor=distributor,
        dc=dc,
    )

    stores = _add_store_coordinates(
        stores,
        coordinates_path,
    )

    # ---------------------------------------------------------
    # DC-level metrics
    # ---------------------------------------------------------

    quantity_on_hand_cases = (
        dc_inventory["quantity_on_hand_cases"]
        .fillna(0)
        .sum()
    )

    quantity_on_hand_units = (
        dc_inventory["quantity_on_hand_units"]
        .fillna(0)
        .sum()
    )

    quantity_on_po_cases = (
        dc_inventory[
            "quantity_on_purchase_order_cases"
        ]
        .fillna(0)
        .sum()
    )

    quantity_on_po_units = (
        dc_inventory[
            "quantity_on_purchase_order_units"
        ]
        .fillna(0)
        .sum()
    )

    weeks_on_hand = _get_dc_coverage(
        dc_inventory,
        "quantity_on_hand_units",
    )

    weeks_with_inbound = _get_dc_coverage(
        dc_inventory,
        "inventory_units_with_inbound",
    )

    total_units_per_week = (
        dc_inventory["dc_weekly_velocity"]
        .fillna(0)
        .sum()
    )

    total_cases_per_week = (
        (
            dc_inventory["dc_weekly_velocity"]
            / dc_inventory["units_per_case"]
        )
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
        .sum()
    )

    recommended_cases = (
        dc_inventory["recommended_cases_to_send"]
        .dropna()
        .sum()
    )

    lead_time_days = (
        dc_inventory["planning_lead_time_days"]
        .dropna()
    )

    replenishment_event_count = (
        dc_inventory["replenishment_event_count"]
        .dropna()
    )

    lead_time_source = (
        dc_inventory["lead_time_source"]
        .dropna()
    )

    planning_lead_time_days = (
        lead_time_days.iloc[0]
        if not lead_time_days.empty
        else None
    )

    lead_time_events = (
        replenishment_event_count.iloc[0]
        if not replenishment_event_count.empty
        else None
    )

    dc_lead_time_source = (
        lead_time_source.iloc[0]
        if not lead_time_source.empty
        else "missing"
    )

    # ---------------------------------------------------------
    # SKU snapshot
    # ---------------------------------------------------------

    sku_rows = []

    for _, row in dc_inventory.sort_values(
        "recommended_cases_to_send",
        ascending=False,
        na_position="last",
    ).iterrows():
        units_per_case = row.get(
            "units_per_case"
        )

        velocity_units = row.get(
            "dc_weekly_velocity"
        )

        velocity_cases = None

        if (
            pd.notna(velocity_units)
            and pd.notna(units_per_case)
            and units_per_case > 0
        ):
            velocity_cases = (
                velocity_units / units_per_case
            )

        state = row[
            "current_inventory_state"
        ]

        if state == "healthy":
            status = "healthy"
        elif state == "no_active_demand":
            status = "review"
        else:
            status = "needs_order"

        sku_rows.append(
            {
                "sku": row["sku"],

                "product_name": row["sku"],

                # Wire actual product images later.
                "image_url": None,

                "units_per_case": _safe_float(
                    units_per_case
                ),

                "quantity_on_hand_cases": _safe_float(
                    row[
                        "quantity_on_hand_cases"
                    ]
                ),

                "quantity_on_hand_units": _safe_float(
                    row[
                        "quantity_on_hand_units"
                    ]
                ),

                "quantity_on_po_cases": _safe_float(
                    row[
                        "quantity_on_purchase_order_cases"
                    ]
                ),

                "quantity_on_po_units": _safe_float(
                    row[
                        "quantity_on_purchase_order_units"
                    ]
                ),

                "units_per_week": _safe_float(
                    velocity_units
                ),

                "cases_per_week": _safe_float(
                    velocity_cases
                ),

                "weeks_on_hand": _safe_float(
                    row[
                        "calculated_weeks_on_hand"
                    ]
                ),

                "weeks_with_inbound": _safe_float(
                    row[
                        "weeks_of_inventory_with_inbound"
                    ]
                ),

                "recommended_cases_to_send": _safe_float(
                    row[
                        "recommended_cases_to_send"
                    ]
                ),

                "monitor_inbound": bool(
                    row["monitor_inbound"]
                ),

                "order_needed": bool(
                    row["order_needed"]
                ),

                "lead_time_risk": bool(
                    row["lead_time_risk"]
                ),

                "status": status,
            }
        )

    # ---------------------------------------------------------
    # Store list
    # ---------------------------------------------------------

    store_rows = []

    if not stores.empty:
        for _, row in stores.iterrows():
            store_rows.append(
                {
                    "coded_customer": row.get(
                        "coded_customer"
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
                        row.get("latitude")
                    ),
                    "longitude": _safe_float(
                        row.get("longitude")
                    ),
                }
            )

    # ---------------------------------------------------------
    # Response
    # ---------------------------------------------------------

    return {
        "distributor": distributor,
        "dc": dc,

        # We can map code -> full DC name later.
        "dc_name": dc,

        # DC itself has not been geocoded yet.
        "dc_latitude": None,
        "dc_longitude": None,

        "status": _get_dc_status(
            dc_inventory
        ),

        "quantity_on_hand_cases": _safe_float(
            quantity_on_hand_cases
        ),

        "quantity_on_hand_units": _safe_float(
            quantity_on_hand_units
        ),

        "quantity_on_po_cases": _safe_float(
            quantity_on_po_cases
        ),

        "quantity_on_po_units": _safe_float(
            quantity_on_po_units
        ),

        "weeks_on_hand": _safe_float(
            weeks_on_hand
        ),

        "weeks_with_inbound": _safe_float(
            weeks_with_inbound
        ),

        "planning_lead_time_days": _safe_float(
            planning_lead_time_days
        ),

        "replenishment_event_count": _safe_int(
            lead_time_events
        ),

        "lead_time_source": dc_lead_time_source,

        "quantity_needed_cases": _safe_float(
            recommended_cases
        ),

        "active_store_count": len(
            stores
        ),

        "units_per_week": _safe_float(
            total_units_per_week
        ),

        "cases_per_week": _safe_float(
            total_cases_per_week
        ),

        "target_inventory_weeks": 8,

        "skus": sku_rows,

        "stores": store_rows,
    }
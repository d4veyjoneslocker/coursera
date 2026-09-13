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
        dc_inventory["quantity_on_purchase_order_cases"]
        .fillna(0)
        .sum()
    )

    quantity_on_po_units = (
        dc_inventory["quantity_on_purchase_order_units"]
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
        units_per_case = row.get("units_per_case")
        velocity_units = row.get("dc_weekly_velocity")
        velocity_cases = None

        if (
            pd.notna(velocity_units)
            and pd.notna(units_per_case)
            and units_per_case > 0
        ):
            velocity_cases = velocity_units / units_per_case

        state = row["current_inventory_state"]

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

                # Actual product imagery can be wired later.
                "image_url": None,

                "units_per_case": _safe_float(
                    units_per_case
                ),

                "quantity_on_hand_cases": _safe_float(
                    row["quantity_on_hand_cases"]
                ),

                "quantity_on_hand_units": _safe_float(
                    row["quantity_on_hand_units"]
                ),

                "quantity_on_po_cases": _safe_float(
                    row["quantity_on_purchase_order_cases"]
                ),

                "quantity_on_po_units": _safe_float(
                    row["quantity_on_purchase_order_units"]
                ),

                "units_per_week": _safe_float(
                    velocity_units
                ),

                "cases_per_week": _safe_float(
                    velocity_cases
                ),

                "weeks_on_hand": _safe_float(
                    row["calculated_weeks_on_hand"]
                ),

                "weeks_with_inbound": _safe_float(
                    row["weeks_of_inventory_with_inbound"]
                ),

                "recommended_cases_to_send": _safe_float(
                    row["recommended_cases_to_send"]
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
    #
    # These are the real active stores for this distributor/DC.
    # Map coordinates will be joined later after geocoding.
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
                }
            )

    # ---------------------------------------------------------
    # Response
    # ---------------------------------------------------------

    return {
        "distributor": distributor,
        "dc": dc,

        # Full DC name/location can be mapped later.
        "dc_name": dc,

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
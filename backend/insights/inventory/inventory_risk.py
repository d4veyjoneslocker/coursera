import numpy as np
import pandas as pd

from backend.metrics.inventory.replenishment_lead_time import (
    calculate_replenishment_lead_time,
)


def get_current_inventory_state(
    row: pd.Series,
    low_inventory_weeks: float = 4.0,
) -> str:
    if (
        pd.isna(row["dc_weekly_velocity"])
        or row["dc_weekly_velocity"] <= 0
    ):
        return "no_active_demand"

    if row["is_out_of_stock"]:
        return "oos"

    if (
        pd.notna(row["calculated_weeks_on_hand"])
        and row["calculated_weeks_on_hand"] < low_inventory_weeks
    ):
        return "low"

    return "healthy"


def run_inventory_risk(
    df: pd.DataFrame,
    inventory_history: pd.DataFrame,
    low_inventory_weeks: float = 4.0,
    lead_time_overrides: pd.DataFrame | None = None,
) -> pd.DataFrame:
    df = df.copy()

    # Keep relevant inventory positions
    df = df[df["is_relevant_dc_sku"]].copy()

    # Current inventory position only
    df["report_date"] = pd.to_datetime(
        df["report_date"],
        errors="coerce",
    )

    df = (
        df.sort_values("report_date")
        .groupby(["distributor", "dc", "sku"], as_index=False)
        .tail(1)
        .reset_index(drop=True)
    )

    # Current inventory state
    df["current_inventory_state"] = df.apply(
        get_current_inventory_state,
        axis=1,
        low_inventory_weeks=low_inventory_weeks,
    )

    # ---------------------------------------------------------
    # Replenishment lead time
    # ---------------------------------------------------------

    lead_times = calculate_replenishment_lead_time(
        inventory_history
    )

    if not lead_times.empty:
        df = df.merge(
            lead_times[
                [
                    "distributor",
                    "dc",
                    "median_replenishment_days",
                    "average_replenishment_days",
                    "replenishment_event_count",
                ]
            ],
            on=["distributor", "dc"],
            how="left",
        )
    else:
        df["median_replenishment_days"] = pd.NA
        df["average_replenishment_days"] = pd.NA
        df["replenishment_event_count"] = pd.NA

    # Optional user lead-time override
    if (
        lead_time_overrides is not None
        and not lead_time_overrides.empty
    ):
        overrides = lead_time_overrides[
            [
                "distributor",
                "dc",
                "lead_time_override_days",
            ]
        ].drop_duplicates(["distributor", "dc"])

        df = df.merge(
            overrides,
            on=["distributor", "dc"],
            how="left",
        )
    else:
        df["lead_time_override_days"] = pd.NA

    # User override wins, otherwise use observed median
    df["planning_lead_time_days"] = (
        df["lead_time_override_days"]
        .fillna(df["median_replenishment_days"])
    )

    df["lead_time_source"] = np.select(
        [
            df["lead_time_override_days"].notna(),
            df["median_replenishment_days"].notna(),
        ],
        [
            "user_override",
            "observed_history",
        ],
        default="missing",
    )

    df["planning_lead_time_weeks"] = (
        df["planning_lead_time_days"] / 7
    )

    # Expected demand while waiting for replenishment
    df["lead_time_demand_units"] = (
        df["dc_weekly_velocity"]
        * df["planning_lead_time_weeks"]
    )

    # ---------------------------------------------------------
    # Actions
    # ---------------------------------------------------------

    # Existing inbound orders should be monitored independently
    df["monitor_inbound"] = df["has_open_po"]

    # Existing 8-week gap + expected demand during lead time
    df["recommended_units_to_send"] = (
        df["additional_units_needed_after_inbound"]
        + df["lead_time_demand_units"]
    )

    case_recommendation = pd.to_numeric(
        df["recommended_units_to_send"]
        / df["units_per_case"],
        errors="coerce",
    )

    df["recommended_cases_to_send"] = np.ceil(
        case_recommendation.astype(float)
    )

    # No active demand means we cannot make a recommendation
    df.loc[
        df["current_inventory_state"].eq("no_active_demand"),
        "recommended_cases_to_send",
    ] = pd.NA

    # Missing lead time means the complete recommendation
    # cannot yet be calculated
    missing_lead_time = (
        df["current_inventory_state"].ne("no_active_demand")
        & df["planning_lead_time_days"].isna()
    )

    df.loc[
        missing_lead_time,
        "recommended_cases_to_send",
    ] = pd.NA

    df["order_needed"] = (
        df["current_inventory_state"].ne("no_active_demand")
        & df["recommended_cases_to_send"].notna()
        & df["recommended_cases_to_send"].gt(0)
    )

    # ---------------------------------------------------------
    # Lead-time risk
    # ---------------------------------------------------------

    df["lead_time_risk"] = (
        df["calculated_weeks_on_hand"].notna()
        & df["planning_lead_time_weeks"].notna()
        & (
            df["calculated_weeks_on_hand"]
            <= df["planning_lead_time_weeks"]
        )
    )

    # ---------------------------------------------------------
    # Urgency
    # ---------------------------------------------------------

    df["inventory_urgency"] = "normal"

    df.loc[
        df["current_inventory_state"].eq("low"),
        "inventory_urgency",
    ] = "high"

    df.loc[
        df["current_inventory_state"].eq("oos"),
        "inventory_urgency",
    ] = "critical"

    df.loc[
        df["current_inventory_state"].eq("no_active_demand"),
        "inventory_urgency",
    ] = "review"

    df.loc[
        df["lead_time_risk"]
        & df["current_inventory_state"].ne("oos")
        & df["current_inventory_state"].ne("no_active_demand"),
        "inventory_urgency",
    ] = "critical"

    return df
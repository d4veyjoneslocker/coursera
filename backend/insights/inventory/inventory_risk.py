import numpy as np
import pandas as pd

from backend.metrics.inventory.replenishment_metrics import (
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

    # ---------------------------------------------------------
    # Keep relevant/current inventory positions
    # ---------------------------------------------------------

    df = df[df["is_relevant_dc_sku"]].copy()

    df["report_date"] = pd.to_datetime(
        df["report_date"],
        errors="coerce",
    )

    df = (
        df.sort_values("report_date")
        .groupby(
            ["distributor", "dc", "sku"],
            as_index=False,
        )
        .tail(1)
        .reset_index(drop=True)
    )

    # ---------------------------------------------------------
    # Current inventory state
    # ---------------------------------------------------------

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
        lead_times = lead_times.copy()

        lead_times["median_replenishment_days"] = (
            pd.to_numeric(
                lead_times[
                    "median_replenishment_days"
                ],
                errors="coerce",
            )
        )

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

        # -----------------------------------------------------
        # Distributor-level observed default
        #
        # Example:
        # If one UNFI DC does not have enough history,
        # use the median observed UNFI lead time.
        # -----------------------------------------------------

        distributor_defaults = (
            lead_times.groupby(
                "distributor",
                as_index=False,
            )["median_replenishment_days"]
            .median()
            .rename(
                columns={
                    "median_replenishment_days":
                        "distributor_default_lead_time_days"
                }
            )
        )

        df = df.merge(
            distributor_defaults,
            on="distributor",
            how="left",
        )

        # -----------------------------------------------------
        # Network-wide observed default
        #
        # Right now this is effectively derived from the
        # available UNFI observations.
        #
        # KeHE will fall back to this until the user provides
        # a KeHE-specific planning assumption.
        # -----------------------------------------------------

        network_default_lead_time_days = (
            lead_times[
                "median_replenishment_days"
            ]
            .dropna()
            .median()
        )

    else:
        df["median_replenishment_days"] = pd.NA
        df["average_replenishment_days"] = pd.NA
        df["replenishment_event_count"] = pd.NA

        df[
            "distributor_default_lead_time_days"
        ] = pd.NA

        network_default_lead_time_days = pd.NA

    df["network_default_lead_time_days"] = (
        network_default_lead_time_days
    )

    # ---------------------------------------------------------
    # User lead-time overrides
    #
    # Supports:
    #
    # distributor | dc   | lead_time_override_days
    # ------------------------------------------------
    # KEHE        | null | 14
    # UNFI        | HVA  | 10
    #
    # Null DC = override entire distributor.
    # ---------------------------------------------------------

    df["dc_lead_time_override_days"] = pd.NA
    df[
        "distributor_lead_time_override_days"
    ] = pd.NA

    if (
        lead_time_overrides is not None
        and not lead_time_overrides.empty
    ):
        overrides = lead_time_overrides.copy()

        overrides["lead_time_override_days"] = (
            pd.to_numeric(
                overrides["lead_time_override_days"],
                errors="coerce",
            )
        )

        # -----------------------------------------------------
        # DC-specific overrides
        # -----------------------------------------------------

        dc_overrides = overrides[
            overrides["dc"].notna()
        ][
            [
                "distributor",
                "dc",
                "lead_time_override_days",
            ]
        ].drop_duplicates(
            ["distributor", "dc"]
        )

        dc_overrides = dc_overrides.rename(
            columns={
                "lead_time_override_days":
                    "dc_lead_time_override_days"
            }
        )

        if not dc_overrides.empty:
            df = df.drop(
                columns=[
                    "dc_lead_time_override_days"
                ]
            )

            df = df.merge(
                dc_overrides,
                on=["distributor", "dc"],
                how="left",
            )

        # -----------------------------------------------------
        # Distributor-level overrides
        # -----------------------------------------------------

        distributor_overrides = overrides[
            overrides["dc"].isna()
        ][
            [
                "distributor",
                "lead_time_override_days",
            ]
        ].drop_duplicates(
            ["distributor"]
        )

        distributor_overrides = (
            distributor_overrides.rename(
                columns={
                    "lead_time_override_days":
                        "distributor_lead_time_override_days"
                }
            )
        )

        if not distributor_overrides.empty:
            df = df.drop(
                columns=[
                    "distributor_lead_time_override_days"
                ]
            )

            df = df.merge(
                distributor_overrides,
                on="distributor",
                how="left",
            )

    # ---------------------------------------------------------
    # Planning lead-time hierarchy
    #
    # 1. DC user override
    # 2. Distributor user override
    # 3. Observed DC history
    # 4. Observed distributor median
    # 5. Overall observed network median
    # ---------------------------------------------------------

    df["planning_lead_time_days"] = (
        df["dc_lead_time_override_days"]
        .fillna(
            df[
                "distributor_lead_time_override_days"
            ]
        )
        .fillna(
            df["median_replenishment_days"]
        )
        .fillna(
            df[
                "distributor_default_lead_time_days"
            ]
        )
        .fillna(
            df[
                "network_default_lead_time_days"
            ]
        )
    )

    df["lead_time_source"] = np.select(
        [
            df[
                "dc_lead_time_override_days"
            ].notna(),

            df[
                "distributor_lead_time_override_days"
            ].notna(),

            df[
                "median_replenishment_days"
            ].notna(),

            df[
                "distributor_default_lead_time_days"
            ].notna(),

            df[
                "network_default_lead_time_days"
            ].notna(),
        ],
        [
            "dc_user_override",
            "distributor_user_override",
            "observed_history",
            "distributor_default",
            "network_default",
        ],
        default="missing",
    )

    df["planning_lead_time_weeks"] = (
        df["planning_lead_time_days"] / 7
    )

    # ---------------------------------------------------------
    # Expected demand while waiting for replenishment
    # ---------------------------------------------------------

    df["lead_time_demand_units"] = (
        df["dc_weekly_velocity"]
        * df["planning_lead_time_weeks"]
    )

    # ---------------------------------------------------------
    # Actions
    # ---------------------------------------------------------

    # Existing inbound orders should be monitored independently
    df["monitor_inbound"] = df["has_open_po"]

    # Project inventory position when a new replenishment
    # could realistically arrive
    df["projected_inventory_at_replenishment_units"] = (
        df["quantity_on_hand_units"]
        + df["quantity_on_purchase_order_units"]
        - df["lead_time_demand_units"]
    )

    # Replenish enough to bring that projected future
    # inventory position back to the target
    df["recommended_units_to_send"] = (
        df["target_inventory_units"]
        - df["projected_inventory_at_replenishment_units"]
    ).clip(lower=0)

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
        df[
            "current_inventory_state"
        ].eq("no_active_demand"),
        "recommended_cases_to_send",
    ] = pd.NA

    # This should now be rare because missing observations
    # inherit a distributor/network default.
    missing_lead_time = (
        df[
            "current_inventory_state"
        ].ne("no_active_demand")
        & df[
            "planning_lead_time_days"
        ].isna()
    )

    df.loc[
        missing_lead_time,
        "recommended_cases_to_send",
    ] = pd.NA

    df["order_needed"] = (
        df[
            "current_inventory_state"
        ].ne("no_active_demand")
        & df[
            "recommended_cases_to_send"
        ].notna()
        & df[
            "recommended_cases_to_send"
        ].gt(0)
    )

    # ---------------------------------------------------------
    # Lead-time risk
    # ---------------------------------------------------------

    df["lead_time_risk"] = (
        df[
            "calculated_weeks_on_hand"
        ].notna()
        & df[
            "planning_lead_time_weeks"
        ].notna()
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
        df[
            "current_inventory_state"
        ].eq("low"),
        "inventory_urgency",
    ] = "high"

    df.loc[
        df[
            "current_inventory_state"
        ].eq("oos"),
        "inventory_urgency",
    ] = "critical"

    df.loc[
        df[
            "current_inventory_state"
        ].eq("no_active_demand"),
        "inventory_urgency",
    ] = "review"

    df.loc[
        df["lead_time_risk"]
        & df[
            "current_inventory_state"
        ].ne("oos")
        & df[
            "current_inventory_state"
        ].ne("no_active_demand"),
        "inventory_urgency",
    ] = "critical"

    return df
import numpy as np
import pandas as pd

from backend.metrics.inventory.inventory_velocity import calculate_dc_weekly_velocity


def add_inventory_features(
    df: pd.DataFrame,
    features_df: pd.DataFrame,
    low_inventory_weeks: float = 4.0,
    target_inventory_weeks: float = 8.0,
) -> pd.DataFrame:
    df = df.copy()

    # -----------------------------
    # Inventory including inbound POs
    # -----------------------------
    df["inventory_units_with_inbound"] = (
        df["quantity_on_hand_units"].fillna(0)
        + df["quantity_on_purchase_order_units"].fillna(0)
    )

    df["inventory_cases_with_inbound"] = (
        df["quantity_on_hand_cases"].fillna(0)
        + df["quantity_on_purchase_order_cases"].fillna(0)
    )

    # -----------------------------
    # Inventory state
    # -----------------------------
    df["is_out_of_stock"] = df["quantity_on_hand_units"].eq(0)
    df["has_open_po"] = df["quantity_on_purchase_order_units"].fillna(0).gt(0)

    # -----------------------------
    # Sales-derived DC velocity
    # -----------------------------
    dc_velocity = calculate_dc_weekly_velocity(features_df)

    df = df.merge(
        dc_velocity,
        on=["distributor", "dc", "sku"],
        how="left",
    )

    # -----------------------------
    # DC x SKU relevance
    # -----------------------------
    df["has_sales_history"] = df["dc_weekly_velocity"].notna()

    df["has_inventory"] = (
        df["quantity_on_hand_units"].fillna(0).gt(0)
        | df["quantity_on_purchase_order_units"].fillna(0).gt(0)
    )

    # Temporary until we add a client-maintained launch list
    df["is_planned_launch"] = False

    df["is_relevant_dc_sku"] = (
        df["has_sales_history"]
        | df["is_planned_launch"]
        | df["has_inventory"]
    )

    # -----------------------------
    # Current weeks on hand
    # -----------------------------
    df["calculated_weeks_on_hand"] = (
        df["quantity_on_hand_units"]
        / df["dc_weekly_velocity"]
    )

    df.loc[
        df["dc_weekly_velocity"].le(0),
        "calculated_weeks_on_hand",
    ] = pd.NA

    # -----------------------------
    # Weeks of inventory with inbound
    # -----------------------------
    df["weeks_of_inventory_with_inbound"] = (
        df["inventory_units_with_inbound"]
        / df["dc_weekly_velocity"]
    )

    df.loc[
        df["dc_weekly_velocity"].le(0),
        "weeks_of_inventory_with_inbound",
    ] = pd.NA

    # -----------------------------
    # Inventory target
    # -----------------------------
    df["target_inventory_units"] = (
        df["dc_weekly_velocity"] * target_inventory_weeks
    )

    # Additional inventory needed based on current on-hand
    df["additional_units_needed"] = (
        df["target_inventory_units"]
        - df["quantity_on_hand_units"].fillna(0)
    ).clip(lower=0)

    df["additional_cases_needed"] = np.ceil(
        df["additional_units_needed"]
        / df["units_per_case"]
    )

    # Additional inventory still needed after existing inbound POs arrive
    df["additional_units_needed_after_inbound"] = (
        df["target_inventory_units"]
        - df["inventory_units_with_inbound"]
    ).clip(lower=0)

    df["additional_cases_needed_after_inbound"] = np.ceil(
        df["additional_units_needed_after_inbound"]
        / df["units_per_case"]
    )

    # -----------------------------
    # Inventory risk flags
    # -----------------------------
    df["is_low_inventory"] = (
        df["calculated_weeks_on_hand"].gt(0)
        & df["calculated_weeks_on_hand"].lt(low_inventory_weeks)
    )

    return df
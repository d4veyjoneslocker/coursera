from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


EXPECTED_ORDER_EVENT_COLUMNS = [
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


def _empty_expected_order_events() -> pd.DataFrame:
    return pd.DataFrame(columns=EXPECTED_ORDER_EVENT_COLUMNS)


def _validate_required_columns(df: pd.DataFrame, required_columns: list[str], dataframe_name: str) -> None:
    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        raise ValueError(f"{dataframe_name} is missing required columns: {missing}")


def _normalize_output(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return _empty_expected_order_events()

    df = df.copy()
    df["expected_order_date"] = pd.to_datetime(df["expected_order_date"], errors="coerce").dt.normalize()
    df["expected_order_units"] = pd.to_numeric(df["expected_order_units"], errors="coerce")
    df["expected_order_cases"] = pd.to_numeric(df["expected_order_cases"], errors="coerce")

    return df[EXPECTED_ORDER_EVENT_COLUMNS].sort_values(
        ["expected_order_date", "distributor", "dc", "sku"],
        na_position="last",
    ).reset_index(drop=True)


# =============================================================================
# KEHE
# =============================================================================

def build_kehe_expected_order_events(order_projections: pd.DataFrame) -> pd.DataFrame:
    """
    Convert KeHE's Order Projections Report into canonical expected-order events.

    Grain:
        DC × SKU × projected order date
    """

    required = [
        "org_id",
        "distributor",
        "dc",
        "sku",
        "projected_order_date",
        "projected_order_units",
        "units_per_case",
    ]

    _validate_required_columns(order_projections, required, "KeHE order projections")

    df = order_projections.copy()
    df["projected_order_units"] = pd.to_numeric(df["projected_order_units"], errors="coerce")
    df["units_per_case"] = pd.to_numeric(df["units_per_case"], errors="coerce")
    df = df.loc[df["projected_order_units"].fillna(0) > 0].copy()

    if df.empty:
        return _empty_expected_order_events()

    invalid_case_pack = df["units_per_case"].isna() | df["units_per_case"].le(0)

    if invalid_case_pack.any():
        bad_rows = df.loc[invalid_case_pack, ["dc", "sku", "units_per_case"]]
        raise ValueError(f"Cannot convert KeHE projected orders to cases because units_per_case is missing or invalid for:\n{bad_rows.to_string(index=False)}")

    df["expected_order_date"] = pd.to_datetime(df["projected_order_date"], errors="coerce").dt.normalize()
    df["expected_order_units"] = df["projected_order_units"]
    df["expected_order_cases"] = np.ceil(df["projected_order_units"] / df["units_per_case"])
    df["source"] = "kehe_projection"
    df["confidence"] = "distributor_projection"

    return _normalize_output(df)


# =============================================================================
# UNFI
# =============================================================================

def build_unfi_expected_order_events(projected_orders: pd.DataFrame) -> pd.DataFrame:
    """
    Convert UNFI's Projected Orders Detail report into canonical expected-order events.

    Grain:
        DC × SKU × projected order date
    """

    required = [
        "org_id",
        "distributor",
        "dc",
        "sku",
        "projected_order_date",
        "projected_order_cases",
        "units_per_case",
    ]

    _validate_required_columns(projected_orders, required, "UNFI projected orders")

    df = projected_orders.copy()
    df["projected_order_cases"] = pd.to_numeric(df["projected_order_cases"], errors="coerce")
    df["units_per_case"] = pd.to_numeric(df["units_per_case"], errors="coerce")
    df = df.loc[df["projected_order_cases"].fillna(0) > 0].copy()

    if df.empty:
        return _empty_expected_order_events()

    invalid_case_pack = df["units_per_case"].isna() | df["units_per_case"].le(0)

    if invalid_case_pack.any():
        bad_rows = df.loc[invalid_case_pack, ["dc", "sku", "units_per_case"]]
        raise ValueError(f"Cannot convert UNFI projected orders to units because units_per_case is missing or invalid for:\n{bad_rows.to_string(index=False)}")

    df["expected_order_date"] = pd.to_datetime(df["projected_order_date"], errors="coerce").dt.normalize()
    df["expected_order_cases"] = df["projected_order_cases"]
    df["expected_order_units"] = df["projected_order_cases"] * df["units_per_case"]
    df["source"] = "unfi_projection"
    df["confidence"] = "distributor_projection"

    return _normalize_output(df)


# =============================================================================
# COMBINED
# =============================================================================

def build_expected_order_events(
    unfi_projected_orders: Optional[pd.DataFrame] = None,
    kehe_order_projections: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Build one canonical expected-order-event table from distributor-provided
    forward projections.
    """

    outputs = []

    if unfi_projected_orders is not None and not unfi_projected_orders.empty:
        outputs.append(build_unfi_expected_order_events(unfi_projected_orders))

    if kehe_order_projections is not None and not kehe_order_projections.empty:
        outputs.append(build_kehe_expected_order_events(kehe_order_projections))

    if not outputs:
        return _empty_expected_order_events()

    return _normalize_output(pd.concat(outputs, ignore_index=True))
"""
Drop-in replacement for the __main__ test block in inventory_projection.py.

Purpose: check whether an OUTSTANDING (confirmed) PO actually makes it onto the
line-chart series, and if not, WHICH of the three gates it dies at:

  Gate 1  _build_confirmed_po_events  -> is the PO found at all? timing_known?
  Gate 2  _get_projection_inbounds    -> does it become a line inbound, or get
                                         dropped for missing timing?
  Gate 3  the truncated window        -> does its delivery land inside end_date?

Set the SKU below to one you KNOW has an open PO (MAN Strawberry did earlier).
"""

from pathlib import Path

import pandas as pd

from backend.insights.inventory.order_assessment import run_inventory_risk
from backend.forecasting.inventory_projection import (
    build_inventory_projection,
    _build_confirmed_po_events,
    _get_projection_inbounds,
    _build_expected_order_events,
)
from backend.metrics.inventory.expected_orders import (
    build_kehe_expected_order_events,
    build_unfi_expected_order_events,
)
from backend.transforms.inventory.kehe import transform_kehe_order_projections
from backend.transforms.inventory.unfi import (
    transform_unfi_projected_orders,
    transform_unfi_purchase_orders,
)

# --- pick a SKU with a known outstanding PO -----------------------------------
org_id = "default_org"
distributor = "UNFI"
dc = "MAN"
sku = "STRAWBERRY"
as_of_date = "2026-09-16"

org_dir = Path("backend/data") / org_id

inventory_features = pd.read_csv(org_dir / "inventory_features_test.csv")
inventory_history = pd.read_parquet(org_dir / "inventory_combined.parquet")

purchase_orders = transform_unfi_purchase_orders(
    pd.read_csv(org_dir / "raw/inventory/unfi/Purchase Orders.csv"), org_id=org_id
)

expected_frames = [
    build_unfi_expected_order_events(
        transform_unfi_projected_orders(
            pd.read_csv(org_dir / "raw/inventory/unfi/Projected Orders Detail.csv"),
            org_id=org_id,
        )
    ),
    build_kehe_expected_order_events(
        transform_kehe_order_projections(
            pd.read_csv(org_dir / "raw/inventory/kehe/Order Projections Report.csv"),
            org_id=org_id,
        )
    ),
]
expected_orders = pd.concat(expected_frames, ignore_index=True)

assessment = run_inventory_risk(
    df=inventory_features.copy(),
    inventory_history=inventory_history,
    expected_orders=expected_orders,
    purchase_orders=purchase_orders,
    as_of_date=as_of_date,
)

row = assessment[
    (assessment["distributor"] == distributor)
    & (assessment["dc"] == dc)
    & (assessment["sku"] == sku)
].iloc[0]

print("=" * 70)
print(f"PO-ON-LINE DIAGNOSTIC — {distributor} {dc} {sku}  (as of {as_of_date})")
print("=" * 70)

# --- what the snapshot claims is on PO ----------------------------------------
on_po = row.get("quantity_on_purchase_order_cases")
print(f"\nsnapshot quantity_on_purchase_order_cases: {on_po}")

# --- Gate 1: are confirmed PO events built? -----------------------------------
confirmed = _build_confirmed_po_events(
    row=row, purchase_orders=purchase_orders, as_of_date=pd.Timestamp(as_of_date)
)
print("\n--- GATE 1: _build_confirmed_po_events ---")
if not confirmed:
    print("  -> NO confirmed PO events built (PO not found for this DC/SKU).")
else:
    for e in confirmed:
        print(f"  cases={e['cases']}  timing_known={e['timing_known']}  "
              f"projection_delivery_date={e.get('projection_delivery_date')}  "
              f"distributor_eta={e.get('distributor_expected_delivery_date')}  "
              f"skuba_eta={e.get('skuba_expected_delivery_date')}  "
              f"overdue={e.get('is_overdue')}")

# --- Gate 2: do they become line inbounds? ------------------------------------
expected_events = _build_expected_order_events(
    row=row, expected_orders=expected_orders, as_of_date=pd.Timestamp(as_of_date)
)
inbounds = _get_projection_inbounds(confirmed, expected_events)
po_inbounds = [i for i in inbounds if i["type"] == "confirmed_po_delivery"]
print("\n--- GATE 2: _get_projection_inbounds (confirmed_po only) ---")
if not po_inbounds:
    print("  -> confirmed PO produced NO line inbound "
          "(dropped for missing timing_known / projection_delivery_date).")
else:
    for i in po_inbounds:
        print(f"  date={i['date'].date()}  cases={i['cases']}")

# --- Gate 3: does the PO land inside the truncated window? ---------------------
proj = build_inventory_projection(
    row=row,
    expected_orders=expected_orders,
    purchase_orders=purchase_orders,
    as_of_date=as_of_date,
    floor_weeks=3,
    tolerance_weeks=0.5,
)
series = pd.DataFrame(proj["series"])
window_end = series["date"].iloc[-1] if not series.empty else None
print("\n--- GATE 3: truncated window ---")
print(f"  window end: {window_end}")
if po_inbounds:
    for i in po_inbounds:
        inside = str(i["date"].date()) <= str(window_end)
        print(f"  PO delivery {i['date'].date()} inside window? {inside}")

# --- did the line actually move on the PO date? -------------------------------
print("\n--- SERIES around any PO delivery ---")
print(series.to_string(index=False))
print("\nconfirmed_pos in projection payload:")
print(proj["confirmed_pos"])
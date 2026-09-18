from __future__ import annotations

import pandas as pd

from backend.metrics.inventory.replenishment_metrics import (
    calculate_replenishment_lead_time,
    resolve_replenishment_lead_time,
)


# =============================================================================
# HELPERS
# =============================================================================


def _safe_number(value) -> float | None:
    value = pd.to_numeric(value, errors="coerce")

    if pd.isna(value):
        return None

    return float(value)


def _latest_inventory_rows(
    inventory_history: pd.DataFrame,
) -> pd.DataFrame:
    """
    Return the latest observed inventory row for each
    distributor x DC x SKU.

    This is a factual snapshot helper only. It does not project inventory
    forward or apply recommendation logic.
    """

    if inventory_history is None or inventory_history.empty:
        return pd.DataFrame()

    df = inventory_history.copy()

    df["report_date"] = pd.to_datetime(
        df["report_date"],
        errors="coerce",
    )

    df = df[df["report_date"].notna()].copy()

    if df.empty:
        return df

    return (
        df.sort_values("report_date")
        .groupby(
            ["distributor", "dc", "sku"],
            as_index=False,
        )
        .tail(1)
        .reset_index(drop=True)
    )


def _build_open_po_cases_lookup(
    purchase_orders: pd.DataFrame | None,
) -> pd.DataFrame:
    """
    Sum currently OPEN purchase-order cases by distributor x DC x SKU.

    The transformed Purchase Orders file is the source of truth for current
    committed PO quantity. RECEIVED/CLOSED rows are never counted.

    Staleness is intentionally not inferred here. This dashboard is factual:
    it reports what the current PO file says is still OPEN. Planning treatment
    of overdue/stale POs remains the responsibility of the assessment engine.
    """

    columns = [
        "distributor",
        "dc",
        "sku",
        "open_po_cases",
    ]

    if purchase_orders is None or purchase_orders.empty:
        return pd.DataFrame(columns=columns)

    po = purchase_orders.copy()

    required = {
        "distributor",
        "dc",
        "sku",
        "open_quantity_cases",
    }

    if not required.issubset(po.columns):
        return pd.DataFrame(columns=columns)

    po["open_quantity_cases"] = pd.to_numeric(
        po["open_quantity_cases"],
        errors="coerce",
    ).fillna(0)

    if "po_status" in po.columns:
        po = po[
            po["po_status"]
            .astype(str)
            .str.strip()
            .str.upper()
            .eq("OPEN")
        ].copy()

    po = po[po["open_quantity_cases"] > 0].copy()

    if po.empty:
        return pd.DataFrame(columns=columns)

    return (
        po.groupby(
            ["distributor", "dc", "sku"],
            as_index=False,
        )["open_quantity_cases"]
        .sum()
        .rename(
            columns={
                "open_quantity_cases": "open_po_cases",
            }
        )
    )


def _count_unfi_oos_events(
    inventory_history: pd.DataFrame,
    as_of_date: pd.Timestamp,
    lookback_months: int = 6,
) -> pd.DataFrame:
    """
    Count observed UNFI stockout events by distributor x DC x SKU.

    An event begins when an observed inventory series enters QOH <= 0.
    Consecutive zero observations are one event. If inventory recovers above
    zero and later returns to zero, that is a new event.

    The first observation inside the six-month window is counted as the start
    of an event when it is already OOS. This means the metric answers:
        "How many distinct OOS episodes were observed during this window?"

    Missing QOH observations do not create an event and do not reset an
    existing OOS episode.
    """

    columns = [
        "distributor",
        "dc",
        "sku",
        "oos_events_l6m",
    ]

    if inventory_history is None or inventory_history.empty:
        return pd.DataFrame(columns=columns)

    df = inventory_history.copy()

    required = {
        "distributor",
        "dc",
        "sku",
        "report_date",
        "quantity_on_hand_cases",
    }

    if not required.issubset(df.columns):
        return pd.DataFrame(columns=columns)

    df["report_date"] = pd.to_datetime(
        df["report_date"],
        errors="coerce",
    ).dt.normalize()

    df["quantity_on_hand_cases"] = pd.to_numeric(
        df["quantity_on_hand_cases"],
        errors="coerce",
    )

    window_start = (
        pd.Timestamp(as_of_date).normalize()
        - pd.DateOffset(months=lookback_months)
    )

    df = df[
        df["distributor"]
        .astype(str)
        .str.strip()
        .str.upper()
        .eq("UNFI")
        & df["report_date"].between(
            window_start,
            pd.Timestamp(as_of_date).normalize(),
            inclusive="both",
        )
    ].copy()

    if df.empty:
        return pd.DataFrame(columns=columns)

    rows = []

    for (distributor, dc, sku), group in df.groupby(
        ["distributor", "dc", "sku"],
        dropna=False,
    ):
        group = (
            group.sort_values("report_date")
            .reset_index(drop=True)
        )

        event_count = 0
        currently_oos = False
        has_known_state = False

        for _, row in group.iterrows():
            qoh = row["quantity_on_hand_cases"]

            if pd.isna(qoh):
                continue

            is_oos = qoh <= 0

            if not has_known_state:
                if is_oos:
                    event_count += 1

                currently_oos = is_oos
                has_known_state = True
                continue

            if is_oos and not currently_oos:
                event_count += 1

            currently_oos = is_oos

        rows.append(
            {
                "distributor": distributor,
                "dc": dc,
                "sku": sku,
                "oos_events_l6m": int(event_count),
            }
        )

    return pd.DataFrame(rows, columns=columns)


def _build_oos_lookup(
    latest_inventory: pd.DataFrame,
    inventory_history: pd.DataFrame,
    as_of_date: pd.Timestamp,
    lookback_months: int = 6,
) -> pd.DataFrame:
    """
    Build the distributor x DC x SKU OOS metric used by the dashboard.

    UNFI:
        Uses observed inventory history over the trailing six months.

    KeHE / distributors without history:
        Uses current OOS only:
            current QOH <= 0 -> 1
            current QOH > 0  -> 0

        These rows are explicitly flagged as incomplete history so the API/UI
        never has to interpret a zero as proof of zero historical stockouts.
    """

    columns = [
        "distributor",
        "dc",
        "sku",
        "oos_events_l6m",
        "oos_history_complete",
    ]

    if latest_inventory is None or latest_inventory.empty:
        return pd.DataFrame(columns=columns)

    latest = latest_inventory.copy()

    latest["quantity_on_hand_cases"] = pd.to_numeric(
        latest.get("quantity_on_hand_cases"),
        errors="coerce",
    )

    unfi_events = _count_unfi_oos_events(
        inventory_history=inventory_history,
        as_of_date=as_of_date,
        lookback_months=lookback_months,
    )

    unfi_lookup = {
        (
            str(row["distributor"]),
            str(row["dc"]),
            str(row["sku"]),
        ): int(row["oos_events_l6m"])
        for _, row in unfi_events.iterrows()
    }

    rows = []

    for _, row in latest.iterrows():
        distributor = str(row["distributor"])
        dc = str(row["dc"])
        sku = str(row["sku"])

        qoh = pd.to_numeric(
            row.get("quantity_on_hand_cases"),
            errors="coerce",
        )

        if distributor.strip().upper() == "UNFI":
            event_count = unfi_lookup.get(
                (distributor, dc, sku),
                0,
            )
            history_complete = True
        else:
            event_count = (
                1
                if pd.notna(qoh) and qoh <= 0
                else 0
            )
            history_complete = False

        rows.append(
            {
                "distributor": distributor,
                "dc": dc,
                "sku": sku,
                "oos_events_l6m": int(event_count),
                "oos_history_complete": history_complete,
            }
        )

    return pd.DataFrame(rows, columns=columns)


def _calculate_current_sku_facts(
    latest_inventory: pd.DataFrame,
    features_df: pd.DataFrame,
    purchase_orders: pd.DataFrame | None,
) -> pd.DataFrame:
    """
    Add current factual inventory metrics at distributor x DC x SKU.

    Velocity is sourced from the existing sales-derived DC velocity metric.
    Open PO quantity is sourced from the current transformed PO file.

    No inventory projection, breach classification, or recommendation logic
    is performed here.
    """

    if latest_inventory is None or latest_inventory.empty:
        return pd.DataFrame()

    df = latest_inventory.copy()

    dc_velocity = (
        features_df[
            ["distributor", "dc", "sku", "dc_weekly_velocity"]
        ]
        .drop_duplicates(
            subset=["distributor", "dc", "sku"]
        )
        .copy()
    )

    dc_velocity["dc_weekly_velocity"] = pd.to_numeric(
        dc_velocity["dc_weekly_velocity"],
        errors="coerce",
    )

    df = df.drop(
        columns=["dc_weekly_velocity"],
        errors="ignore",
    )

    df = df.merge(
        dc_velocity,
        on=["distributor", "dc", "sku"],
        how="left",
    )

    for col in [
        "quantity_on_hand_cases",
        "quantity_on_hand_units",
        "units_per_case",
        "dc_weekly_velocity",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce",
            )

    # Prefer the canonical units field when it exists. Otherwise derive
    # physical units from QOH cases x units per case.
    if "quantity_on_hand_units" not in df.columns:
        df["quantity_on_hand_units"] = (
            df["quantity_on_hand_cases"]
            * df["units_per_case"]
        )

    open_po = _build_open_po_cases_lookup(
        purchase_orders
    )

    df = df.merge(
        open_po,
        on=["distributor", "dc", "sku"],
        how="left",
    )

    df["open_po_cases"] = pd.to_numeric(
        df["open_po_cases"],
        errors="coerce",
    ).fillna(0)

    df["velocity_cases_per_week"] = (
        df["dc_weekly_velocity"]
        / df["units_per_case"]
    )

    invalid_velocity = (
        df["dc_weekly_velocity"].isna()
        | df["dc_weekly_velocity"].le(0)
        | df["units_per_case"].isna()
        | df["units_per_case"].le(0)
    )

    df.loc[
        invalid_velocity,
        "velocity_cases_per_week",
    ] = pd.NA

    df["weeks_on_hand"] = (
        df["quantity_on_hand_cases"]
        / df["velocity_cases_per_week"]
    )

    df.loc[
        df["velocity_cases_per_week"].isna()
        | df["velocity_cases_per_week"].le(0),
        "weeks_on_hand",
    ] = pd.NA

    # Same temporary relevance concept already used elsewhere:
    # sales history OR physical inventory OR current open PO.
    df["is_relevant_dc_sku"] = (
        df["dc_weekly_velocity"].notna()
        | df["quantity_on_hand_cases"].fillna(0).gt(0)
        | df["open_po_cases"].fillna(0).gt(0)
    )

    return df


# =============================================================================
# SKU-LEVEL FACTUAL SNAPSHOT
# =============================================================================


def build_dc_sku_inventory_snapshot(
    inventory_history: pd.DataFrame,
    features_df: pd.DataFrame,
    purchase_orders: pd.DataFrame | None = None,
    as_of_date=None,
    lookback_months: int = 6,
) -> pd.DataFrame:
    """
    Build the factual current-state dataset at distributor x DC x SKU.

    This is intentionally separate from SKUba's inventory assessment engine.

    It answers:
        "What is true right now?"

    It does NOT answer:
        "What should the client do?"
    """

    if inventory_history is None or inventory_history.empty:
        return pd.DataFrame()

    history = inventory_history.copy()

    history["report_date"] = pd.to_datetime(
        history["report_date"],
        errors="coerce",
    ).dt.normalize()

    valid_dates = history["report_date"].dropna()

    if valid_dates.empty:
        return pd.DataFrame()

    if as_of_date is None:
        as_of_date = valid_dates.max()
    else:
        as_of_date = pd.Timestamp(
            as_of_date
        ).normalize()

    # Never allow observations after the requested snapshot date to leak
    # into the factual snapshot.
    history_through_as_of = history[
        history["report_date"] <= as_of_date
    ].copy()

    latest = _latest_inventory_rows(
        history_through_as_of
    )

    if latest.empty:
        return pd.DataFrame()

    facts = _calculate_current_sku_facts(
        latest_inventory=latest,
        features_df=features_df,
        purchase_orders=purchase_orders,
    )

    oos = _build_oos_lookup(
        latest_inventory=latest,
        inventory_history=history_through_as_of,
        as_of_date=as_of_date,
        lookback_months=lookback_months,
    )

    facts = facts.merge(
        oos,
        on=["distributor", "dc", "sku"],
        how="left",
    )

    facts = facts[
        facts["is_relevant_dc_sku"]
    ].copy()

    # Purely descriptive inventory bands for the network dashboard.
    # These are not assessment-engine urgency/status classifications.
    #
    # OOS is its own factual state and is mutually exclusive from
    # the WOH-based inventory bands.
    facts["inventory_band"] = pd.NA

    current_oos = (
        facts["quantity_on_hand_cases"].notna()
        & facts["quantity_on_hand_cases"].le(0)
    )

    facts.loc[
        current_oos,
        "inventory_band",
    ] = "oos"

    facts.loc[
        ~current_oos
        & facts["weeks_on_hand"].notna()
        & facts["weeks_on_hand"].lt(3),
        "inventory_band",
    ] = "below_3_woh"

    facts.loc[
        ~current_oos
        & facts["weeks_on_hand"].notna()
        & facts["weeks_on_hand"].ge(3)
        & facts["weeks_on_hand"].lt(4),
        "inventory_band",
    ] = "3_to_4_woh"

    facts.loc[
        ~current_oos
        & facts["weeks_on_hand"].notna()
        & facts["weeks_on_hand"].ge(4),
        "inventory_band",
    ] = "4_plus_woh"

    facts.loc[
        ~current_oos
        & facts["weeks_on_hand"].isna(),
        "inventory_band",
    ] = "woh_unavailable"

    facts["as_of_date"] = as_of_date

    keep = [
        "as_of_date",
        "report_date",
        "distributor",
        "dc",
        "sku",
        "quantity_on_hand_cases",
        "open_po_cases",
        "velocity_cases_per_week",
        "weeks_on_hand",
        "units_per_case",
        "oos_events_l6m",
        "oos_history_complete",
        "inventory_band",
    ]

    keep = [
        col
        for col in keep
        if col in facts.columns
    ]

    return (
        facts[keep]
        .sort_values(
            ["distributor", "dc", "sku"]
        )
        .reset_index(drop=True)
    )


# =============================================================================
# DC-LEVEL FACTUAL SNAPSHOT
# =============================================================================


def build_dc_inventory_snapshot(
    inventory_history: pd.DataFrame,
    features_df: pd.DataFrame,
    purchase_orders: pd.DataFrame | None = None,
    as_of_date=None,
    lookback_months: int = 6,
) -> pd.DataFrame:
    """
    Aggregate the factual SKU snapshot to one row per distributor x DC.
    """

    sku_facts = build_dc_sku_inventory_snapshot(
        inventory_history=inventory_history,
        features_df=features_df,
        purchase_orders=purchase_orders,
        as_of_date=as_of_date,
        lookback_months=lookback_months,
    )

    if sku_facts.empty:
        return pd.DataFrame()

    rows = []

    for (distributor, dc), group in sku_facts.groupby(
        ["distributor", "dc"],
        sort=True,
    ):
        qoh = pd.to_numeric(
            group["quantity_on_hand_cases"],
            errors="coerce",
        ).fillna(0)

        open_po = pd.to_numeric(
            group["open_po_cases"],
            errors="coerce",
        ).fillna(0)

        velocity = pd.to_numeric(
            group["velocity_cases_per_week"],
            errors="coerce",
        )

        total_qoh = float(qoh.sum())
        total_open_po = float(open_po.sum())
        total_velocity = float(
            velocity.fillna(0).sum()
        )

        network_woh = (
            total_qoh / total_velocity
            if total_velocity > 0
            else None
        )

        rows.append(
            {
                "as_of_date": group["as_of_date"].iloc[0],
                "report_date": group["report_date"].max(),
                "distributor": distributor,
                "dc": dc,
                "quantity_on_hand_cases": total_qoh,
                "quantity_on_po_cases": total_open_po,
                "velocity_cases_per_week": total_velocity,
                "weeks_on_hand": network_woh,
                "sku_count": int(len(group)),
                "skus_oos": int(
                    group["inventory_band"]
                    .eq("oos")
                    .sum()
                ),
                "skus_below_3_woh": int(
                    group["inventory_band"]
                    .eq("below_3_woh")
                    .sum()
                ),
                "skus_3_to_4_woh": int(
                    group["inventory_band"]
                    .eq("3_to_4_woh")
                    .sum()
                ),
                "skus_4_plus_woh": int(
                    group["inventory_band"]
                    .eq("4_plus_woh")
                    .sum()
                ),
                "skus_woh_unavailable": int(
                    group["inventory_band"]
                    .eq("woh_unavailable")
                    .sum()
                ),
                "oos_events_l6m": int(
                    pd.to_numeric(
                        group["oos_events_l6m"],
                        errors="coerce",
                    )
                    .fillna(0)
                    .sum()
                ),
                "oos_history_complete": bool(
                    group["oos_history_complete"]
                    .fillna(False)
                    .all()
                ),
            }
        )

    dc_snapshot = pd.DataFrame(rows)

    # Reuse the exact observed/fallback lead-time policy already used by
    # SKUba rather than defining another lead-time metric here.
    lead_times = calculate_replenishment_lead_time(
        inventory_history
    )

    lead_days = []
    lead_sources = []

    for _, row in dc_snapshot.iterrows():
        resolved = resolve_replenishment_lead_time(
            distributor=row["distributor"],
            dc=row["dc"],
            lead_times=lead_times,
        )

        lead_days.append(
            resolved.get("lead_time_days")
        )
        lead_sources.append(
            resolved.get("lead_time_source")
        )

    dc_snapshot["planning_lead_time_days"] = (
        lead_days
    )
    dc_snapshot["planning_lead_time_source"] = (
        lead_sources
    )

    return dc_snapshot.reset_index(drop=True)


# =============================================================================
# NETWORK-LEVEL FACTUAL SNAPSHOT
# =============================================================================


def build_dc_network_snapshot(
    inventory_history: pd.DataFrame,
    features_df: pd.DataFrame,
    purchase_orders: pd.DataFrame | None = None,
    as_of_date=None,
    lookback_months: int = 6,
) -> dict:
    """
    Build the complete factual payload for the DC network dashboard.

    Output:
        {
            "as_of_date": ...,
            "summary": {...},
            "distribution_centers": [...]
        }

    No recommendation, urgency, intervention, or breach classifications are
    included.
    """

    dc_snapshot = build_dc_inventory_snapshot(
        inventory_history=inventory_history,
        features_df=features_df,
        purchase_orders=purchase_orders,
        as_of_date=as_of_date,
        lookback_months=lookback_months,
    )

    if dc_snapshot.empty:
        return {
            "as_of_date": None,
            "summary": {
                "quantity_on_hand_cases": 0.0,
                "quantity_on_po_cases": 0.0,
                "network_woh": None,
                "active_dc_count": 0,
                "sku_count": 0,
                "oos_events_l6m": 0,
            },
            "distribution_centers": [],
        }

    total_qoh = float(
        dc_snapshot[
            "quantity_on_hand_cases"
        ].sum()
    )

    total_open_po = float(
        dc_snapshot[
            "quantity_on_po_cases"
        ].sum()
    )

    total_velocity = float(
        dc_snapshot[
            "velocity_cases_per_week"
        ].sum()
    )

    network_woh = (
        total_qoh / total_velocity
        if total_velocity > 0
        else None
    )

    as_of = pd.Timestamp(
        dc_snapshot["as_of_date"].iloc[0]
    ).normalize()

    records = []

    for record in dc_snapshot.to_dict(
        orient="records"
    ):
        cleaned = {}

        for key, value in record.items():
            if isinstance(value, pd.Timestamp):
                cleaned[key] = value.strftime(
                    "%Y-%m-%d"
                )
            elif pd.isna(value):
                cleaned[key] = None
            elif hasattr(value, "item"):
                cleaned[key] = value.item()
            else:
                cleaned[key] = value

        records.append(cleaned)

    return {
        "as_of_date": as_of.strftime("%Y-%m-%d"),
        "summary": {
            "quantity_on_hand_cases": total_qoh,
            "quantity_on_po_cases": total_open_po,
            "network_woh": network_woh,
            "active_dc_count": int(
                len(dc_snapshot)
            ),
            "sku_count": int(
                dc_snapshot["sku_count"].sum()
            ),
            "oos_events_l6m": int(
                dc_snapshot[
                    "oos_events_l6m"
                ].sum()
            ),
        },
        "distribution_centers": records,
    }

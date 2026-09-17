import pandas as pd


def find_po_events(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df["distributor"] == "UNFI"].copy()
    df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")

    events = []

    for (distributor, dc, sku), group in df.groupby(
        ["distributor", "dc", "sku"]
    ):
        group = group.sort_values("report_date").reset_index(drop=True)

        for i in range(1, len(group)):
            previous = group.iloc[i - 1]
            current = group.iloc[i]

            previous_po = previous["quantity_on_purchase_order_cases"]
            current_po = current["quantity_on_purchase_order_cases"]
            current_on_hand = current["quantity_on_hand_cases"]

            if (
                pd.isna(previous_po)
                or pd.isna(current_po)
                or pd.isna(current_on_hand)
            ):
                continue

            # Start of a new PO cycle:
            # this SKU/DC previously had nothing on PO
            # and now has product on PO.
            if previous_po == 0 and current_po > 0:
                events.append(
                    {
                        "distributor": distributor,
                        "dc": dc,
                        "sku": sku,
                        "po_date": current["report_date"],
                        "on_hand_cases_at_order": float(current_on_hand),
                        "po_quantity_cases": float(current_po),
                    }
                )

    return pd.DataFrame(events)

def evaluate_po_cycles(
    df: pd.DataFrame,
    po_events: pd.DataFrame,
) -> pd.DataFrame:
    df = df.copy()
    df["report_date"] = pd.to_datetime(
        df["report_date"],
        errors="coerce",
    )

    po_events = po_events.copy()
    po_events["po_date"] = pd.to_datetime(
        po_events["po_date"],
        errors="coerce",
    )

    cycles = []

    for _, event in po_events.iterrows():
        distributor = event["distributor"]
        dc = event["dc"]
        sku = event["sku"]
        po_date = event["po_date"]

        history = (
            df[
                (df["distributor"] == distributor)
                & (df["dc"] == dc)
                & (df["sku"] == sku)
                & (df["report_date"] >= po_date)
            ]
            .sort_values("report_date")
            .reset_index(drop=True)
        )

        receipt_date = pd.NaT
        stockout_date = pd.NaT

        # -----------------------------------------
        # Find first observed receipt
        # -----------------------------------------
        for i in range(1, len(history)):
            previous = history.iloc[i - 1]
            current = history.iloc[i]

            previous_po = previous[
                "quantity_on_purchase_order_cases"
            ]
            current_po = current[
                "quantity_on_purchase_order_cases"
            ]

            previous_on_hand = previous[
                "quantity_on_hand_cases"
            ]
            current_on_hand = current[
                "quantity_on_hand_cases"
            ]

            if (
                pd.isna(previous_po)
                or pd.isna(current_po)
                or pd.isna(previous_on_hand)
                or pd.isna(current_on_hand)
            ):
                continue

            if (
                current_po < previous_po
                and current_on_hand > previous_on_hand
            ):
                receipt_date = current["report_date"]
                break

        # -----------------------------------------
        # Incomplete PO cycle
        # -----------------------------------------
        if pd.isna(receipt_date):
            cycles.append(
                {
                    "distributor": distributor,
                    "dc": dc,
                    "sku": sku,
                    "po_date": po_date,
                    "po_quantity_cases": event[
                        "po_quantity_cases"
                    ],
                    "on_hand_cases_at_order": event[
                        "on_hand_cases_at_order"
                    ],
                    "receipt_date": pd.NaT,
                    "days_to_receipt": float("nan"),
                    "stocked_out_before_receipt": pd.NA,
                    "stockout_date": pd.NaT,
                    "days_stocked_out_before_receipt": float("nan"),
                }
            )
            continue

        # -----------------------------------------
        # Look for first stockout before receipt
        # -----------------------------------------
        pre_receipt_history = history[
            (history["report_date"] >= po_date)
            & (history["report_date"] < receipt_date)
        ]

        stockout_rows = pre_receipt_history[
            pre_receipt_history[
                "quantity_on_hand_cases"
            ] == 0
        ]

        stocked_out_before_receipt = not stockout_rows.empty

        if stocked_out_before_receipt:
            stockout_date = stockout_rows.iloc[0]["report_date"]

            days_stocked_out_before_receipt = (
                receipt_date - stockout_date
            ).days
        else:
            days_stocked_out_before_receipt = 0

        cycles.append(
            {
                "distributor": distributor,
                "dc": dc,
                "sku": sku,
                "po_date": po_date,
                "po_quantity_cases": event[
                    "po_quantity_cases"
                ],
                "on_hand_cases_at_order": event[
                    "on_hand_cases_at_order"
                ],
                "receipt_date": receipt_date,
                "days_to_receipt": (
                    receipt_date - po_date
                ).days,
                "stocked_out_before_receipt":
                    stocked_out_before_receipt,
                "stockout_date": stockout_date,
                "days_stocked_out_before_receipt":
                    days_stocked_out_before_receipt,
            }
        )

    return pd.DataFrame(cycles)

def find_replenishment_events(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df["distributor"] == "UNFI"].copy()
    df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")

    events = []

    for (dc, sku), group in df.groupby(["dc", "sku"]):
        group = group.sort_values("report_date").reset_index(drop=True)

        last_po_increase_date = None

        for i in range(1, len(group)):
            previous = group.iloc[i - 1]
            current = group.iloc[i]

            previous_po = previous["quantity_on_purchase_order_cases"]
            current_po = current["quantity_on_purchase_order_cases"]

            previous_on_hand = previous["quantity_on_hand_cases"]
            current_on_hand = current["quantity_on_hand_cases"]

            if (
                pd.isna(previous_po)
                or pd.isna(current_po)
                or pd.isna(previous_on_hand)
                or pd.isna(current_on_hand)
            ):
                continue

            po_change = current_po - previous_po
            on_hand_change = current_on_hand - previous_on_hand

            # Most recent observed increase in open PO balance
            if po_change > 0:
                last_po_increase_date = current["report_date"]

            # First likely delivery after the observed PO increase
            if (
                po_change < 0
                and on_hand_change > 0
                and last_po_increase_date is not None
            ):
                replenishment_days = (
                    current["report_date"] - last_po_increase_date
                ).days

                events.append(
                    {
                        "distributor": "UNFI",
                        "dc": dc,
                        "sku": sku,
                        "order_date": last_po_increase_date,
                        "receipt_date": current["report_date"],
                        "replenishment_days": replenishment_days,
                        "po_cases_decrease": abs(float(po_change)),
                        "on_hand_cases_increase": float(on_hand_change),
                        "po_cases_before_receipt": float(previous_po),
                        "po_cases_after_receipt": float(current_po),
                        "on_hand_cases_before_receipt": float(previous_on_hand),
                        "on_hand_cases_after_receipt": float(current_on_hand),
                    }
                )

                # Only measure the first observed delivery for this PO increase
                last_po_increase_date = None

    return pd.DataFrame(events)


def calculate_replenishment_lead_time(
    df: pd.DataFrame,
) -> pd.DataFrame:
    events = find_replenishment_events(df)

    if events.empty:
        return pd.DataFrame(
            columns=[
                "distributor",
                "dc",
                "median_replenishment_days",
                "average_replenishment_days",
                "replenishment_event_count",
            ]
        )

    dc_lead_times = (
        events.groupby(
            ["distributor", "dc"],
            as_index=False,
        )
        .agg(
            median_replenishment_days=(
                "replenishment_days",
                "median",
            ),
            average_replenishment_days=(
                "replenishment_days",
                "mean",
            ),
            replenishment_event_count=(
                "replenishment_days",
                "count",
            ),
        )
    )

    overall_unfi = pd.DataFrame(
        [
            {
                "distributor": "UNFI",
                "dc": "__DEFAULT__",
                "median_replenishment_days": (
                    events["replenishment_days"].median()
                ),
                "average_replenishment_days": (
                    events["replenishment_days"].mean()
                ),
                "replenishment_event_count": len(events),
            }
        ]
    )

    return pd.concat(
        [dc_lead_times, overall_unfi],
        ignore_index=True,
    )

def calculate_replenishment_target_quantity(df: pd.DataFrame) -> pd.DataFrame:
    events = find_replenishment_events(df)

    if events.empty:
        return pd.DataFrame(
            columns=[
                "distributor",
                "dc",
                "sku",
                "median_replenishment_target_cases",
                "average_replenishment_target_cases",
                "replenishment_event_count",
            ]
        )

    return (
        events.groupby(["distributor", "dc", "sku"], as_index=False)
        .agg(
            median_replenishment_target_cases=(
                "on_hand_cases_after_receipt",
                "median",
            ),
            average_replenishment_target_cases=(
                "on_hand_cases_after_receipt",
                "mean",
            ),
            replenishment_event_count=(
                "on_hand_cases_after_receipt",
                "count",
            ),
        )
    )

def calculate_expected_delivery_date(df: pd.DataFrame, order_date_col: str = "order_date") -> pd.DataFrame:
    df = df.copy()
    df[order_date_col] = pd.to_datetime(df[order_date_col], errors="coerce")
    df["expected_delivery_date"] = df[order_date_col] + pd.to_timedelta(df["median_replenishment_days"], unit="D")
    return df

def resolve_replenishment_lead_time(
    distributor: str,
    dc: str,
    lead_times: pd.DataFrame,
) -> dict:
    """
    Resolve the planning lead time for a distributor/DC.

    Hierarchy:
    1. Observed distributor/DC median
    2. Overall UNFI observed median fallback

    Lead times are rounded UP to the nearest whole day.

    KeHE temporarily uses the overall UNFI fallback when
    KeHE-specific observed lead time is unavailable.
    """

    import math

    distributor = str(distributor).strip().upper()
    dc = str(dc).strip().upper()

    # --------------------------------------------------------------
    # 1. Distributor / DC-specific observed lead time
    # --------------------------------------------------------------

    dc_match = lead_times[
        (
            lead_times["distributor"]
            .astype(str)
            .str.strip()
            .str.upper()
            == distributor
        )
        & (
            lead_times["dc"]
            .astype(str)
            .str.strip()
            .str.upper()
            == dc
        )
    ]

    if not dc_match.empty:
        lead_days = pd.to_numeric(
            dc_match.iloc[0]["median_replenishment_days"],
            errors="coerce",
        )

        if pd.notna(lead_days) and lead_days > 0:
            return {
                "lead_time_days": int(math.ceil(lead_days)),
                "lead_time_source": "observed_dc",
            }

    # --------------------------------------------------------------
    # 2. Overall UNFI fallback
    # --------------------------------------------------------------

    default_match = lead_times[
        (
            lead_times["distributor"]
            .astype(str)
            .str.strip()
            .str.upper()
            == "UNFI"
        )
        & (
            lead_times["dc"]
            .astype(str)
            .str.strip()
            .str.upper()
            == "__DEFAULT__"
        )
    ]

    if not default_match.empty:
        lead_days = pd.to_numeric(
            default_match.iloc[0]["median_replenishment_days"],
            errors="coerce",
        )

        if pd.notna(lead_days) and lead_days > 0:
            return {
                "lead_time_days": int(math.ceil(lead_days)),
                "lead_time_source": "unfi_overall_fallback",
            }

    return {
        "lead_time_days": None,
        "lead_time_source": "unavailable",
    }
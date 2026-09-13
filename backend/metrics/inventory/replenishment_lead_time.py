import pandas as pd


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


def calculate_replenishment_lead_time(df: pd.DataFrame) -> pd.DataFrame:
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

    return (
        events.groupby(["distributor", "dc"], as_index=False)
        .agg(
            median_replenishment_days=("replenishment_days", "median"),
            average_replenishment_days=("replenishment_days", "mean"),
            replenishment_event_count=("replenishment_days", "count"),
        )
    )
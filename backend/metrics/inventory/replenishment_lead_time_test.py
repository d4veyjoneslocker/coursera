import pandas as pd

from backend.metrics.inventory.replenishment_lead_time import (
    find_replenishment_events,
    calculate_replenishment_lead_time,
)

pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)

INPUT_PATH = "backend/data/default_org/inventory_combined.parquet"


def main():
    df = pd.read_parquet(INPUT_PATH)

    # -----------------------------
    # Detected replenishment events
    # -----------------------------
    events = find_replenishment_events(df)

    print("\nReplenishment events found:", len(events))

    if not events.empty:
        print(
            events[
                [
                    "dc",
                    "sku",
                    "order_date",
                    "receipt_date",
                    "replenishment_days",
                    "po_cases_before_receipt",
                    "po_cases_after_receipt",
                    "on_hand_cases_before_receipt",
                    "on_hand_cases_after_receipt",
                ]
            ]
            .sort_values(["dc", "sku", "receipt_date"])
            .to_string(index=False)
        )

    # -----------------------------
    # DC-level lead time summary
    # -----------------------------
    summary = calculate_replenishment_lead_time(df)

    print("\nReplenishment lead time by DC:")

    if not summary.empty:
        print(
            summary.sort_values("dc")
            .to_string(index=False)
        )

    # -----------------------------
    # Basic QA
    # -----------------------------
    if not events.empty:
        print("\nLead time distribution:")
        print(events["replenishment_days"].describe())

        print("\nEvents by DC:")
        print(
            events["dc"]
            .value_counts()
            .sort_index()
        )

        print("\nShortest events:")
        print(
            events.sort_values("replenishment_days")
            .head(20)
            .to_string(index=False)
        )

        print("\nLongest events:")
        print(
            events.sort_values("replenishment_days", ascending=False)
            .head(20)
            .to_string(index=False)
        )


if __name__ == "__main__":
    main()
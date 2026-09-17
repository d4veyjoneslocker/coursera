import pandas as pd

from backend.metrics.inventory.replenishment_metrics import (
    find_po_events,
    evaluate_po_cycles,
)

INPUT_PATH = "backend/data/default_org/inventory_combined.parquet"
OUTPUT_PATH = "backend/data/default_org/how_mocha_joe_daily_history.csv"


def main():
    df = pd.read_parquet(INPUT_PATH)

    df["report_date"] = pd.to_datetime(
        df["report_date"],
        errors="coerce",
    )

    # Optional: still run these so we can compare the detected events/cycles
    po_events = find_po_events(df)
    po_cycles = evaluate_po_cycles(df, po_events)

    # --------------------------------------------------
    # Full daily history for HOW / MOCHA JOE
    # --------------------------------------------------
    history = (
        df[
            (df["distributor"] == "UNFI")
            & (df["dc"] == "HOW")
            & (df["sku"] == "MOCHA JOE")
        ]
        .sort_values("report_date")
        .copy()
    )

    # Add useful day-over-day changes
    history["qoh_change_cases"] = (
        history["quantity_on_hand_cases"].diff()
    )

    history["po_change_cases"] = (
        history["quantity_on_purchase_order_cases"].diff()
    )

    # Flag detected PO starts
    how_mocha_events = po_events[
        (po_events["distributor"] == "UNFI")
        & (po_events["dc"] == "HOW")
        & (po_events["sku"] == "MOCHA JOE")
    ][
        [
            "po_date",
            "po_quantity_cases",
            "on_hand_cases_at_order",
        ]
    ].copy()

    how_mocha_events["po_event"] = True

    history = history.merge(
        how_mocha_events,
        left_on="report_date",
        right_on="po_date",
        how="left",
        suffixes=("", "_event"),
    )

    history["po_event"] = history["po_event"].fillna(False)

    # Keep a clean set of columns if present
    preferred_columns = [
        "report_date",
        "distributor",
        "dc",
        "sku",
        "quantity_on_hand_cases",
        "qoh_change_cases",
        "quantity_on_purchase_order_cases",
        "po_change_cases",
        "quantity_on_sales_order_cases",
        "lead_time_weeks",
        "po_event",
        "po_quantity_cases",
        "on_hand_cases_at_order",
    ]

    output_columns = [
        col
        for col in preferred_columns
        if col in history.columns
    ]

    history[output_columns].to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print(f"\nSaved daily history to:")
    print(OUTPUT_PATH)

    # --------------------------------------------------
    # Specifically print 2/26 through 3/26
    # --------------------------------------------------
    window = history[
        (history["report_date"] >= "2026-02-26")
        & (history["report_date"] <= "2026-03-26")
    ]

    print("\nHOW / MOCHA JOE — 2026-02-26 through 2026-03-26:")
    print(
        window[output_columns].to_string(index=False)
    )

    # --------------------------------------------------
    # Print every QOH increase in that window
    # --------------------------------------------------
    qoh_increases = window[
        window["qoh_change_cases"] > 0
    ]

    print("\nQOH increases between 2/26 and 3/26:")
    if qoh_increases.empty:
        print("None")
    else:
        print(
            qoh_increases[
                [
                    "report_date",
                    "quantity_on_hand_cases",
                    "qoh_change_cases",
                    "quantity_on_purchase_order_cases",
                    "po_change_cases",
                ]
            ].to_string(index=False)
        )


if __name__ == "__main__":
    main()
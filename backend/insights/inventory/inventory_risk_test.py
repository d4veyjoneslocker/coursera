import pandas as pd

from backend.insights.inventory.inventory_risk import run_inventory_risk

pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)

FEATURES_PATH = "backend/data/default_org/inventory_features_test.csv"
HISTORY_PATH = "backend/data/default_org/inventory_combined.parquet"


def main():
    df = pd.read_csv(FEATURES_PATH)
    inventory_history = pd.read_parquet(HISTORY_PATH)

    inventory = run_inventory_risk(
        df,
        inventory_history=inventory_history,
    )

    print("\nLead time assumptions:")
    print(
        inventory[
            [
                "distributor",
                "dc",
                "planning_lead_time_days",
                "replenishment_event_count",
                "lead_time_source",
            ]
        ]
        .drop_duplicates()
        .sort_values(["distributor", "dc"])
        .to_string(index=False)
    )

    print("\nInventory summary:")
    print("Total relevant:", len(inventory))
    print("Orders to monitor:", inventory["monitor_inbound"].sum())
    print("Orders to place:", inventory["order_needed"].sum())
    print(
        "No active demand:",
        (inventory["current_inventory_state"] == "no_active_demand").sum(),
    )
    print(
        "Lead time risk:",
        inventory["lead_time_risk"].sum(),
    )

    print("\nInventory states:")
    print(
        inventory["current_inventory_state"]
        .value_counts()
        .to_string()
    )

    print("\nUrgency:")
    print(
        inventory["inventory_urgency"]
        .value_counts()
        .to_string()
    )

    orders = inventory[
        inventory["order_needed"]
    ].copy()

    print("\nTop 10 orders to place:")

    if not orders.empty:
        print(
            orders[
                [
                    "distributor",
                    "dc",
                    "sku",
                    "calculated_weeks_on_hand",
                    "planning_lead_time_days",
                    "recommended_cases_to_send",
                ]
            ]
            .sort_values("calculated_weeks_on_hand")
            .head(10)
            .to_string(index=False)
        )


if __name__ == "__main__":
    main()
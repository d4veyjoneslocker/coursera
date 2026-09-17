import numpy as np
import pandas as pd


def calculate_recommended_orders(df: pd.DataFrame, floor_weeks: float = 3, target_weeks: float = 5) -> pd.DataFrame:
    df = df.copy()

    df["velocity_cases_per_week"] = df["dc_weekly_velocity"] / df["units_per_case"]
    df["projected_weeks_at_delivery"] = df["projected_cases_at_delivery"] / df["velocity_cases_per_week"]
    df["target_cases_at_delivery"] = df["velocity_cases_per_week"] * target_weeks

    can_calculate = df["velocity_cases_per_week"].gt(0) & df["projected_cases_at_delivery"].notna()
    needs_order = can_calculate & df["projected_weeks_at_delivery"].lt(floor_weeks)
    recommendation = np.ceil((df["target_cases_at_delivery"] - df["projected_cases_at_delivery"]).clip(lower=0).astype(float))

    df["recommended_order_cases"] = np.where(~can_calculate, np.nan, np.where(needs_order, recommendation, 0))

    mask = (df["distributor"] == "UNFI") & (df["dc"] == "GRW") & (df["sku"] == "STRAWBERRY")
    if mask.any():
        r = df[mask].iloc[0]
        print("\n--- GRW STRAWBERRY REC MATH ---")
        print("row quantity_on_hand_cases:", r["quantity_on_hand_cases"])
        print("velocity_cases_per_week:  ", r["velocity_cases_per_week"])
        print("projected_cases_at_delivery:", r["projected_cases_at_delivery"])
        print("projected_weeks_at_delivery:", r["projected_weeks_at_delivery"])
        print("target_cases_at_delivery:  ", r["target_cases_at_delivery"], f"(target_weeks × velocity)")
        print("recommended_order_cases:   ", r["recommended_order_cases"])

    return df


def calculate_recommended_order_for_date(
    df: pd.DataFrame,
    purchase_orders: pd.DataFrame,
    order_date,
    target_weeks: float = 5,
) -> pd.DataFrame:
    df = df.copy()
    order_date = pd.Timestamp(order_date).normalize()

    results = []

    for _, row in df.iterrows():
        result = row.copy()

        lead_days = row["median_replenishment_days"]
        velocity_cases_per_week = row["dc_weekly_velocity"] / row["units_per_case"]

        if pd.isna(lead_days) or pd.isna(velocity_cases_per_week) or velocity_cases_per_week <= 0 or pd.isna(row["quantity_on_hand_cases"]):
            result["projected_cases_at_delivery"] = np.nan
            results.append(result)
            continue

        report_date = pd.Timestamp(row["report_date"]).normalize()
        delivery_date = order_date + pd.to_timedelta(lead_days, unit="D")
        inventory = float(row["quantity_on_hand_cases"])

        current_date = report_date

        po = purchase_orders[
            (purchase_orders["distributor"] == row["distributor"])
            & (purchase_orders["dc"] == row["dc"])
            & (purchase_orders["sku"] == row["sku"])
            & purchase_orders["open_quantity_cases"].gt(0)
        ].copy()

        if not po.empty:
            po["receipt_date"] = pd.to_datetime(po["po_create_date"]).dt.normalize() + pd.to_timedelta(lead_days, unit="D")
            po = po[(po["receipt_date"] >= report_date) & (po["receipt_date"] <= delivery_date)].groupby("receipt_date", as_index=False)["open_quantity_cases"].sum().sort_values("receipt_date")

            for _, event in po.iterrows():
                weeks_elapsed = max((event["receipt_date"] - current_date).days, 0) / 7
                inventory = max(inventory - (velocity_cases_per_week * weeks_elapsed), 0)
                inventory += event["open_quantity_cases"]
                current_date = event["receipt_date"]


        if row["distributor"] == "UNFI" and row["dc"] == "GRW" and row["sku"] == "STRAWBERRY":
            print("\n--- GRW STRAW PROJECTION DEBUG - PRE INVENTORY ---")
            print("order_date:      ", order_date)
            print("report_date:     ", report_date)
            print("delivery_date:   ", delivery_date)
            print("lead_days:       ", lead_days)
            print("start inventory: ", inventory)
            print("po rows found:   ", len(po))



        weeks_elapsed = max((delivery_date - current_date).days, 0) / 7
        inventory = max(inventory - (velocity_cases_per_week * weeks_elapsed), 0)

        result["order_date"] = order_date
        result["expected_delivery_date"] = delivery_date
        result["projected_cases_at_delivery"] = inventory
        results.append(result)

    out = pd.DataFrame(results)

    if row["distributor"] == "UNFI" and row["dc"] == "GRW" and row["sku"] == "STRAWBERRY":
        print("\n--- GRW STRAW PROJECTION DEBUG ---")
        print("order_date:      ", order_date)
        print("report_date:     ", report_date)
        print("delivery_date:   ", delivery_date)
        print("lead_days:       ", lead_days)
        print("start inventory: ", inventory)
        print("po rows found:   ", len(po))

    return calculate_recommended_orders(out, target_weeks=target_weeks)
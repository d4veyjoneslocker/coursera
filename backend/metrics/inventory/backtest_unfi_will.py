from pathlib import Path

import numpy as np
import pandas as pd

from backend.transforms.inventory.unfi import transform_unfi_purchase_orders


BASE_DIR = Path(__file__).resolve().parents[2]
ORG_ID = "default_org"

PO_PATH = BASE_DIR / "data" / ORG_ID / "raw" / "inventory" / "unfi" / "Purchase Orders.csv"
INVENTORY_PATH = BASE_DIR / "data" / ORG_ID / "inventory_planning_backtest.csv"
OUTPUT_PATH = BASE_DIR / "data" / ORG_ID / "unfi_will_combined_range_backtest.csv"

RECENT_ORDERS = 5
MIN_HISTORY_ORDERS = 3
CLIFF_FILTERS = [None, 3, 5, 10]


def prepare_pos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in ["po_create_date", "received_date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.normalize()

    df["original_quantity_cases"] = pd.to_numeric(
        df["original_quantity_cases"], errors="coerce"
    )

    return (
        df.loc[
            df["po_create_date"].notna()
            & df["original_quantity_cases"].gt(0)
        ]
        .sort_values(["dc", "sku", "po_create_date"])
        .reset_index(drop=True)
    )


def prepare_inventory(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["test_date"] = pd.to_datetime(df["test_date"], errors="coerce").dt.normalize()

    for col in ["qoh_cases", "qpo_cases", "velocity_cases_per_week"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return (
        df.loc[df["test_date"].notna()]
        .sort_values(["dc", "sku", "test_date"])
        .reset_index(drop=True)
    )


def add_inventory_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["previous_date"] = df.groupby(["dc", "sku"])["test_date"].shift()
    df["previous_qoh"] = df.groupby(["dc", "sku"])["qoh_cases"].shift()

    df["days_since_snapshot"] = (
        df["test_date"] - df["previous_date"]
    ).dt.days

    df["observed_depletion_cases"] = (
        df["previous_qoh"] - df["qoh_cases"]
    ).clip(lower=0)

    df["expected_depletion_cases"] = (
        df["velocity_cases_per_week"]
        * df["days_since_snapshot"]
        / 7
    )

    df["depletion_multiple"] = np.where(
        df["expected_depletion_cases"].gt(0),
        df["observed_depletion_cases"] / df["expected_depletion_cases"],
        np.nan,
    )

    df["woh"] = np.where(
        df["velocity_cases_per_week"].gt(0),
        df["qoh_cases"] / df["velocity_cases_per_week"],
        np.nan,
    )

    return df


def latest_inventory_state(
    inventory_group: pd.DataFrame,
    date: pd.Timestamp,
) -> pd.Series | None:
    eligible = inventory_group.loc[
        inventory_group["test_date"] <= date
    ]

    if eligible.empty:
        return None

    return eligible.iloc[-1]


def get_temporal_predictions(
    history: pd.DataFrame,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    # Skip the initial-load interval.
    recurring = history.iloc[1:].copy()

    creation_intervals = (
        recurring["po_create_date"]
        .diff()
        .dt.days
        .dropna()
        .tail(RECENT_ORDERS)
    )

    creation_cadence = (
        creation_intervals.median()
        if len(creation_intervals)
        else np.nan
    )

    creation_prediction = (
        history.iloc[-1]["po_create_date"]
        + pd.to_timedelta(creation_cadence, unit="D")
        if pd.notna(creation_cadence)
        else pd.NaT
    )

    delivery_intervals = []

    # PO2 receipt -> PO3 creation is the first recurring interval.
    for i in range(2, len(history)):
        previous_receipt = history.iloc[i - 1]["received_date"]
        current_creation = history.iloc[i]["po_create_date"]

        if pd.notna(previous_receipt) and pd.notna(current_creation):
            delivery_intervals.append(
                (current_creation - previous_receipt).days
            )

    delivery_intervals = delivery_intervals[-RECENT_ORDERS:]

    delivery_cadence = (
        np.median(delivery_intervals)
        if delivery_intervals
        else np.nan
    )

    last_receipt = history.iloc[-1]["received_date"]

    delivery_prediction = (
        last_receipt
        + pd.to_timedelta(delivery_cadence, unit="D")
        if pd.notna(last_receipt)
        and pd.notna(delivery_cadence)
        else pd.NaT
    )

    return creation_prediction, delivery_prediction


def historical_reorder_woh(
    history: pd.DataFrame,
    inventory_group: pd.DataFrame,
    cliff_multiple: float | None,
) -> tuple[float, int]:
    values = []

    # Skip first observed PO because it may be initial fill / launch behavior.
    for i in range(1, len(history)):
        po_date = history.iloc[i]["po_create_date"]
        state = latest_inventory_state(inventory_group, po_date)

        if state is None:
            continue

        if pd.isna(state["woh"]) or state["woh"] < 0:
            continue

        if (
            cliff_multiple is not None
            and pd.notna(state["depletion_multiple"])
            and state["depletion_multiple"] > cliff_multiple
        ):
            continue

        values.append(state["woh"])

    if not values:
        return np.nan, 0

    recent = values[-RECENT_ORDERS:]

    return float(np.median(recent)), len(values)


def inventory_prediction(
    history: pd.DataFrame,
    inventory_group: pd.DataFrame,
    reorder_woh: float,
) -> pd.Timestamp:
    if pd.isna(reorder_woh):
        return pd.NaT

    last_po = history.iloc[-1]
    receipt_date = last_po["received_date"]

    # Respect the existing PO cycle. We only start predicting the
    # following reorder after the most recent PO has been received.
    if pd.isna(receipt_date):
        return pd.NaT

    state = latest_inventory_state(
        inventory_group,
        receipt_date,
    )

    if state is None:
        return pd.NaT

    qoh = state["qoh_cases"]
    velocity = state["velocity_cases_per_week"]

    if pd.isna(qoh) or pd.isna(velocity) or velocity <= 0:
        return pd.NaT

    reorder_cases = reorder_woh * velocity
    cases_until_reorder = qoh - reorder_cases

    if cases_until_reorder <= 0:
        return receipt_date

    days_until_reorder = (
        cases_until_reorder / velocity * 7
    )

    return (
        receipt_date
        + pd.to_timedelta(days_until_reorder, unit="D")
    )


def build_range(
    creation_prediction: pd.Timestamp,
    delivery_prediction: pd.Timestamp,
    inventory_prediction_date: pd.Timestamp,
) -> tuple[pd.Timestamp, pd.Timestamp, int]:
    predictions = [
        x
        for x in [
            creation_prediction,
            delivery_prediction,
            inventory_prediction_date,
        ]
        if pd.notna(x)
    ]

    if len(predictions) < 2:
        return pd.NaT, pd.NaT, len(predictions)

    return min(predictions), max(predictions), len(predictions)


def range_metrics(
    actual_date: pd.Timestamp,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> dict:
    if pd.isna(start) or pd.isna(end):
        return {
            "range_width_days": np.nan,
            "inside_range": False,
            "inside_range_3d": False,
            "inside_range_7d": False,
            "distance_from_range_days": np.nan,
            "miss_direction": None,
        }

    width = (end - start).days

    if actual_date < start:
        distance = (start - actual_date).days
        direction = "early"
    elif actual_date > end:
        distance = (actual_date - end).days
        direction = "late"
    else:
        distance = 0
        direction = "inside"

    return {
        "range_width_days": width,
        "inside_range": distance == 0,
        "inside_range_3d": distance <= 3,
        "inside_range_7d": distance <= 7,
        "distance_from_range_days": distance,
        "miss_direction": direction,
    }


def build_tests(
    purchase_orders: pd.DataFrame,
    inventory: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    inventory_groups = {
        key: group.reset_index(drop=True)
        for key, group in inventory.groupby(["dc", "sku"])
    }

    for (dc, sku), po_group in purchase_orders.groupby(["dc", "sku"]):
        po_group = (
            po_group
            .sort_values("po_create_date")
            .reset_index(drop=True)
        )

        inventory_group = inventory_groups.get((dc, sku))

        if inventory_group is None:
            continue

        if len(po_group) < MIN_HISTORY_ORDERS + 1:
            continue

        for test_idx in range(
            MIN_HISTORY_ORDERS,
            len(po_group),
        ):
            history = po_group.iloc[:test_idx].copy()
            actual = po_group.iloc[test_idx]
            actual_date = actual["po_create_date"]

            creation_pred, delivery_pred = (
                get_temporal_predictions(history)
            )

            temporal_predictions = [
                x
                for x in [
                    creation_pred,
                    delivery_pred,
                ]
                if pd.notna(x)
            ]

            temporal_start = (
                min(temporal_predictions)
                if temporal_predictions
                else pd.NaT
            )

            temporal_end = (
                max(temporal_predictions)
                if temporal_predictions
                else pd.NaT
            )

            temporal_metrics = range_metrics(
                actual_date,
                temporal_start,
                temporal_end,
            )

            for cliff_multiple in CLIFF_FILTERS:
                reorder_woh, reorder_history_n = (
                    historical_reorder_woh(
                        history,
                        inventory_group,
                        cliff_multiple,
                    )
                )

                inventory_pred = inventory_prediction(
                    history,
                    inventory_group,
                    reorder_woh,
                )

                combined_start, combined_end, signal_count = (
                    build_range(
                        creation_pred,
                        delivery_pred,
                        inventory_pred,
                    )
                )

                combined_metrics = range_metrics(
                    actual_date,
                    combined_start,
                    combined_end,
                )

                rows.append({
                    "dc": dc,
                    "sku": sku,
                    "actual_order_date": actual_date,
                    "history_orders": len(history),

                    "cliff_filter": (
                        "none"
                        if cliff_multiple is None
                        else f"{cliff_multiple}x"
                    ),

                    "reorder_woh": reorder_woh,
                    "reorder_history_n": reorder_history_n,

                    "creation_prediction": creation_pred,
                    "delivery_prediction": delivery_pred,
                    "inventory_prediction": inventory_pred,

                    "temporal_start": temporal_start,
                    "temporal_end": temporal_end,
                    "temporal_width_days":
                        temporal_metrics["range_width_days"],
                    "temporal_inside":
                        temporal_metrics["inside_range"],
                    "temporal_inside_3d":
                        temporal_metrics["inside_range_3d"],
                    "temporal_inside_7d":
                        temporal_metrics["inside_range_7d"],
                    "temporal_distance_days":
                        temporal_metrics["distance_from_range_days"],

                    "combined_start": combined_start,
                    "combined_end": combined_end,
                    "combined_signal_count": signal_count,
                    "combined_width_days":
                        combined_metrics["range_width_days"],
                    "combined_inside":
                        combined_metrics["inside_range"],
                    "combined_inside_3d":
                        combined_metrics["inside_range_3d"],
                    "combined_inside_7d":
                        combined_metrics["inside_range_7d"],
                    "combined_distance_days":
                        combined_metrics["distance_from_range_days"],
                    "combined_miss_direction":
                        combined_metrics["miss_direction"],
                })

    return pd.DataFrame(rows)


def summarize_range(
    df: pd.DataFrame,
    prefix: str,
) -> dict:
    valid = df.loc[
        df[f"{prefix}_width_days"].notna()
    ].copy()

    if valid.empty:
        return {
            "n": 0,
            "exact_capture": np.nan,
            "capture_3d": np.nan,
            "capture_7d": np.nan,
            "median_width": np.nan,
            "mean_width": np.nan,
            "median_distance": np.nan,
            "mean_distance": np.nan,
        }

    return {
        "n": len(valid),
        "exact_capture":
            valid[f"{prefix}_inside"].mean(),
        "capture_3d":
            valid[f"{prefix}_inside_3d"].mean(),
        "capture_7d":
            valid[f"{prefix}_inside_7d"].mean(),
        "median_width":
            valid[f"{prefix}_width_days"].median(),
        "mean_width":
            valid[f"{prefix}_width_days"].mean(),
        "median_distance":
            valid[f"{prefix}_distance_days"].median(),
        "mean_distance":
            valid[f"{prefix}_distance_days"].mean(),
    }


def compare_ranges(
    results: pd.DataFrame,
    cliff_filter: str,
) -> pd.DataFrame:
    df = results.loc[
        results["cliff_filter"] == cliff_filter
    ].copy()

    rows = []

    for name, prefix in [
        ("temporal_only", "temporal"),
        ("temporal_plus_inventory", "combined"),
    ]:
        metrics = summarize_range(df, prefix)

        rows.append({
            "model": name,
            **metrics,
        })

    return pd.DataFrame(rows)


def summarize_filters(
    results: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    for cliff_filter, group in results.groupby(
        "cliff_filter",
        sort=False,
    ):
        metrics = summarize_range(
            group,
            "combined",
        )

        rows.append({
            "cliff_filter": cliff_filter,
            **metrics,
        })

    return pd.DataFrame(rows)


def summarize_history(
    results: pd.DataFrame,
    cliff_filter: str,
) -> pd.DataFrame:
    df = results.loc[
        results["cliff_filter"] == cliff_filter
    ].copy()

    df["history_bucket"] = pd.cut(
        df["history_orders"],
        bins=[2, 3, 5, 8, np.inf],
        labels=["3", "4-5", "6-8", "9+"],
    )

    rows = []

    for bucket, group in df.groupby(
        "history_bucket",
        observed=True,
    ):
        temporal = summarize_range(
            group,
            "temporal",
        )

        combined = summarize_range(
            group,
            "combined",
        )

        rows.append({
            "history_orders": bucket,
            "n": len(group),

            "temporal_exact":
                temporal["exact_capture"],
            "temporal_3d":
                temporal["capture_3d"],
            "temporal_7d":
                temporal["capture_7d"],
            "temporal_median_width":
                temporal["median_width"],

            "combined_exact":
                combined["exact_capture"],
            "combined_3d":
                combined["capture_3d"],
            "combined_7d":
                combined["capture_7d"],
            "combined_median_width":
                combined["median_width"],

            "median_reorder_woh":
                group["reorder_woh"].median(),
        })

    return pd.DataFrame(rows)


def summarize_width_buckets(
    results: pd.DataFrame,
    cliff_filter: str,
) -> pd.DataFrame:
    df = results.loc[
        (results["cliff_filter"] == cliff_filter)
        & results["combined_width_days"].notna()
    ].copy()

    df["width_bucket"] = pd.cut(
        df["combined_width_days"],
        bins=[-1, 7, 14, 21, 35, np.inf],
        labels=[
            "0-7",
            "8-14",
            "15-21",
            "22-35",
            "36+",
        ],
    )

    rows = []

    for bucket, group in df.groupby(
        "width_bucket",
        observed=True,
    ):
        metrics = summarize_range(
            group,
            "combined",
        )

        rows.append({
            "window_width": bucket,
            **metrics,
        })

    return pd.DataFrame(rows)


def format_percentages(
    df: pd.DataFrame,
) -> pd.DataFrame:
    df = df.copy()

    percentage_cols = [
        "exact_capture",
        "capture_3d",
        "capture_7d",
        "temporal_exact",
        "temporal_3d",
        "temporal_7d",
        "combined_exact",
        "combined_3d",
        "combined_7d",
    ]

    for col in percentage_cols:
        if col in df.columns:
            df[col] = df[col].map(
                lambda x: (
                    f"{x:.1%}"
                    if pd.notna(x)
                    else ""
                )
            )

    return df


if __name__ == "__main__":
    print(
        "\n=== UNFI WILL: COMBINED EXPECTED-ORDER RANGE ===\n"
    )

    raw_po = pd.read_csv(PO_PATH)

    purchase_orders = prepare_pos(
        transform_unfi_purchase_orders(
            raw_po,
            org_id=ORG_ID,
        )
    )

    inventory = prepare_inventory(
        pd.read_csv(INVENTORY_PATH)
    )

    inventory = add_inventory_features(
        inventory
    )

    results = build_tests(
        purchase_orders,
        inventory,
    )

    if results.empty:
        raise ValueError(
            "No eligible WILL observations found."
        )

    observations = (
        results[
            ["dc", "sku", "actual_order_date"]
        ]
        .drop_duplicates()
        .shape[0]
    )

    combinations = (
        results[
            ["dc", "sku"]
        ]
        .drop_duplicates()
        .shape[0]
    )

    print(
        f"Walk-forward observations: {observations:,}"
    )
    print(
        f"DC × SKU combinations: {combinations:,}"
    )

    print(
        "\n=== TEMPORAL VS COMBINED — 3X CLIFF FILTER ===\n"
    )

    print(
        format_percentages(
            compare_ranges(
                results,
                "3x",
            )
        ).to_string(index=False)
    )

    print(
        "\n=== COMBINED RANGE BY CLIFF FILTER ===\n"
    )

    print(
        format_percentages(
            summarize_filters(
                results
            )
        ).to_string(index=False)
    )

    print(
        "\n=== BY HISTORY DEPTH — 3X CLIFF FILTER ===\n"
    )

    print(
        format_percentages(
            summarize_history(
                results,
                "3x",
            )
        ).to_string(index=False)
    )

    print(
        "\n=== COMBINED RANGE BY WINDOW WIDTH — 3X CLIFF FILTER ===\n"
    )

    print(
        format_percentages(
            summarize_width_buckets(
                results,
                "3x",
            )
        ).to_string(index=False)
    )

    miss_counts = (
        results.loc[
            results["cliff_filter"] == "3x",
            "combined_miss_direction",
        ]
        .value_counts()
    )

    print(
        "\n=== COMBINED MISS DIRECTION — 3X ===\n"
    )
    print(miss_counts.to_string())

    results.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print(
        f"\nDetailed predictions saved to: "
        f"{OUTPUT_PATH}"
    )
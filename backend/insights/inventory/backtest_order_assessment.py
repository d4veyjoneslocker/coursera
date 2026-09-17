from pathlib import Path

import numpy as np
import pandas as pd


ORG_ID = "default_org"
BASE_DIR = Path("backend/data") / ORG_ID

INVENTORY_PATH = BASE_DIR / "inventory_features_test.csv"
BACKTEST_PATH = BASE_DIR / "inventory_planning_backtest.csv"
OUTPUT_PATH = BASE_DIR / "inventory_policy_backtest.csv"
SUMMARY_PATH = BASE_DIR / "inventory_policy_summary.csv"

LOOKBACK_DAYS = 60

POLICIES = [
    (2, 4),
    (2, 5),
    (3, 4),
    (3, 5),
    (3, 6),
    (4, 5),
    (4, 6),
]

LEAD_TIME_SCENARIOS = {
    "normal": 0,
    "plus_3_days": 3,
    "plus_7_days": 7,
}


def prepare_inventory(inventory: pd.DataFrame) -> pd.DataFrame:
    df = inventory[inventory["distributor"] == "UNFI"].copy()
    df["report_date"] = pd.to_datetime(df["report_date"]).dt.normalize()
    df = df.sort_values(["dc", "sku", "report_date"])

    df["previous_qoh"] = df.groupby(["dc", "sku"])["quantity_on_hand_cases"].shift(1)
    df["oos_start"] = df["previous_qoh"].gt(0) & df["quantity_on_hand_cases"].fillna(0).le(0)

    oos_pairs = df.loc[df["oos_start"], ["dc", "sku"]].drop_duplicates()

    return df.merge(oos_pairs, on=["dc", "sku"], how="inner")


def prepare_snapshots(snapshots: pd.DataFrame, inventory: pd.DataFrame) -> pd.DataFrame:
    df = snapshots.copy()
    df["test_date"] = pd.to_datetime(df["test_date"]).dt.normalize()

    oos_pairs = inventory[["dc", "sku"]].drop_duplicates()

    return df.merge(oos_pairs, on=["dc", "sku"], how="inner")


def calculate_policy_recommendations(
    snapshots: pd.DataFrame,
    floor_weeks: float,
    target_weeks: float,
) -> pd.DataFrame:
    df = snapshots.copy()

    velocity = pd.to_numeric(df["velocity_cases_per_week"], errors="coerce")
    qoh = pd.to_numeric(df["qoh_cases"], errors="coerce")
    qpo = pd.to_numeric(df["qpo_cases"], errors="coerce")
    lead_days = pd.to_numeric(df["lead_time_days"], errors="coerce")

    projected_cases = (
        qoh
        + qpo
        - velocity * lead_days / 7
    ).clip(lower=0)

    projected_weeks = projected_cases / velocity
    target_cases = velocity * target_weeks

    can_calculate = (
        velocity.gt(0)
        & qoh.notna()
        & qpo.notna()
        & lead_days.notna()
    )

    needs_order = can_calculate & projected_weeks.lt(floor_weeks)

    recommendation = np.ceil(
        (target_cases - projected_cases).clip(lower=0)
    )

    df["projected_cases_at_delivery"] = projected_cases
    df["projected_weeks_at_delivery"] = projected_weeks

    df["recommended_cases"] = np.where(
        ~can_calculate,
        np.nan,
        np.where(needs_order, recommendation, 0),
    )

    df["floor_weeks"] = floor_weeks
    df["target_weeks"] = target_weeks

    return df


def find_oos_incidents(inventory: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for (dc, sku), group in inventory.groupby(["dc", "sku"], sort=False):
        group = group.sort_values("report_date").reset_index(drop=True)
        oos_indices = group.index[group["oos_start"]].tolist()

        for incident_number, idx in enumerate(oos_indices, start=1):
            oos_date = group.loc[idx, "report_date"]

            previous_oos_idx = (
                oos_indices[incident_number - 2]
                if incident_number > 1
                else None
            )

            previous_oos_date = (
                group.loc[previous_oos_idx, "report_date"]
                if previous_oos_idx is not None
                else pd.NaT
            )

            recovery_date = pd.NaT

            if previous_oos_idx is not None:
                between = group[
                    (group.index > previous_oos_idx)
                    & (group.index < idx)
                    & group["quantity_on_hand_cases"].gt(0)
                ]

                if not between.empty:
                    recovery_date = between.iloc[0]["report_date"]

            lookback_start = oos_date - pd.Timedelta(days=LOOKBACK_DAYS)

            if pd.notna(recovery_date):
                cycle_start = max(lookback_start, recovery_date)
            else:
                cycle_start = lookback_start

            rows.append({
                "dc": dc,
                "sku": sku,
                "incident_number": incident_number,
                "previous_oos_date": previous_oos_date,
                "recovery_date": recovery_date,
                "cycle_start": cycle_start,
                "oos_date": oos_date,
            })

    return pd.DataFrame(rows)


def get_cycle_history(
    snapshots: pd.DataFrame,
    dc: str,
    sku: str,
    cycle_start: pd.Timestamp,
    oos_date: pd.Timestamp,
) -> pd.DataFrame:
    return (
        snapshots[
            (snapshots["dc"] == dc)
            & (snapshots["sku"] == sku)
            & (snapshots["test_date"] >= cycle_start)
            & (snapshots["test_date"] < oos_date)
        ]
        .sort_values("test_date")
        .copy()
    )


def get_first_action(history: pd.DataFrame) -> pd.Series | None:
    actions = history[
        history["recommended_cases"].notna()
        & history["recommended_cases"].gt(0)
        & history["lead_time_days"].notna()
    ]

    if actions.empty:
        return None

    return actions.iloc[0]


def get_inventory_path(
    inventory: pd.DataFrame,
    dc: str,
    sku: str,
    action_date: pd.Timestamp,
    oos_date: pd.Timestamp,
) -> pd.DataFrame:
    return (
        inventory[
            (inventory["dc"] == dc)
            & (inventory["sku"] == sku)
            & (inventory["report_date"] >= action_date)
            & (inventory["report_date"] <= oos_date)
        ]
        .sort_values("report_date")
        .copy()
    )


def simulate_incident(
    inventory: pd.DataFrame,
    action: pd.Series,
    incident: pd.Series,
    extra_lead_days: int,
) -> dict:
    dc = incident["dc"]
    sku = incident["sku"]
    oos_date = incident["oos_date"]

    action_date = action["test_date"]
    recommended_cases = float(action["recommended_cases"])
    lead_time_days = int(np.ceil(float(action["lead_time_days"]))) + extra_lead_days
    arrival_date = action_date + pd.Timedelta(days=lead_time_days)

    path = get_inventory_path(
        inventory=inventory,
        dc=dc,
        sku=sku,
        action_date=action_date,
        oos_date=oos_date,
    )

    if path.empty:
        return {
            "status": "not_evaluable",
            "reason": "no_inventory_path",
            "action_date": action_date,
            "recommended_cases": recommended_cases,
            "lead_time_days": lead_time_days,
            "arrival_date": arrival_date,
            "shipment_arrived_before_oos": arrival_date <= oos_date,
            "simulated_qoh_at_oos": np.nan,
            "prevented_oos": np.nan,
        }

    simulated_qoh = float(path.iloc[0]["quantity_on_hand_cases"])
    previous_actual_qoh = float(path.iloc[0]["quantity_on_hand_cases"])

    skuba_received = False
    receipt_offset_remaining = 0.0

    for i, (_, row) in enumerate(path.iterrows()):
        date = row["report_date"]
        actual_qoh = float(row["quantity_on_hand_cases"])

        if not skuba_received and date >= arrival_date:
            simulated_qoh += recommended_cases
            receipt_offset_remaining += recommended_cases
            skuba_received = True

        if i > 0:
            actual_change = actual_qoh - previous_actual_qoh

            if actual_change < 0:
                simulated_qoh += actual_change

            elif actual_change > 0:
                offset = min(actual_change, receipt_offset_remaining)
                simulated_qoh += actual_change - offset
                receipt_offset_remaining -= offset

        previous_actual_qoh = actual_qoh

    prevented_oos = simulated_qoh > 0

    return {
        "status": "prevented" if prevented_oos else "not_prevented",
        "reason": (
            "prevented"
            if prevented_oos
            else (
                "shipment_too_late"
                if arrival_date > oos_date
                else "recommended_quantity_insufficient"
            )
        ),
        "action_date": action_date,
        "warning_days": (oos_date - action_date).days,
        "recommended_cases": recommended_cases,
        "lead_time_days": lead_time_days,
        "arrival_date": arrival_date,
        "shipment_arrived_before_oos": arrival_date <= oos_date,
        "actual_qoh_at_action": path.iloc[0]["quantity_on_hand_cases"],
        "actual_qoh_at_oos": path.iloc[-1]["quantity_on_hand_cases"],
        "remaining_receipt_offset": receipt_offset_remaining,
        "simulated_qoh_at_oos": simulated_qoh,
        "prevented_oos": prevented_oos,
    }


def run_scenario(
    inventory: pd.DataFrame,
    snapshots: pd.DataFrame,
    incidents: pd.DataFrame,
    floor_weeks: float,
    target_weeks: float,
    scenario: str,
    extra_lead_days: int,
) -> pd.DataFrame:
    rows = []

    print(
        f"\nPolicy {floor_weeks}/{target_weeks} | "
        f"{scenario} ({extra_lead_days:+d} lead-time days)"
    )

    for i, incident in incidents.iterrows():
        dc = incident["dc"]
        sku = incident["sku"]
        oos_date = incident["oos_date"]
        cycle_start = incident["cycle_start"]

        print(
            f"\r{i + 1}/{len(incidents)} {dc} | {sku} | {oos_date.date()}",
            end="",
            flush=True,
        )

        history = get_cycle_history(
            snapshots=snapshots,
            dc=dc,
            sku=sku,
            cycle_start=cycle_start,
            oos_date=oos_date,
        )

        base = {
            "floor_weeks": floor_weeks,
            "target_weeks": target_weeks,
            "policy": f"{floor_weeks}/{target_weeks}",
            "scenario": scenario,
            "dc": dc,
            "sku": sku,
            "incident_number": incident["incident_number"],
            "previous_oos_date": incident["previous_oos_date"],
            "recovery_date": incident["recovery_date"],
            "cycle_start": cycle_start,
            "oos_date": oos_date,
        }

        if history.empty:
            rows.append({
                **base,
                "status": "not_evaluable",
                "reason": "no_skuba_history",
                "action_date": pd.NaT,
                "warning_days": np.nan,
                "recommended_cases": np.nan,
                "lead_time_days": np.nan,
                "arrival_date": pd.NaT,
                "shipment_arrived_before_oos": np.nan,
                "actual_qoh_at_action": np.nan,
                "actual_qoh_at_oos": 0,
                "remaining_receipt_offset": np.nan,
                "simulated_qoh_at_oos": np.nan,
                "prevented_oos": np.nan,
            })
            continue

        action = get_first_action(history)

        if action is None:
            has_calculable_recommendation = history["recommended_cases"].notna().any()

            rows.append({
                **base,
                "status": (
                    "not_prevented"
                    if has_calculable_recommendation
                    else "not_evaluable"
                ),
                "reason": (
                    "no_action"
                    if has_calculable_recommendation
                    else "insufficient_history"
                ),
                "action_date": pd.NaT,
                "warning_days": np.nan,
                "recommended_cases": np.nan,
                "lead_time_days": np.nan,
                "arrival_date": pd.NaT,
                "shipment_arrived_before_oos": (
                    False if has_calculable_recommendation else np.nan
                ),
                "actual_qoh_at_action": np.nan,
                "actual_qoh_at_oos": 0,
                "remaining_receipt_offset": np.nan,
                "simulated_qoh_at_oos": (
                    0 if has_calculable_recommendation else np.nan
                ),
                "prevented_oos": (
                    False if has_calculable_recommendation else np.nan
                ),
            })
            continue

        result = simulate_incident(
            inventory=inventory,
            action=action,
            incident=incident,
            extra_lead_days=extra_lead_days,
        )

        rows.append({**base, **result})

    print()

    return pd.DataFrame(rows)


def run_backtest(
    inventory: pd.DataFrame,
    snapshots: pd.DataFrame,
) -> pd.DataFrame:
    inventory = prepare_inventory(inventory)
    snapshots = prepare_snapshots(snapshots, inventory)
    incidents = find_oos_incidents(inventory)

    print(
        f"\nOOS DC × SKU combinations: "
        f"{len(incidents[['dc', 'sku']].drop_duplicates())}"
    )
    print(f"Historical OOS incidents:  {len(incidents)}")

    results = []

    for floor_weeks, target_weeks in POLICIES:
        policy_snapshots = calculate_policy_recommendations(
            snapshots=snapshots,
            floor_weeks=floor_weeks,
            target_weeks=target_weeks,
        )

        for scenario, extra_days in LEAD_TIME_SCENARIOS.items():
            results.append(
                run_scenario(
                    inventory=inventory,
                    snapshots=policy_snapshots,
                    incidents=incidents,
                    floor_weeks=floor_weeks,
                    target_weeks=target_weeks,
                    scenario=scenario,
                    extra_lead_days=extra_days,
                )
            )

    return pd.concat(results, ignore_index=True)

def calculate_policy_inventory_cost(snapshots: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for floor_weeks, target_weeks in POLICIES:
        policy = calculate_policy_recommendations(snapshots, floor_weeks, target_weeks)
        calculable = policy[policy["recommended_cases"].notna()]
        actions = calculable[calculable["recommended_cases"].gt(0)]

        rows.append({
            "floor_weeks": floor_weeks,
            "target_weeks": target_weeks,
            "policy": f"{floor_weeks}/{target_weeks}",
            "calculable_snapshots": len(calculable),
            "action_snapshots": len(actions),
            "action_rate": len(actions) / len(calculable) if len(calculable) else np.nan,
            "total_recommended_cases": actions["recommended_cases"].sum(),
            "average_recommended_cases": actions["recommended_cases"].mean(),
            "median_recommended_cases": actions["recommended_cases"].median(),
        })

    return pd.DataFrame(rows)

def build_summary(results: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for (floor, target, scenario), group in results.groupby(
        ["floor_weeks", "target_weeks", "scenario"],
        sort=False,
    ):
        evaluable = group[group["status"] != "not_evaluable"]

        total = len(group)
        evaluated = len(evaluable)
        prevented = int(evaluable["prevented_oos"].eq(True).sum())
        missed = evaluated - prevented

        rows.append({
            "floor_weeks": floor,
            "target_weeks": target,
            "policy": f"{floor}/{target}",
            "scenario": scenario,
            "historical_oos": total,
            "evaluable_oos": evaluated,
            "not_evaluable": total - evaluated,
            "prevented": prevented,
            "not_prevented": missed,
            "prevention_rate": prevented / evaluated if evaluated else np.nan,
            "shipment_too_late": int(
                evaluable["reason"].eq("shipment_too_late").sum()
            ),
            "no_action": int(
                evaluable["reason"].eq("no_action").sum()
            ),
            "quantity_insufficient": int(
                evaluable["reason"]
                .eq("recommended_quantity_insufficient")
                .sum()
            ),
        })

    return pd.DataFrame(rows)


def summarize_backtest(summary: pd.DataFrame) -> None:
    print("\n=== POLICY COMPARISON ===\n")

    normal = summary[summary["scenario"] == "normal"].copy()
    normal["prevention_rate"] = normal["prevention_rate"].map(
        lambda x: f"{x:.1%}"
    )

    normal["action_rate"] = normal["action_rate"].map(lambda x: f"{x:.1%}")
    normal["recommended_cases_vs_3_5"] = normal["recommended_cases_vs_3_5"].map(
        lambda x: f"{x:+.1%}"
    )

    print(
        normal[
            [
                "policy",
                "evaluable_oos",
                "prevented",
                "not_prevented",
                "prevention_rate",
                "shipment_too_late",
                "no_action",
                "quantity_insufficient",
                "action_rate",
                "total_recommended_cases",
                "recommended_cases_vs_3_5",
            ]
        ].to_string(index=False)
    )

    print("\n=== ALL LEAD-TIME SCENARIOS ===\n")

    display = summary.copy()
    display["prevention_rate"] = display["prevention_rate"].map(
        lambda x: f"{x:.1%}"
    )

    print(
        display[
            [
                "policy",
                "scenario",
                "prevented",
                "evaluable_oos",
                "prevention_rate",
            ]
        ].to_string(index=False)
    )

DIAGNOSTIC_PATH = BASE_DIR / "inventory_3_5_miss_diagnostics.csv"

def build_miss_diagnostics(
    results: pd.DataFrame,
    snapshots: pd.DataFrame,
    days_before_action: int = 14,
    days_before_oos_no_action: int = 30,
) -> pd.DataFrame:
    misses = results[
        (results["policy"] == "3/5")
        & (results["scenario"] == "normal")
        & (results["status"] == "not_prevented")
    ].copy()

    for col in ["cycle_start", "oos_date", "action_date"]:
        misses[col] = pd.to_datetime(misses[col], errors="coerce").dt.normalize()

    policy_snapshots = calculate_policy_recommendations(
        snapshots=snapshots,
        floor_weeks=3,
        target_weeks=5,
    )

    policy_snapshots["test_date"] = pd.to_datetime(
        policy_snapshots["test_date"]
    ).dt.normalize()

    rows = []

    for _, miss in misses.iterrows():
        if pd.notna(miss["action_date"]):
            diagnostic_start = miss["action_date"] - pd.Timedelta(days=days_before_action)
        else:
            diagnostic_start = miss["oos_date"] - pd.Timedelta(days=days_before_oos_no_action)

        diagnostic_start = max(diagnostic_start, miss["cycle_start"])

        history = policy_snapshots[
            (policy_snapshots["dc"] == miss["dc"])
            & (policy_snapshots["sku"] == miss["sku"])
            & (policy_snapshots["test_date"] >= diagnostic_start)
            & (policy_snapshots["test_date"] < miss["oos_date"])
        ].sort_values("test_date").copy()

        if history.empty:
            continue

        history["incident_number"] = miss["incident_number"]
        history["oos_date"] = miss["oos_date"]
        history["miss_reason"] = miss["reason"]
        history["action_date"] = miss["action_date"]
        history["days_until_oos"] = (
            miss["oos_date"] - history["test_date"]
        ).dt.days

        history["days_relative_to_action"] = np.where(
            pd.notna(miss["action_date"]),
            (history["test_date"] - miss["action_date"]).dt.days,
            np.nan,
        )

        history["is_first_action"] = (
            history["test_date"].eq(miss["action_date"])
            if pd.notna(miss["action_date"])
            else False
        )

        rows.append(history)

    if not rows:
        return pd.DataFrame()

    diagnostics = pd.concat(rows, ignore_index=True)

    columns = [
        "dc",
        "sku",
        "incident_number",
        "oos_date",
        "miss_reason",
        "action_date",
        "test_date",
        "days_relative_to_action",
        "days_until_oos",
        "qoh_cases",
        "qpo_cases",
        "velocity_cases_per_week",
        "lead_time_days",
        "projected_cases_at_delivery",
        "projected_weeks_at_delivery",
        "recommended_cases",
        "is_first_action",
    ]

    return diagnostics[columns]

if __name__ == "__main__":
    print("Loading inventory history...")
    inventory = pd.read_csv(INVENTORY_PATH)

    print("Loading historical SKUba snapshots...")
    snapshots = pd.read_csv(BACKTEST_PATH)

    results = run_backtest(inventory, snapshots)
    summary = build_summary(results)
    inventory_cost = calculate_policy_inventory_cost(snapshots)

    summary = summary.merge(
        inventory_cost,
        on=["floor_weeks", "target_weeks", "policy"],
        how="left",
    )

    baseline_cases = inventory_cost.loc[
        inventory_cost["policy"] == "3/5",
        "total_recommended_cases",
    ].iloc[0]

    summary["recommended_cases_vs_3_5"] = (
        summary["total_recommended_cases"] / baseline_cases - 1
    )

    diagnostics = build_miss_diagnostics(
        results=results,
        snapshots=snapshots,
    )

    results.to_csv(OUTPUT_PATH, index=False)
    summary.to_csv(SUMMARY_PATH, index=False)
    diagnostics.to_csv(DIAGNOSTIC_PATH, index=False)

    summarize_backtest(summary)

    print(f"\nSaved detailed results to: {OUTPUT_PATH}")
    print(f"Saved policy summary to:   {SUMMARY_PATH}")
    print(f"Saved miss diagnostics to: {DIAGNOSTIC_PATH}")
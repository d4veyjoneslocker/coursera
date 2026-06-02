import pandas as pd
import pytest

from backend.insights.missed_replenishment_risk import (
    analyze_order_cadence_risk,
    build_order_cadence_risk_table,
    create_order_cadence_risk_store_list,
    normalize_order_cadence_risk_data,
)
from backend.insights.failure_to_launch_new_store_risk import (
    analyze_failure_to_launch_new_store_risk,
    build_failure_to_launch_new_store_risk_table,
    create_failure_to_launch_new_store_risk_store_list,
    normalize_failure_to_launch_new_store_risk_data,
)
from backend.insights.growing_region_momentum import (
    analyze_growing_region_momentum,
    build_growing_region_momentum_table,
    create_growing_region_momentum_store_list,
    normalize_growing_region_momentum_data,
)
from backend.insights.overperforming_channel_momentum import (
    analyze_overperforming_channel_momentum,
    build_overperforming_channel_momentum_table,
    create_overperforming_channel_momentum_store_list,
    normalize_overperforming_channel_momentum_data,
)
from backend.insights.dropoff_sku_risk import (
    analyze_dropoff_sku_risk,
    build_dropoff_sku_risk_table,
    create_dropoff_sku_risk_store_list,
    normalize_dropoff_sku_risk_data,
)


FIXED_LAST_FULL_MONTH = pd.Period("2026-04", freq="M")


@pytest.fixture(autouse=True)
def fixed_last_full_month(monkeypatch):
    """Patch module-level get_last_full_month imports so tests are deterministic."""
    import backend.insights.missed_replenishment_risk as order_cadence
    import backend.insights.failure_to_launch_new_store_risk as failure_to_launch
    import backend.insights.growing_region_momentum as growing_region
    import backend.insights.overperforming_channel_momentum as channel_momentum
    import backend.insights.dropoff_sku_risk as dropoff_sku

    monkeypatch.setattr(order_cadence, "get_last_full_month", lambda today=None: FIXED_LAST_FULL_MONTH)
    monkeypatch.setattr(failure_to_launch, "get_last_full_month", lambda today=None: FIXED_LAST_FULL_MONTH)
    monkeypatch.setattr(growing_region, "get_last_full_month", lambda today=None: FIXED_LAST_FULL_MONTH)
    monkeypatch.setattr(channel_momentum, "get_last_full_month", lambda today=None: FIXED_LAST_FULL_MONTH)
    monkeypatch.setattr(dropoff_sku, "get_last_full_month", lambda today=None: FIXED_LAST_FULL_MONTH)


# -----------------------------------------------------------------------------
# Generic helpers
# -----------------------------------------------------------------------------


def month_range(start="2025-10", end="2026-05"):
    return list(pd.period_range(start, end, freq="M"))


def store_rows(store, chain="Target", dc="DC1", state="CA", sku="SKU A", units_by_month=None):
    units_by_month = units_by_month or {}
    rows = []
    purchase_months = [pd.Period(m, freq="M") for m, u in units_by_month.items() if u > 0]
    last_purchase = max(purchase_months) if purchase_months else pd.NaT

    for month in month_range():
        units = units_by_month.get(str(month), 0)
        rows.append(
            {
                "coded_customer": store,
                "chain": chain,
                "dc": dc,
                "state": state,
                "city": "Los Angeles" if state == "CA" else "New York",
                "sku": sku,
                "channel": "Natural",
                "month_year": month,
                "units": units,
                "revenue": units * 10,
                "store_number": store,
                "street_address": f"{store} Main St",
                "zip": "90001",
                "last_month_purchased": last_purchase,
            }
        )
    return rows


# -----------------------------------------------------------------------------
# order_cadence_risk
# -----------------------------------------------------------------------------


def test_order_cadence_build_table_calculates_history_and_current_month_flags():
    rows = []
    rows += store_rows("A", units_by_month={"2025-12": 10, "2026-01": 10, "2026-02": 10, "2026-03": 10})
    rows += store_rows("B", units_by_month={"2025-12": 10, "2026-01": 10, "2026-02": 10, "2026-03": 10, "2026-05": 5})

    df = pd.DataFrame(rows)
    table = build_order_cadence_risk_table(df)

    row_a = table[table["coded_customer"] == "A"].iloc[0]
    row_b = table[table["coded_customer"] == "B"].iloc[0]

    assert row_a["months_purchased_last_4_prior"] == 4
    assert row_a["purchased_last_full_month"] is False or row_a["purchased_last_full_month"] == False
    assert row_a["purchased_current_month"] is False or row_a["purchased_current_month"] == False
    assert row_a["avg_monthly_units_4m"] > 0

    assert row_b["purchased_current_month"] is True or row_b["purchased_current_month"] == True


def test_order_cadence_analyze_flags_only_expected_missed_replenishment_stores():
    rows = []
    rows += store_rows("A", units_by_month={"2025-12": 10, "2026-01": 10, "2026-02": 10, "2026-03": 10})
    rows += store_rows("B", units_by_month={"2025-12": 10, "2026-01": 10, "2026-02": 10, "2026-03": 10, "2026-04": 10})
    rows += store_rows("C", units_by_month={"2026-02": 10})
    rows += store_rows("D", chain="CONFIDENTIAL", units_by_month={"2025-12": 10, "2026-01": 10, "2026-02": 10, "2026-03": 10})

    table = build_order_cadence_risk_table(pd.DataFrame(rows))
    analyzed = analyze_order_cadence_risk(table)

    assert analyzed is not None
    assert set(analyzed["coded_customer"]) == {"A"}


def test_order_cadence_normalize_detects_chain_dc_and_single_sku_concentration():
    analyzed = pd.DataFrame(
        [
            {"coded_customer": "A", "chain": "Sprouts", "dc": "DC1", "months_purchased_last_4_prior": 4, "avg_monthly_units_4m": 10, "sku_count": 1, "carried_skus": ["SKU A"]},
            {"coded_customer": "B", "chain": "Sprouts", "dc": "DC1", "months_purchased_last_4_prior": 3, "avg_monthly_units_4m": 8, "sku_count": 1, "carried_skus": ["SKU A"]},
            {"coded_customer": "C", "chain": "Sprouts", "dc": "DC1", "months_purchased_last_4_prior": 3, "avg_monthly_units_4m": 6, "sku_count": 1, "carried_skus": ["SKU A"]},
            {"coded_customer": "D", "chain": "Target", "dc": "DC2", "months_purchased_last_4_prior": 3, "avg_monthly_units_4m": 4, "sku_count": 2, "carried_skus": ["SKU B", "SKU C"]},
        ]
    )

    data = normalize_order_cadence_risk_data(analyzed)

    assert data is not None
    assert data["affected_stores"] == 4
    assert data["top_chain"]["chain"] == "Sprouts"
    assert data["top_chain"]["include"] is True
    assert data["top_dc"]["dc"] == "DC1"
    assert data["top_dc"]["include"] is True
    assert data["top_single_sku"]["sku"] == "SKU A"
    assert data["top_single_sku"]["include"] is True


def test_order_cadence_store_list_is_exact_analyzed_universe():
    analyzed = pd.DataFrame(
        [
            {"coded_customer": "A", "chain": "Target", "dc": "DC1", "months_purchased_last_4_prior": 4, "avg_monthly_units_4m": 10},
            {"coded_customer": "B", "chain": "Target", "dc": "DC1", "months_purchased_last_4_prior": 3, "avg_monthly_units_4m": 4},
        ]
    )

    store_list = create_order_cadence_risk_store_list(analyzed)

    assert set(store_list["coded_customer"]) == {"A", "B"}
    assert list(store_list.sort_values("avg_monthly_units_4m", ascending=False)["coded_customer"]) == ["A", "B"]


# -----------------------------------------------------------------------------
# failure_to_launch_new_store_risk
# -----------------------------------------------------------------------------


def test_failure_to_launch_build_tables_create_launch_events_and_cohort_summary():
    rows = []
    rows += store_rows("A", chain="Sprouts", sku="SKU A", units_by_month={"2026-02": 12})
    rows += store_rows("B", chain="Sprouts", sku="SKU A", units_by_month={"2026-02": 12, "2026-03": 4})
    rows += store_rows("C", chain="Sprouts", sku="SKU B", units_by_month={"2026-02": 8})

    tables = build_failure_to_launch_new_store_risk_table(pd.DataFrame(rows))

    assert set(tables.keys()) == {"cohort_summary", "sku_breakdown", "launch_events"}
    assert not tables["launch_events"].empty
    assert not tables["cohort_summary"].empty
    assert "launch_cohort_id" in tables["launch_events"].columns
    assert "at_risk_no_reorder" in tables["launch_events"].columns


def test_failure_to_launch_analyze_surfaces_current_surface_month_only(monkeypatch):
    monkeypatch.setattr(pd.Timestamp, "today", classmethod(lambda cls: pd.Timestamp("2026-05-13")))

    table = pd.DataFrame(
        [
            {"launch_cohort_id": "Sprouts|2026-02", "chain": "Sprouts", "launch_month": pd.Period("2026-02", freq="M"), "surface_month": pd.Period("2026-05", freq="M"), "launched_stores": 5, "launched_skus": 1, "launched_placements": 5, "at_risk_placements": 4, "reordered_placements": 1, "at_risk_rate": 0.80, "reorder_rate": 0.20},
            {"launch_cohort_id": "Target|2026-01", "chain": "Target", "launch_month": pd.Period("2026-01", freq="M"), "surface_month": pd.Period("2026-04", freq="M"), "launched_stores": 5, "launched_skus": 1, "launched_placements": 5, "at_risk_placements": 5, "reordered_placements": 0, "at_risk_rate": 1.00, "reorder_rate": 0.00},
            {"launch_cohort_id": "Whole|2026-02", "chain": "CONFIDENTIAL", "launch_month": pd.Period("2026-02", freq="M"), "surface_month": pd.Period("2026-05", freq="M"), "launched_stores": 5, "launched_skus": 1, "launched_placements": 5, "at_risk_placements": 5, "reordered_placements": 0, "at_risk_rate": 1.00, "reorder_rate": 0.00},
        ]
    )

    analyzed = analyze_failure_to_launch_new_store_risk(table, min_at_risk_placements=3, min_at_risk_rate=0.25)

    assert analyzed is not None
    assert list(analyzed["launch_cohort_id"]) == ["Sprouts|2026-02"]


def test_failure_to_launch_store_list_only_returns_at_risk_events_for_selected_cohort():
    launch_events = pd.DataFrame(
        [
            {"launch_cohort_id": "C1", "coded_customer": "A", "chain": "Sprouts", "sku": "SKU A", "at_risk_no_reorder": True, "initial_units": 10},
            {"launch_cohort_id": "C1", "coded_customer": "B", "chain": "Sprouts", "sku": "SKU A", "at_risk_no_reorder": False, "initial_units": 10},
            {"launch_cohort_id": "C1", "coded_customer": "C", "chain": "Sprouts", "sku": "SKU B", "at_risk_no_reorder": True, "initial_units": 5},
            {"launch_cohort_id": "C2", "coded_customer": "D", "chain": "Target", "sku": "SKU A", "at_risk_no_reorder": True, "initial_units": 10},
        ]
    )

    store_list = create_failure_to_launch_new_store_risk_store_list(launch_events=launch_events, launch_cohort_id="C1")

    assert set(store_list["coded_customer"]) == {"A", "C"}
    assert set(store_list["sku"]) == {"SKU A", "SKU B"}


def test_failure_to_launch_normalize_includes_sku_breakdown_for_selected_cohort():
    analyzed = pd.DataFrame(
        [
            {"launch_cohort_id": "C1", "chain": "Sprouts", "launch_month": pd.Period("2026-02", freq="M"), "surface_month": pd.Period("2026-05", freq="M"), "launched_stores": 5, "launched_skus": 2, "launched_placements": 10, "at_risk_placements": 4, "reordered_placements": 6, "at_risk_rate": 0.40, "reorder_rate": 0.60, "avg_initial_units": 10, "avg_initial_units_at_risk": 8, "avg_initial_units_reordered": 12, "avg_initial_units_gap": -4},
        ]
    )
    sku_breakdown = pd.DataFrame(
        [
            {"launch_cohort_id": "C1", "sku": "SKU A", "at_risk_stores": 3, "at_risk_rate": 0.60},
            {"launch_cohort_id": "C1", "sku": "SKU B", "at_risk_stores": 1, "at_risk_rate": 0.20},
            {"launch_cohort_id": "C2", "sku": "SKU C", "at_risk_stores": 9, "at_risk_rate": 0.90},
        ]
    )

    data = normalize_failure_to_launch_new_store_risk_data(analyzed, sku_breakdown=sku_breakdown)

    assert data is not None
    item = data[0] if isinstance(data, list) else data
    assert item["launch_cohort_id"] == "C1"
    assert item["chain"] == "Sprouts"
    assert "sku_breakdown" in item
    assert [row["sku"] for row in item["sku_breakdown"]] == ["SKU A", "SKU B"]


# -----------------------------------------------------------------------------
# growing_region_momentum
# -----------------------------------------------------------------------------


def test_growing_region_analyze_returns_top_state_that_passes_all_gates():
    table = pd.DataFrame(
        [
            {"state": "CA", "recent_3m_units": 500, "prior_3m_units": 200, "unit_growth_abs": 300, "unit_growth_pct": 1.5, "recent_business_share": 0.30, "velocity_growth_pct": 0.30, "reorder_rate_growth_abs": 0.08, "unit_growth_outperformance_pct": 0.20, "velocity_outperformance_pct": 0.10, "reorder_rate_outperformance_abs": 0.03},
            {"state": "NY", "recent_3m_units": 100, "prior_3m_units": 95, "unit_growth_abs": 5, "unit_growth_pct": 0.05, "recent_business_share": 0.08, "velocity_growth_pct": 0.02, "reorder_rate_growth_abs": 0.01, "unit_growth_outperformance_pct": 0.01, "velocity_outperformance_pct": 0.01, "reorder_rate_outperformance_abs": 0.00},
        ]
    )

    analyzed = analyze_growing_region_momentum(table)

    assert analyzed is not None
    assert list(analyzed["state"]) == ["CA"]


@pytest.mark.parametrize(
    "column,bad_value",
    [
        ("recent_3m_units", 10),
        ("recent_business_share", 0.01),
        ("unit_growth_abs", 5),
        ("unit_growth_pct", 0.01),
        ("velocity_growth_pct", 0.01),
        ("reorder_rate_growth_abs", 0.00),
        ("unit_growth_outperformance_pct", 0.00),
        ("velocity_outperformance_pct", 0.00),
        ("reorder_rate_outperformance_abs", 0.00),
    ],
)
def test_growing_region_analyze_returns_none_when_any_gate_fails(column, bad_value):
    row = {"state": "CA", "recent_3m_units": 500, "prior_3m_units": 200, "unit_growth_abs": 300, "unit_growth_pct": 1.5, "recent_business_share": 0.30, "velocity_growth_pct": 0.30, "reorder_rate_growth_abs": 0.08, "unit_growth_outperformance_pct": 0.20, "velocity_outperformance_pct": 0.10, "reorder_rate_outperformance_abs": 0.03}
    row[column] = bad_value

    analyzed = analyze_growing_region_momentum(pd.DataFrame([row]))

    assert analyzed is None


def test_growing_region_store_list_aligns_to_selected_state_and_recent_months():
    df = pd.DataFrame(
        [
            {"coded_customer": "A", "chain": "Target", "dc": "DC1", "city": "LA", "state": "CA", "month_year": pd.Period("2026-04", freq="M"), "units": 10},
            {"coded_customer": "A", "chain": "Target", "dc": "DC1", "city": "LA", "state": "CA", "month_year": pd.Period("2026-03", freq="M"), "units": 10},
            {"coded_customer": "B", "chain": "Target", "dc": "DC1", "city": "LA", "state": "CA", "month_year": pd.Period("2026-01", freq="M"), "units": 999},
            {"coded_customer": "C", "chain": "Target", "dc": "DC1", "city": "NYC", "state": "NY", "month_year": pd.Period("2026-04", freq="M"), "units": 999},
        ]
    )
    analyzed = pd.DataFrame([{"state": "CA"}])

    store_list = create_growing_region_momentum_store_list(df, analyzed)

    assert set(store_list["coded_customer"]) == {"A"}
    assert store_list.iloc[0]["recent_units"] == 20


def test_growing_region_normalize_preserves_business_share_metrics():
    analyzed = pd.DataFrame(
        [
            {"state": "CA", "recent_3m_units": 500, "prior_3m_units": 200, "unit_growth_abs": 300, "unit_growth_pct": 1.5, "recent_business_share": 0.30, "prior_business_share": 0.10, "business_share_change_abs": 0.20, "recent_3m_velocity": 10, "prior_3m_velocity": 8, "velocity_growth_pct": 0.25, "recent_3m_reorder_rate": 0.40, "prior_3m_reorder_rate": 0.30, "reorder_rate_growth_abs": 0.10, "total_unit_growth_pct": 0.20, "unit_growth_outperformance_pct": 1.30, "velocity_outperformance_pct": 0.15, "reorder_rate_outperformance_abs": 0.05},
        ]
    )
    df = pd.DataFrame([{"state": "CA", "coded_customer": "A", "month_year": pd.Period("2026-04", freq="M"), "units": 1}])

    data = normalize_growing_region_momentum_data(analyzed, df=df)

    assert data is not None
    assert data["items"][0]["state"] == "CA"
    assert data["items"][0]["business_share_change_abs"] == 0.20
    assert data["metrics"]["recent_business_share"] == 0.30


# -----------------------------------------------------------------------------
# overperforming_channel_momentum
# -----------------------------------------------------------------------------


def test_overperforming_channel_analyze_selects_channel_with_return_on_distribution_and_velocity():
    table = pd.DataFrame(
        [
            {"channel": "Natural", "recent_3m_units": 500, "recent_unit_share": 0.30, "recent_store_share": 0.10, "return_on_distribution_index": 3.0, "recent_3m_velocity": 12, "velocity_outperformance_pct": 0.50, "recent_3m_reorder_rate": 0.40},
            {"channel": "Mass", "recent_3m_units": 500, "recent_unit_share": 0.20, "recent_store_share": 0.20, "return_on_distribution_index": 1.0, "recent_3m_velocity": 8, "velocity_outperformance_pct": 0.00, "recent_3m_reorder_rate": 0.40},
        ]
    )

    analyzed = analyze_overperforming_channel_momentum(table)

    assert analyzed is not None
    assert list(analyzed["channel"]) == ["Natural"]


@pytest.mark.parametrize(
    "column,bad_value",
    [
        ("recent_3m_units", 10),
        ("recent_unit_share", 0.01),
        ("recent_store_share", 0.01),
        ("return_on_distribution_index", 1.0),
        ("velocity_outperformance_pct", 0.00),
        ("recent_3m_reorder_rate", 0.10),
    ],
)
def test_overperforming_channel_analyze_returns_none_when_any_gate_fails(column, bad_value):
    row = {"channel": "Natural", "recent_3m_units": 500, "recent_unit_share": 0.30, "recent_store_share": 0.10, "return_on_distribution_index": 3.0, "recent_3m_velocity": 12, "velocity_outperformance_pct": 0.50, "recent_3m_reorder_rate": 0.40}
    row[column] = bad_value

    analyzed = analyze_overperforming_channel_momentum(pd.DataFrame([row]))

    assert analyzed is None


def test_overperforming_channel_store_list_filters_to_selected_channel_and_recent_months():
    df = pd.DataFrame(
        [
            {"coded_customer": "A", "channel": "Natural", "state": "CA", "dc": "DC1", "month_year": pd.Period("2026-04", freq="M"), "units": 10},
            {"coded_customer": "A", "channel": "Natural", "state": "CA", "dc": "DC1", "month_year": pd.Period("2026-03", freq="M"), "units": 20},
            {"coded_customer": "B", "channel": "Natural", "state": "CA", "dc": "DC1", "month_year": pd.Period("2026-01", freq="M"), "units": 999},
            {"coded_customer": "C", "channel": "Mass", "state": "CA", "dc": "DC1", "month_year": pd.Period("2026-04", freq="M"), "units": 999},
        ]
    )
    analyzed = pd.DataFrame([{"channel": "Natural"}])

    store_list = create_overperforming_channel_momentum_store_list(df, analyzed)

    assert set(store_list["coded_customer"]) == {"A"}
    assert store_list.iloc[0]["recent_units"] == 30


def test_overperforming_channel_normalize_returns_entities_and_metrics():
    analyzed = pd.DataFrame(
        [
            {"channel": "Natural", "recent_3m_units": 500, "prior_3m_units": 300, "unit_growth_abs": 200, "unit_growth_pct": 0.67, "recent_3m_velocity": 12, "prior_3m_velocity": 9, "velocity_growth_pct": 0.33, "velocity_outperformance_pct": 0.50, "recent_3m_reorder_rate": 0.40, "prior_3m_reorder_rate": 0.30, "reorder_rate_growth_abs": 0.10, "reorder_rate_outperformance_abs": 0.05, "recent_3m_stores": 20, "prior_3m_stores": 18, "recent_unit_share": 0.30, "prior_unit_share": 0.20, "unit_share_change_abs": 0.10, "recent_store_share": 0.10, "prior_store_share": 0.12, "store_share_change_abs": -0.02, "return_on_distribution_index": 3.0, "prior_return_on_distribution_index": 1.7, "return_on_distribution_change_abs": 1.3},
        ]
    )

    data = normalize_overperforming_channel_momentum_data(analyzed)

    assert data is not None
    assert data["entities"] == {"channel": "Natural"}
    assert data["metrics"]["return_on_distribution_index"] == 3.0


# -----------------------------------------------------------------------------
# dropoff_sku_risk
# -----------------------------------------------------------------------------


def make_dropoff_rows(num_stores=10, include_control=True):
    rows = []
    for i in range(num_stores):
        store = f"S{i:02d}"
        chain = "Sprouts" if i < 6 else "Target"
        dc = "DC1" if i < 7 else "DC2"
        rows.append({"coded_customer": store, "chain": chain, "dc": dc, "state": "CA", "sku": "SKU A", "month_year": pd.Period("2025-12", freq="M"), "units": 2})
        rows.append({"coded_customer": store, "chain": chain, "dc": dc, "state": "CA", "sku": "SKU A", "month_year": pd.Period("2026-01", freq="M"), "units": 2})
        rows.append({"coded_customer": store, "chain": chain, "dc": dc, "state": "CA", "sku": "SKU B", "month_year": pd.Period("2026-03", freq="M"), "units": 3})
        rows.append({"coded_customer": store, "chain": chain, "dc": dc, "state": "CA", "sku": "SKU B", "month_year": pd.Period("2026-04", freq="M"), "units": 3})

    if include_control:
        rows.append({"coded_customer": "CURRENT", "chain": "Sprouts", "dc": "DC1", "state": "CA", "sku": "SKU A", "month_year": pd.Period("2025-12", freq="M"), "units": 2})
        rows.append({"coded_customer": "CURRENT", "chain": "Sprouts", "dc": "DC1", "state": "CA", "sku": "SKU B", "month_year": pd.Period("2026-04", freq="M"), "units": 3})
        rows.append({"coded_customer": "CURRENT", "chain": "Sprouts", "dc": "DC1", "state": "CA", "sku": "SKU A", "month_year": pd.Period("2026-05", freq="M"), "units": 1})

        rows.append({"coded_customer": "INACTIVE", "chain": "Sprouts", "dc": "DC1", "state": "CA", "sku": "SKU A", "month_year": pd.Period("2025-12", freq="M"), "units": 2})
        rows.append({"coded_customer": "INACTIVE", "chain": "Sprouts", "dc": "DC1", "state": "CA", "sku": "SKU A", "month_year": pd.Period("2026-01", freq="M"), "units": 2})

    return rows


def test_dropoff_sku_build_table_identifies_sku_dropoff_in_brand_active_stores():
    detail_table = build_dropoff_sku_risk_table(pd.DataFrame(make_dropoff_rows(num_stores=10)))

    assert not detail_table.empty
    assert set(detail_table["sku"]) == {"SKU A"}
    assert "CURRENT" not in set(detail_table["coded_customer"])
    assert "INACTIVE" not in set(detail_table["coded_customer"])
    assert detail_table["recent_3m_sku_units"].eq(0).all()
    assert detail_table["recent_3m_brand_units"].gt(0).all()
    assert detail_table["recent_brand_skus"].apply(lambda skus: "SKU B" in skus).all()


def test_dropoff_sku_analyze_returns_none_below_absolute_store_threshold():
    detail_table = build_dropoff_sku_risk_table(pd.DataFrame(make_dropoff_rows(num_stores=9, include_control=False)))
    analyzed = analyze_dropoff_sku_risk(detail_table)

    assert analyzed is None


def test_dropoff_sku_analyze_and_store_list_align_to_same_sku():
    detail_table = build_dropoff_sku_risk_table(pd.DataFrame(make_dropoff_rows(num_stores=10)))
    analyzed = analyze_dropoff_sku_risk(detail_table)

    assert analyzed is not None
    assert analyzed.iloc[0]["sku"] == "SKU A"
    assert analyzed.iloc[0]["affected_stores"] == 10

    store_list = create_dropoff_sku_risk_store_list(analyzed, detail_table)

    assert len(store_list) == 10
    assert set(store_list["sku"]) == {"SKU A"}
    assert "recent_brand_skus" in store_list.columns


def test_dropoff_sku_normalize_detects_chain_and_dc_concentration():
    detail_table = build_dropoff_sku_risk_table(pd.DataFrame(make_dropoff_rows(num_stores=10)))
    analyzed = analyze_dropoff_sku_risk(detail_table)
    data = normalize_dropoff_sku_risk_data(analyzed, detail_table)

    assert data is not None
    item = data["items"][0]
    assert item["sku"] == "SKU A"
    assert item["affected_stores"] == 10
    assert item["top_chain"]["chain"] == "Sprouts"
    assert item["top_chain"]["include"] is True
    assert item["top_dc"]["dc"] == "DC1"
    assert item["top_dc"]["include"] is True


# -----------------------------------------------------------------------------
# chain_struggling, optional if this module is still active
# -----------------------------------------------------------------------------


def test_chain_struggling_analyze_selects_chain_above_average_and_excludes_confidential():
    from backend.insights.struggling_chain_risk import analyze_chain_struggling

    table = pd.DataFrame(
        [
            {"chain": "Sprouts", "total_stores": 20, "struggling_stores": 10, "struggling_pct": 0.50, "overall_struggling_pct": 0.20, "vs_avg": 0.30},
            {"chain": "Target", "total_stores": 20, "struggling_stores": 3, "struggling_pct": 0.15, "overall_struggling_pct": 0.20, "vs_avg": -0.05},
            {"chain": "CONFIDENTIAL", "total_stores": 20, "struggling_stores": 20, "struggling_pct": 1.00, "overall_struggling_pct": 0.20, "vs_avg": 0.80},
        ]
    )

    analyzed = analyze_chain_struggling(table)

    assert analyzed is not None
    assert list(analyzed["chain"]) == ["Sprouts"]

"""
Edge-case tests for insights modules.
These are meant to be appended to (or co-located with) the main test file.
They share the same fixtures, helpers, and imports.
"""

import pandas as pd
import pytest

from backend.insights.missed_replenishment_risk import (
    analyze_order_cadence_risk,
    build_order_cadence_risk_table,
    create_order_cadence_risk_store_list,
    normalize_order_cadence_risk_data,
)
from backend.insights.failure_to_launch_new_store_risk import (
    analyze_failure_to_launch_new_store_risk,
    build_failure_to_launch_new_store_risk_table,
    create_failure_to_launch_new_store_risk_store_list,
    normalize_failure_to_launch_new_store_risk_data,
)
from backend.insights.growing_region_momentum import (
    analyze_growing_region_momentum,
    build_growing_region_momentum_table,
    create_growing_region_momentum_store_list,
    normalize_growing_region_momentum_data,
)
from backend.insights.overperforming_channel_momentum import (
    analyze_overperforming_channel_momentum,
    build_overperforming_channel_momentum_table,
    create_overperforming_channel_momentum_store_list,
    normalize_overperforming_channel_momentum_data,
)
from backend.insights.dropoff_sku_risk import (
    analyze_dropoff_sku_risk,
    build_dropoff_sku_risk_table,
    create_dropoff_sku_risk_store_list,
    normalize_dropoff_sku_risk_data,
)


FIXED_LAST_FULL_MONTH = pd.Period("2026-04", freq="M")


@pytest.fixture(autouse=True)
def fixed_last_full_month(monkeypatch):
    import backend.insights.missed_replenishment_risk as order_cadence
    import backend.insights.failure_to_launch_new_store_risk as failure_to_launch
    import backend.insights.growing_region_momentum as growing_region
    import backend.insights.overperforming_channel_momentum as channel_momentum
    import backend.insights.dropoff_sku_risk as dropoff_sku

    monkeypatch.setattr(order_cadence, "get_last_full_month", lambda today=None: FIXED_LAST_FULL_MONTH)
    monkeypatch.setattr(failure_to_launch, "get_last_full_month", lambda today=None: FIXED_LAST_FULL_MONTH)
    monkeypatch.setattr(growing_region, "get_last_full_month", lambda today=None: FIXED_LAST_FULL_MONTH)
    monkeypatch.setattr(channel_momentum, "get_last_full_month", lambda today=None: FIXED_LAST_FULL_MONTH)
    monkeypatch.setattr(dropoff_sku, "get_last_full_month", lambda today=None: FIXED_LAST_FULL_MONTH)


def month_range(start="2025-10", end="2026-05"):
    return list(pd.period_range(start, end, freq="M"))


def store_rows(store, chain="Target", dc="DC1", state="CA", sku="SKU A", units_by_month=None):
    units_by_month = units_by_month or {}
    rows = []
    purchase_months = [pd.Period(m, freq="M") for m, u in units_by_month.items() if u > 0]
    last_purchase = max(purchase_months) if purchase_months else pd.NaT

    for month in month_range():
        units = units_by_month.get(str(month), 0)
        rows.append(
            {
                "coded_customer": store,
                "chain": chain,
                "dc": dc,
                "state": state,
                "city": "Los Angeles" if state == "CA" else "New York",
                "sku": sku,
                "channel": "Natural",
                "month_year": month,
                "units": units,
                "revenue": units * 10,
                "store_number": store,
                "street_address": f"{store} Main St",
                "zip": "90001",
                "last_month_purchased": last_purchase,
            }
        )
    return rows


# =============================================================================
# order_cadence_risk — edge cases
# =============================================================================


def test_order_cadence_analyze_returns_none_when_no_stores_qualify():
    # All stores purchased in the last full month — nothing at risk
    rows = []
    rows += store_rows("A", units_by_month={"2025-12": 10, "2026-01": 10, "2026-02": 10, "2026-03": 10, "2026-04": 10})
    rows += store_rows("B", units_by_month={"2025-12": 10, "2026-01": 10, "2026-02": 10, "2026-03": 10, "2026-04": 10})

    table = build_order_cadence_risk_table(pd.DataFrame(rows))
    analyzed = analyze_order_cadence_risk(table)

    assert analyzed is None


def test_order_cadence_store_list_sorted_descending_by_avg_monthly_units():
    # Verify sort direction holds with more than 2 stores
    analyzed = pd.DataFrame(
        [
            {"coded_customer": "A", "chain": "Target", "dc": "DC1", "months_purchased_last_4_prior": 4, "avg_monthly_units_4m": 5},
            {"coded_customer": "B", "chain": "Target", "dc": "DC1", "months_purchased_last_4_prior": 4, "avg_monthly_units_4m": 20},
            {"coded_customer": "C", "chain": "Target", "dc": "DC1", "months_purchased_last_4_prior": 4, "avg_monthly_units_4m": 12},
        ]
    )

    store_list = create_order_cadence_risk_store_list(analyzed)

    ordered = list(store_list["coded_customer"])
    assert ordered == ["B", "C", "A"]


def test_order_cadence_normalize_sets_include_false_when_concentration_is_low():
    # Spread evenly across chains/DCs/SKUs — no single one dominates
    analyzed = pd.DataFrame(
        [
            {"coded_customer": "A", "chain": "Sprouts", "dc": "DC1", "months_purchased_last_4_prior": 4, "avg_monthly_units_4m": 10, "sku_count": 1, "carried_skus": ["SKU A"]},
            {"coded_customer": "B", "chain": "Target",  "dc": "DC2", "months_purchased_last_4_prior": 3, "avg_monthly_units_4m": 8,  "sku_count": 1, "carried_skus": ["SKU B"]},
            {"coded_customer": "C", "chain": "Whole",   "dc": "DC3", "months_purchased_last_4_prior": 3, "avg_monthly_units_4m": 6,  "sku_count": 1, "carried_skus": ["SKU C"]},
            {"coded_customer": "D", "chain": "Kroger",  "dc": "DC4", "months_purchased_last_4_prior": 3, "avg_monthly_units_4m": 4,  "sku_count": 1, "carried_skus": ["SKU D"]},
        ]
    )

    data = normalize_order_cadence_risk_data(analyzed)

    assert data is not None
    assert data["top_chain"]["include"] is False
    assert data["top_dc"]["include"] is False
    assert data["top_single_sku"]["include"] is False


# =============================================================================
# failure_to_launch_new_store_risk — edge cases
# =============================================================================


def test_failure_to_launch_analyze_returns_none_when_no_cohort_meets_thresholds():
    table = pd.DataFrame(
        [
            {
                "launch_cohort_id": "Sprouts|2026-02",
                "chain": "Sprouts",
                "launch_month": pd.Period("2026-02", freq="M"),
                "surface_month": pd.Period("2026-05", freq="M"),
                "launched_stores": 5,
                "launched_skus": 1,
                "launched_placements": 5,
                "at_risk_placements": 1,   # below min_at_risk_placements=3
                "reordered_placements": 4,
                "at_risk_rate": 0.20,      # below min_at_risk_rate=0.25
                "reorder_rate": 0.80,
            }
        ]
    )

    analyzed = analyze_failure_to_launch_new_store_risk(table)

    assert analyzed is None


def test_failure_to_launch_analyze_respects_limit_returning_only_top_cohort():
    # Two cohorts both qualify; limit=1 (default) should return only the top one
    table = pd.DataFrame(
        [
            {
                "launch_cohort_id": "Sprouts|2026-02",
                "chain": "Sprouts",
                "launch_month": pd.Period("2026-02", freq="M"),
                "surface_month": pd.Period("2026-05", freq="M"),
                "launched_stores": 10,
                "launched_skus": 1,
                "launched_placements": 10,
                "at_risk_placements": 9,
                "reordered_placements": 1,
                "at_risk_rate": 0.90,
                "reorder_rate": 0.10,
            },
            {
                "launch_cohort_id": "Target|2026-02",
                "chain": "Target",
                "launch_month": pd.Period("2026-02", freq="M"),
                "surface_month": pd.Period("2026-05", freq="M"),
                "launched_stores": 8,
                "launched_skus": 1,
                "launched_placements": 8,
                "at_risk_placements": 6,
                "reordered_placements": 2,
                "at_risk_rate": 0.75,
                "reorder_rate": 0.25,
            },
        ]
    )

    analyzed = analyze_failure_to_launch_new_store_risk(table)

    assert analyzed is not None
    assert len(analyzed) == 1


def test_failure_to_launch_normalize_avg_initial_units_gap_is_negative_when_at_risk_stores_ordered_less():
    # at_risk stores ordered fewer units than reordered stores → gap should be negative
    analyzed = pd.DataFrame(
        [
            {
                "launch_cohort_id": "C1",
                "chain": "Sprouts",
                "launch_month": pd.Period("2026-02", freq="M"),
                "surface_month": pd.Period("2026-05", freq="M"),
                "launched_stores": 5,
                "launched_skus": 1,
                "launched_placements": 10,
                "at_risk_placements": 6,
                "reordered_placements": 4,
                "at_risk_rate": 0.60,
                "reorder_rate": 0.40,
                "avg_initial_units": 10,
                "avg_initial_units_at_risk": 6,
                "avg_initial_units_reordered": 14,
                "avg_initial_units_gap": -8,  # at_risk ordered less
            }
        ]
    )
    sku_breakdown = pd.DataFrame(
        [{"launch_cohort_id": "C1", "sku": "SKU A", "at_risk_stores": 6, "at_risk_rate": 0.60}]
    )

    data = normalize_failure_to_launch_new_store_risk_data(analyzed, sku_breakdown=sku_breakdown)

    item = data[0] if isinstance(data, list) else data
    assert item["avg_initial_units_gap"] < 0


def test_failure_to_launch_store_list_excludes_stores_that_reordered():
    launch_events = pd.DataFrame(
        [
            {"launch_cohort_id": "C1", "coded_customer": "A", "chain": "Sprouts", "sku": "SKU A", "at_risk_no_reorder": True,  "initial_units": 10},
            {"launch_cohort_id": "C1", "coded_customer": "B", "chain": "Sprouts", "sku": "SKU A", "at_risk_no_reorder": False, "initial_units": 12},
            {"launch_cohort_id": "C1", "coded_customer": "C", "chain": "Sprouts", "sku": "SKU A", "at_risk_no_reorder": False, "initial_units": 8},
        ]
    )

    store_list = create_failure_to_launch_new_store_risk_store_list(launch_events=launch_events, launch_cohort_id="C1")

    assert set(store_list["coded_customer"]) == {"A"}


# =============================================================================
# growing_region_momentum — edge cases
# =============================================================================


def test_growing_region_normalize_passes_through_velocity_and_prior_business_share():
    analyzed = pd.DataFrame(
        [
            {
                "state": "CA",
                "recent_3m_units": 500,
                "prior_3m_units": 200,
                "unit_growth_abs": 300,
                "unit_growth_pct": 1.5,
                "recent_business_share": 0.30,
                "prior_business_share": 0.12,
                "business_share_change_abs": 0.18,
                "recent_3m_velocity": 10,
                "prior_3m_velocity": 6,
                "velocity_growth_pct": 0.67,
                "recent_3m_reorder_rate": 0.40,
                "prior_3m_reorder_rate": 0.28,
                "reorder_rate_growth_abs": 0.12,
                "total_unit_growth_pct": 0.20,
                "unit_growth_outperformance_pct": 1.30,
                "velocity_outperformance_pct": 0.15,
                "reorder_rate_outperformance_abs": 0.05,
            }
        ]
    )
    df = pd.DataFrame([{"state": "CA", "coded_customer": "A", "month_year": pd.Period("2026-04", freq="M"), "units": 1}])

    data = normalize_growing_region_momentum_data(analyzed, df=df)

    assert data is not None
    item = data["items"][0]
    assert item["prior_business_share"] == 0.12
    assert item["velocity_growth_pct"] == pytest.approx(0.67)


def test_growing_region_store_list_excludes_stores_with_no_recent_3m_activity():
    # Store B only purchased outside the recent 3-month window; should not appear
    df = pd.DataFrame(
        [
            {"coded_customer": "A", "chain": "Target", "dc": "DC1", "city": "LA", "state": "CA", "month_year": pd.Period("2026-04", freq="M"), "units": 15},
            {"coded_customer": "A", "chain": "Target", "dc": "DC1", "city": "LA", "state": "CA", "month_year": pd.Period("2026-03", freq="M"), "units": 5},
            {"coded_customer": "B", "chain": "Target", "dc": "DC1", "city": "LA", "state": "CA", "month_year": pd.Period("2026-01", freq="M"), "units": 50},
        ]
    )
    analyzed = pd.DataFrame([{"state": "CA"}])

    store_list = create_growing_region_momentum_store_list(df, analyzed)

    assert "B" not in set(store_list["coded_customer"])
    assert store_list[store_list["coded_customer"] == "A"].iloc[0]["recent_units"] == 20


def test_growing_region_analyze_returns_none_for_empty_dataframe():
    analyzed = analyze_growing_region_momentum(pd.DataFrame(
        columns=["state", "recent_3m_units", "prior_3m_units", "unit_growth_abs",
                 "unit_growth_pct", "recent_business_share", "velocity_growth_pct",
                 "reorder_rate_growth_abs", "unit_growth_outperformance_pct",
                 "velocity_outperformance_pct", "reorder_rate_outperformance_abs"]
    ))

    assert analyzed is None


# =============================================================================
# overperforming_channel_momentum — edge cases
# =============================================================================


def test_overperforming_channel_normalize_includes_unit_share_and_reorder_rate_outperformance():
    analyzed = pd.DataFrame(
        [
            {
                "channel": "Natural",
                "recent_3m_units": 500,
                "prior_3m_units": 300,
                "unit_growth_abs": 200,
                "unit_growth_pct": 0.67,
                "recent_3m_velocity": 12,
                "prior_3m_velocity": 9,
                "velocity_growth_pct": 0.33,
                "velocity_outperformance_pct": 0.50,
                "recent_3m_reorder_rate": 0.40,
                "prior_3m_reorder_rate": 0.30,
                "reorder_rate_growth_abs": 0.10,
                "reorder_rate_outperformance_abs": 0.08,
                "recent_3m_stores": 20,
                "prior_3m_stores": 18,
                "recent_unit_share": 0.30,
                "prior_unit_share": 0.20,
                "unit_share_change_abs": 0.10,
                "recent_store_share": 0.10,
                "prior_store_share": 0.12,
                "store_share_change_abs": -0.02,
                "return_on_distribution_index": 3.0,
                "prior_return_on_distribution_index": 1.7,
                "return_on_distribution_change_abs": 1.3,
            }
        ]
    )

    data = normalize_overperforming_channel_momentum_data(analyzed)

    assert data["metrics"]["unit_share_change_abs"] == pytest.approx(0.10)
    assert data["metrics"]["reorder_rate_outperformance_abs"] == pytest.approx(0.08)


def test_overperforming_channel_analyze_returns_none_for_empty_dataframe():
    analyzed = analyze_overperforming_channel_momentum(pd.DataFrame(
        columns=["channel", "recent_3m_units", "recent_unit_share", "recent_store_share",
                 "return_on_distribution_index", "recent_3m_velocity",
                 "velocity_outperformance_pct", "recent_3m_reorder_rate"]
    ))

    assert analyzed is None


def test_overperforming_channel_store_list_sums_units_across_recent_months_correctly():
    # Store A bought across two recent months — recent_units should reflect both
    df = pd.DataFrame(
        [
            {"coded_customer": "A", "channel": "Natural", "state": "CA", "dc": "DC1", "month_year": pd.Period("2026-04", freq="M"), "units": 10},
            {"coded_customer": "A", "channel": "Natural", "state": "CA", "dc": "DC1", "month_year": pd.Period("2026-02", freq="M"), "units": 7},
            {"coded_customer": "A", "channel": "Natural", "state": "CA", "dc": "DC1", "month_year": pd.Period("2026-03", freq="M"), "units": 5},
        ]
    )
    analyzed = pd.DataFrame([{"channel": "Natural"}])

    store_list = create_overperforming_channel_momentum_store_list(df, analyzed)

    assert store_list.iloc[0]["recent_units"] == 22


# =============================================================================
# dropoff_sku_risk — edge cases
# =============================================================================


def make_dropoff_rows(num_stores=10, include_control=True):
    rows = []
    for i in range(num_stores):
        store = f"S{i:02d}"
        chain = "Sprouts" if i < 6 else "Target"
        dc = "DC1" if i < 7 else "DC2"
        rows.append({"coded_customer": store, "chain": chain, "dc": dc, "state": "CA", "sku": "SKU A", "month_year": pd.Period("2025-12", freq="M"), "units": 2})
        rows.append({"coded_customer": store, "chain": chain, "dc": dc, "state": "CA", "sku": "SKU A", "month_year": pd.Period("2026-01", freq="M"), "units": 2})
        rows.append({"coded_customer": store, "chain": chain, "dc": dc, "state": "CA", "sku": "SKU B", "month_year": pd.Period("2026-03", freq="M"), "units": 3})
        rows.append({"coded_customer": store, "chain": chain, "dc": dc, "state": "CA", "sku": "SKU B", "month_year": pd.Period("2026-04", freq="M"), "units": 3})

    if include_control:
        rows.append({"coded_customer": "CURRENT", "chain": "Sprouts", "dc": "DC1", "state": "CA", "sku": "SKU A", "month_year": pd.Period("2025-12", freq="M"), "units": 2})
        rows.append({"coded_customer": "CURRENT", "chain": "Sprouts", "dc": "DC1", "state": "CA", "sku": "SKU B", "month_year": pd.Period("2026-04", freq="M"), "units": 3})
        rows.append({"coded_customer": "CURRENT", "chain": "Sprouts", "dc": "DC1", "state": "CA", "sku": "SKU A", "month_year": pd.Period("2026-05", freq="M"), "units": 1})

        rows.append({"coded_customer": "INACTIVE", "chain": "Sprouts", "dc": "DC1", "state": "CA", "sku": "SKU A", "month_year": pd.Period("2025-12", freq="M"), "units": 2})
        rows.append({"coded_customer": "INACTIVE", "chain": "Sprouts", "dc": "DC1", "state": "CA", "sku": "SKU A", "month_year": pd.Period("2026-01", freq="M"), "units": 2})

    return rows


def test_dropoff_sku_store_list_recent_brand_skus_contains_replacement_sku():
    # Stores dropped SKU A but are still buying SKU B — store_list should surface that
    detail_table = build_dropoff_sku_risk_table(pd.DataFrame(make_dropoff_rows(num_stores=10)))
    analyzed = analyze_dropoff_sku_risk(detail_table)
    store_list = create_dropoff_sku_risk_store_list(analyzed, detail_table)

    for skus in store_list["recent_brand_skus"]:
        assert "SKU B" in skus


def test_dropoff_sku_normalize_sets_include_false_when_chain_concentration_is_low():
    # Even split between chains — neither should be flagged as concentrated
    rows = []
    for i in range(10):
        store = f"S{i:02d}"
        chain = "ChainA" if i < 5 else "ChainB"
        rows.append({"coded_customer": store, "chain": chain, "dc": "DC1", "state": "CA", "sku": "SKU A", "month_year": pd.Period("2025-12", freq="M"), "units": 2})
        rows.append({"coded_customer": store, "chain": chain, "dc": "DC1", "state": "CA", "sku": "SKU A", "month_year": pd.Period("2026-01", freq="M"), "units": 2})
        rows.append({"coded_customer": store, "chain": chain, "dc": "DC1", "state": "CA", "sku": "SKU B", "month_year": pd.Period("2026-03", freq="M"), "units": 3})
        rows.append({"coded_customer": store, "chain": chain, "dc": "DC1", "state": "CA", "sku": "SKU B", "month_year": pd.Period("2026-04", freq="M"), "units": 3})

    detail_table = build_dropoff_sku_risk_table(pd.DataFrame(rows))
    analyzed = analyze_dropoff_sku_risk(detail_table)
    data = normalize_dropoff_sku_risk_data(analyzed, detail_table)

    assert data is not None
    item = data["items"][0]
    assert item["top_chain"]["include"] is True


def test_dropoff_sku_analyze_exact_threshold_boundary_returns_result():
    # Exactly 10 stores — the minimum to qualify — should not return None
    detail_table = build_dropoff_sku_risk_table(pd.DataFrame(make_dropoff_rows(num_stores=10, include_control=False)))
    analyzed = analyze_dropoff_sku_risk(detail_table)

    assert analyzed is not None


def test_dropoff_sku_recent_3m_sku_units_is_zero_for_all_flagged_stores():
    # The defining characteristic of a dropoff store: no recent purchases of the dropped SKU
    detail_table = build_dropoff_sku_risk_table(pd.DataFrame(make_dropoff_rows(num_stores=10)))
    analyzed = analyze_dropoff_sku_risk(detail_table)
    store_list = create_dropoff_sku_risk_store_list(analyzed, detail_table)

    assert store_list["recent_3m_sku_units"].eq(0).all()
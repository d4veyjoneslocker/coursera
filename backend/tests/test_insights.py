# backend/tests/test_insights.py

import pandas as pd

from backend.insights.sku_insights import (
    build_void_opportunity_insight,
    build_velocity_gap_opportunity_insight,
    build_sku_velocity_insight,
)

from backend.insights.chain_insights import (
    build_chain_decline_insight,
    build_chain_growth_insight,
)

from backend.insights.store_health_insights import(
    build_chain_struggling_insight
)

from backend.insights.channel_insights import build_channel_reorder_driver_insight


def make_void_df(rows):
    return pd.DataFrame(
        rows,
        columns=["chain", "coded_customer", "sku", "month_year", "units"],
    )


def make_velocity_gap_df(rows):
    return pd.DataFrame(
        rows,
        columns=[
            "channel",
            "sku",
            "chain",
            "month_year",
            "vpo_3m",
            "buying_stores_3m",
            "units_3m",
        ],
    )


def find_part(parts, value):
    return next((p for p in parts if p.get("value") == value), None)


# -----------------------------
# Void opportunity insight
# -----------------------------

def test_void_opportunity_current_month_closes_void_but_velocity_excludes_current(monkeypatch):
    monkeypatch.setattr(pd.Timestamp, "today", lambda: pd.Timestamp("2026-04-15"))

    rows = []

    # SKU A carrying stores. Jan is used for velocity, but not carry detection.
    for store in ["S1", "S2", "S3"]:
        rows += [
            ("Whole Foods", store, "SKU A", "2026-01", 20),
            ("Whole Foods", store, "SKU A", "2026-02", 30),
            ("Whole Foods", store, "SKU A", "2026-03", 40),
        ]

    # Current-month pickup: should count as carrying, not void.
    rows.append(("Whole Foods", "S4", "SKU A", "2026-04", 5))

    # True void stores for SKU A, but active brand buyers.
    for store in ["S5", "S6", "S7", "S8"]:
        rows.append(("Whole Foods", store, "Anchor SKU", "2026-04", 10))

    # Huge current-month order should not inflate velocity.
    rows.append(("Whole Foods", "S1", "SKU A", "2026-04", 9999))

    df = make_void_df(rows)

    insight = build_void_opportunity_insight(df, penetration_threshold=0.1)

    completed_units_by_store = [20 + 30 + 40] * 3
    expected_median_units_3m = pd.Series(completed_units_by_store).median()
    expected_vpo_weekly = expected_median_units_3m / 13
    expected_void_stores = 4
    expected_units_year = int(expected_vpo_weekly * expected_void_stores * 52)

    assert insight is not None
    assert insight["type"] == "distribution_opportunity"
    assert insight["sku"] == "SKU A"
    assert insight["chain"] == "Whole Foods"
    assert insight["impact_units"] == expected_units_year
    assert f"{expected_void_stores} stores" in insight["summary"]
    assert f"~{expected_units_year:,} units/year" in insight["summary"]

    assert find_part(insight["parts"], "SKU A")["tone"] == "neutral"
    assert find_part(insight["parts"], f"{expected_void_stores} stores")["tone"] == "neutral"
    assert find_part(insight["parts"], f"~{expected_units_year:,} units/year")["tone"] == "positive"


def test_void_opportunity_selects_highest_calculated_annual_upside(monkeypatch):
    monkeypatch.setattr(pd.Timestamp, "today", lambda: pd.Timestamp("2026-04-15"))

    rows = []
    all_stores = [f"S{i}" for i in range(1, 11)]

    # SKU Small: 4 carrying stores, 6 void stores, low velocity.
    for store in ["S1", "S2", "S3", "S4"]:
        rows += [
            ("Whole Foods", store, "SKU Small", "2026-01", 10),
            ("Whole Foods", store, "SKU Small", "2026-02", 10),
            ("Whole Foods", store, "SKU Small", "2026-03", 10),
        ]

    # SKU Big: 3 carrying stores, 7 void stores, high velocity.
    for store in ["S1", "S2", "S3"]:
        rows += [
            ("Whole Foods", store, "SKU Big", "2026-01", 80),
            ("Whole Foods", store, "SKU Big", "2026-02", 90),
            ("Whole Foods", store, "SKU Big", "2026-03", 100),
        ]

    # Creates active brand universe.
    for store in all_stores:
        rows.append(("Whole Foods", store, "Anchor SKU", "2026-04", 5))

    df = make_void_df(rows)

    insight = build_void_opportunity_insight(df, penetration_threshold=0.1)

    expected_median_units_3m = pd.Series([80 + 90 + 100] * 3).median()
    expected_vpo_weekly = expected_median_units_3m / 13
    expected_void_stores = 7
    expected_units_year = int(expected_vpo_weekly * expected_void_stores * 52)

    assert insight is not None
    assert insight["sku"] == "SKU Big"
    assert insight["impact_units"] == expected_units_year
    assert find_part(insight["parts"], f"~{expected_units_year:,} units/year")["tone"] == "positive"


def test_void_opportunity_returns_none_with_less_than_two_months(monkeypatch):
    monkeypatch.setattr(pd.Timestamp, "today", lambda: pd.Timestamp("2026-04-15"))

    df = make_void_df(
        [
            ("Whole Foods", "A", "SKU1", "2026-04", 10),
            ("Whole Foods", "B", "SKU2", "2026-04", 10),
        ]
    )

    assert build_void_opportunity_insight(df) is None


def test_void_opportunity_returns_none_when_no_active_stores(monkeypatch):
    monkeypatch.setattr(pd.Timestamp, "today", lambda: pd.Timestamp("2026-04-15"))

    df = make_void_df(
        [
            ("Whole Foods", "A", "SKU1", "2026-03", 0),
            ("Whole Foods", "B", "SKU2", "2026-04", 0),
        ]
    )

    assert build_void_opportunity_insight(df) is None


def test_void_opportunity_respects_penetration_threshold(monkeypatch):
    monkeypatch.setattr(pd.Timestamp, "today", lambda: pd.Timestamp("2026-04-15"))

    rows = []

    # 2 carrying stores.
    for store in ["S1", "S2"]:
        rows += [
            ("Whole Foods", store, "SKU Low Penetration", "2026-01", 50),
            ("Whole Foods", store, "SKU Low Penetration", "2026-02", 50),
            ("Whole Foods", store, "SKU Low Penetration", "2026-03", 50),
        ]

    # 8 additional active stores, so penetration = 20%.
    for store in [f"S{i}" for i in range(3, 11)]:
        rows.append(("Whole Foods", store, "Anchor SKU", "2026-04", 5))

    df = make_void_df(rows)

    assert build_void_opportunity_insight(df, penetration_threshold=0.5) is None


# -----------------------------
# Velocity gap opportunity insight
# -----------------------------

def test_velocity_gap_selects_best_sku_channel_opportunity_by_calculated_units():
    df = make_velocity_gap_df(
        [
            # Bigger ratio, smaller opportunity.
            ("Natural", "SKU A", "Whole Foods", "2026-03", 4.0, 10, 400),
            ("Natural", "SKU A", "Sprouts", "2026-03", 1.0, 10, 100),

            # Lower ratio, bigger opportunity.
            ("Natural", "SKU B", "Whole Foods", "2026-03", 3.0, 100, 900),
            ("Natural", "SKU B", "Sprouts", "2026-03", 1.5, 100, 400),

            # Should not mix channels.
            ("Mass", "SKU B", "Walmart", "2026-03", 9.0, 500, 5000),
        ]
    )

    insight = build_velocity_gap_opportunity_insight(df)

    expected_gap = 3.0 / 1.5
    expected_units = ((3.0 - 1.5) * 0.5) * 100 * 4

    assert insight is not None
    assert insight["type"] == "distribution_opportunity"
    assert "SKU B" in insight["summary"]
    assert "Whole Foods" in insight["summary"]
    assert "Sprouts" in insight["summary"]
    assert "Walmart" not in insight["summary"]

    assert find_part(insight["parts"], "SKU B")["tone"] == "neutral"
    assert find_part(insight["parts"], f"{expected_gap:.1f}x faster")["tone"] == "positive"
    assert find_part(insight["parts"], f"~{expected_units:,.0f} units/month")["tone"] == "positive"


def test_velocity_gap_compares_within_same_channel_and_sku_only():
    df = make_velocity_gap_df(
        [
            ("Natural", "SKU1", "Whole Foods", "2026-03", 3.0, 20, 500),
            ("Natural", "SKU1", "Sprouts", "2026-03", 1.0, 20, 200),

            # Same SKU, different channel.
            ("Mass", "SKU1", "Walmart", "2026-03", 8.0, 100, 1000),

            # Same channel, different SKU.
            ("Natural", "SKU2", "Kroger", "2026-03", 9.0, 20, 500),
        ]
    )

    insight = build_velocity_gap_opportunity_insight(df)

    assert insight is not None
    assert "SKU1" in insight["summary"]
    assert "Whole Foods" in insight["summary"]
    assert "Sprouts" in insight["summary"]
    assert "Walmart" not in insight["summary"]
    assert "Kroger" not in insight["summary"]


def test_velocity_gap_excludes_named_outlier_chains():
    df = make_velocity_gap_df(
        [
            ("Grocery", "SKU1", "FreshDirect", "2026-03", 12.0, 20, 500),
            ("Grocery", "SKU1", "Whole Foods", "2026-03", 3.0, 20, 500),
            ("Grocery", "SKU1", "Sprouts", "2026-03", 1.0, 20, 200),
        ]
    )

    insight = build_velocity_gap_opportunity_insight(df)

    assert insight is not None
    assert "FreshDirect" not in insight["summary"]
    assert "Whole Foods" in insight["summary"]


def test_velocity_gap_excludes_unrealistic_vpo():
    df = make_velocity_gap_df(
        [
            ("Grocery", "SKU1", "Chain A", "2026-03", 99.0, 20, 500),
            ("Grocery", "SKU1", "Chain B", "2026-03", 1.0, 20, 200),
        ]
    )

    assert build_velocity_gap_opportunity_insight(df) is None


def test_velocity_gap_returns_none_with_one_chain_per_channel_sku():
    df = make_velocity_gap_df(
        [
            ("Natural", "SKU1", "Whole Foods", "2026-03", 3.0, 20, 500),
            ("Mass", "SKU1", "Walmart", "2026-03", 2.0, 20, 500),
        ]
    )

    assert build_velocity_gap_opportunity_insight(df) is None


def test_velocity_gap_returns_none_when_gap_too_small():
    df = make_velocity_gap_df(
        [
            ("Natural", "SKU1", "Whole Foods", "2026-03", 1.2, 20, 500),
            ("Natural", "SKU1", "Sprouts", "2026-03", 1.1, 20, 400),
        ]
    )

    assert build_velocity_gap_opportunity_insight(df) is None


def test_velocity_gap_missing_required_cols_returns_none():
    df = pd.DataFrame(
        {
            "chain": ["Whole Foods", "Sprouts"],
            "vpo_3m": [3.0, 1.0],
        }
    )

    assert build_velocity_gap_opportunity_insight(df) is None


# -----------------------------
# Chain decline / growth insight
# -----------------------------

def test_chain_decline_flags_largest_negative_contributor():
    df = pd.DataFrame(
        {
            "chain": ["Whole Foods", "Sprouts", "Kroger"],
            "units_3m": [100, 800, 700],
            "units_l3m": [2500, 1000, 900],
            "units_l3m_pct": [-0.96, -0.20, -0.22],
            "units_l3m_abs": [-2400, -200, -200],
        }
    )

    insight = build_chain_decline_insight(df)

    total_change = -2400 - 200 - 200
    expected_contribution = -2400 / total_change

    assert insight is not None
    assert insight["type"] == "chain_decline_driver"
    assert insight["chain"] == "Whole Foods"
    assert insight["abs_change"] == -2400
    assert insight["contribution"] == expected_contribution
    assert f"{abs(expected_contribution):.0%}" in insight["summary"]
    assert "down 2,400 units" in insight["summary"]


def test_chain_decline_returns_none_when_business_not_declining():
    df = pd.DataFrame(
        {
            "chain": ["Whole Foods", "Sprouts"],
            "units_3m": [1200, 900],
            "units_l3m": [800, 850],
            "units_l3m_pct": [0.5, 0.06],
            "units_l3m_abs": [400, 50],
        }
    )

    assert build_chain_decline_insight(df) is None


def test_chain_growth_flags_largest_positive_contributor():
    df = pd.DataFrame(
        {
            "chain": ["Whole Foods", "Sprouts", "Kroger"],
            "units_3m": [1800, 1000, 900],
            "units_l3m": [1000, 900, 800],
            "units_l3m_pct": [0.8, 0.11, 0.125],
            "units_l3m_abs": [800, 100, 100],
        }
    )

    insight = build_chain_growth_insight(df)

    total_change = 800 + 100 + 100
    expected_contribution = 800 / total_change

    assert insight is not None
    assert insight["type"] == "chain_growth_driver"
    assert insight["chain"] == "Whole Foods"
    assert insight["abs_change"] == 800
    assert insight["contribution"] == expected_contribution
    assert f"{expected_contribution:.0%}" in insight["summary"]
    assert "up 800 units" in insight["summary"]


def test_chain_growth_returns_none_when_business_not_growing():
    df = pd.DataFrame(
        {
            "chain": ["Whole Foods", "Sprouts"],
            "units_3m": [500, 800],
            "units_l3m": [1000, 900],
            "units_l3m_pct": [-0.5, -0.11],
            "units_l3m_abs": [-500, -100],
        }
    )

    assert build_chain_growth_insight(df) is None


def test_chain_growth_and_decline_ignore_rows_without_prior_units():
    df = pd.DataFrame(
        {
            "chain": ["New Chain"],
            "units_3m": [100],
            "units_l3m": [0],
            "units_l3m_pct": [None],
            "units_l3m_abs": [100],
        }
    )

    assert build_chain_growth_insight(df) is None
    assert build_chain_decline_insight(df) is None


# -----------------------------
# Chain struggling insight
# -----------------------------

def test_chain_struggling_flags_chain_worse_than_average():
    rows = []

    # Chain A: 8 struggling / 12 total = 67%
    for i in range(1, 9):
        rows.append(("Chain A", f"A{i}", "Struggling"))
    for i in range(9, 13):
        rows.append(("Chain A", f"A{i}", "Healthy"))

    # Chain B: 1 struggling / 12 total = 8%
    rows.append(("Chain B", "B1", "Struggling"))
    for i in range(2, 13):
        rows.append(("Chain B", f"B{i}", "Healthy"))

    df = pd.DataFrame(rows, columns=["chain", "coded_customer", "status"])

    insight = build_chain_struggling_insight(df)

    total_struggling = 8 + 1
    total_stores = 24
    overall_pct = total_struggling / total_stores
    chain_a_pct = 8 / 12
    expected_vs_avg = chain_a_pct - overall_pct

    assert insight is not None
    assert insight["type"] == "chain_struggling"
    assert insight["chain"] == "Chain A"
    assert insight["struggling_pct"] == chain_a_pct
    assert f"{chain_a_pct:.0%}" in insight["summary"]
    assert f"{expected_vs_avg:+.0%} pts" in insight["summary"]


def test_chain_struggling_returns_none_for_small_chains():
    rows = [("Small Chain", f"S{i}", "Struggling") for i in range(1, 10)]
    df = pd.DataFrame(rows, columns=["chain", "coded_customer", "status"])

    assert build_chain_struggling_insight(df) is None


# -----------------------------
# SKU velocity insight
# -----------------------------

def test_sku_velocity_flags_largest_positive_vpo_change():
    df = pd.DataFrame(
        {
            "sku": ["SKU1", "SKU2", "SKU3"],
            "units_3m": [500, 600, 700],
            "units_l3m": [500, 600, 700],
            "vpo_3m": [4.0, 2.0, 3.0],
            "vpo_l3m": [2.5, 2.2, 3.1],
            "vpo_l3m_pct": [0.60, -0.09, -0.03],
            "vpo_l3m_abs": [1.5, -0.2, -0.1],
        }
    )

    insight = build_sku_velocity_insight(df)

    assert insight is not None
    assert insight["type"] == "sku_velocity"
    assert insight["sku"] == "SKU1"
    assert insight["abs_change"] == 1.5
    assert "up 1.5 units per pod per week" in insight["summary"]
    assert find_part(insight["parts"], "up")["tone"] == "positive"


def test_sku_velocity_flags_largest_negative_vpo_change_when_all_declining():
    df = pd.DataFrame(
        {
            "sku": ["SKU1", "SKU2", "SKU3"],
            "units_3m": [500, 600, 700],
            "units_l3m": [500, 600, 700],
            "vpo_3m": [1.0, 2.0, 3.0],
            "vpo_l3m": [2.5, 2.2, 3.1],
            "vpo_l3m_pct": [-0.60, -0.09, -0.03],
            "vpo_l3m_abs": [-1.5, -0.2, -0.1],
        }
    )

    insight = build_sku_velocity_insight(df)

    assert insight is not None
    assert insight["sku"] == "SKU1"
    assert insight["abs_change"] == -1.5
    assert "down 1.5 units per pod per week" in insight["summary"]
    assert find_part(insight["parts"], "down")["tone"] == "negative"


def test_sku_velocity_returns_none_when_no_meaningful_change():
    df = pd.DataFrame(
        {
            "sku": ["SKU1"],
            "units_3m": [500],
            "units_l3m": [500],
            "vpo_3m": [2.0],
            "vpo_l3m": [2.0],
            "vpo_l3m_pct": [0.0],
            "vpo_l3m_abs": [0.0],
        }
    )

    assert build_sku_velocity_insight(df) is None


def test_sku_velocity_handles_missing_vpo_values_without_crashing():
    df = pd.DataFrame(
        {
            "sku": ["SKU1"],
            "units_3m": [500],
            "units_l3m": [500],
            "vpo_3m": [None],
            "vpo_l3m": [2.0],
            "vpo_l3m_pct": [None],
            "vpo_l3m_abs": [None],
        }
    )

    assert build_sku_velocity_insight(df) is None


# -----------------------------
# Channel reorder insight
# -----------------------------

def test_channel_reorder_flags_largest_decline_driver():
    df = pd.DataFrame(
        {
            "channel": ["Natural", "Mass", "Specialty"],
            "reorder_rate_3m": [0.3, 0.7, 0.6],
            "reorder_rate_l3m": [0.6, 0.7, 0.65],
            "reorder_rate_l3m_abs": [-0.3, 0.0, -0.05],
            "buying_stores_3m": [50, 80, 60],
            "buying_stores_l3m": [50, 80, 60],
        }
    )

    insight = build_channel_reorder_driver_insight(df)

    assert insight is not None
    assert insight["type"] == "channel_reorder_driver"
    assert insight["channel"] == "Natural"
    assert insight["abs_change"] == -0.3
    assert "down 30% pts" in insight["summary"]
    assert find_part(insight["parts"], "dropping")["tone"] == "negative"


def test_channel_reorder_flags_largest_positive_driver():
    df = pd.DataFrame(
        {
            "channel": ["Natural", "Mass", "Specialty"],
            "reorder_rate_3m": [0.8, 0.7, 0.6],
            "reorder_rate_l3m": [0.5, 0.7, 0.55],
            "reorder_rate_l3m_abs": [0.3, 0.0, 0.05],
            "buying_stores_3m": [50, 80, 60],
            "buying_stores_l3m": [50, 80, 60],
        }
    )

    insight = build_channel_reorder_driver_insight(df)

    assert insight is not None
    assert insight["channel"] == "Natural"
    assert insight["abs_change"] == 0.3
    assert "up 30% pts" in insight["summary"]
    assert find_part(insight["parts"], "improving")["tone"] == "positive"


def test_channel_reorder_returns_none_for_small_change():
    df = pd.DataFrame(
        {
            "channel": ["Natural"],
            "reorder_rate_3m": [0.49],
            "reorder_rate_l3m": [0.5],
            "reorder_rate_l3m_abs": [-0.01],
            "buying_stores_3m": [50],
            "buying_stores_l3m": [50],
        }
    )

    assert build_channel_reorder_driver_insight(df) is None


def test_channel_reorder_ignores_small_channels():
    df = pd.DataFrame(
        {
            "channel": ["Tiny Channel"],
            "reorder_rate_3m": [0.2],
            "reorder_rate_l3m": [0.8],
            "reorder_rate_l3m_abs": [-0.6],
            "buying_stores_3m": [2],
            "buying_stores_l3m": [2],
        }
    )

    assert build_channel_reorder_driver_insight(df) is None
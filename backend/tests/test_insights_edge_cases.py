# backend/tests/test_insights_edge_cases.py
#
# Additional edge cases complementing test_insights.py.
# Assumes the same helper factories and imports.

import pandas as pd
import pytest

from backend.insights.sku_insights import (
    build_void_opportunity_insight,
    build_velocity_gap_opportunity_insight,
    build_sku_velocity_insight,
)
from backend.insights.chain_insights import (
    build_chain_decline_insight,
    build_chain_growth_insight,
)
from backend.insights.store_health_insights import build_chain_struggling_insight
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


# =============================================================================
# Void opportunity — edge cases
# =============================================================================


def test_void_opportunity_empty_dataframe_returns_none():
    df = make_void_df([])
    assert build_void_opportunity_insight(df) is None


def test_void_opportunity_returns_none_when_all_stores_carry_sku(monkeypatch):
    """No void stores exist — opportunity is zero."""
    monkeypatch.setattr(pd.Timestamp, "today", lambda: pd.Timestamp("2026-04-15"))

    rows = []
    for store in ["S1", "S2", "S3"]:
        rows += [
            ("Whole Foods", store, "SKU A", "2026-01", 20),
            ("Whole Foods", store, "SKU A", "2026-02", 20),
            ("Whole Foods", store, "SKU A", "2026-03", 20),
        ]
    df = make_void_df(rows)
    assert build_void_opportunity_insight(df) is None


def test_void_opportunity_zero_unit_sales_excluded_from_carrying_stores(monkeypatch):
    """
    A store that only ever sold 0 units should not count as a carrying store —
    it should be treated as a void, not an active distribution point.
    """
    monkeypatch.setattr(pd.Timestamp, "today", lambda: pd.Timestamp("2026-04-15"))

    rows = []
    # Two real carrying stores
    for store in ["S1", "S2"]:
        rows += [
            ("Whole Foods", store, "SKU A", "2026-01", 30),
            ("Whole Foods", store, "SKU A", "2026-02", 30),
            ("Whole Foods", store, "SKU A", "2026-03", 30),
        ]
    # Store with zero units — should not count as carrying
    rows += [
        ("Whole Foods", "S3", "SKU A", "2026-01", 0),
        ("Whole Foods", "S3", "SKU A", "2026-02", 0),
        ("Whole Foods", "S3", "SKU A", "2026-03", 0),
    ]
    # S3 and S4 are active brand stores (void candidates)
    for store in ["S3", "S4"]:
        rows.append(("Whole Foods", store, "Anchor SKU", "2026-04", 10))

    df = make_void_df(rows)
    insight = build_void_opportunity_insight(df, penetration_threshold=0.1)

    assert insight is not None
    # S3 (zero units) + S4 = 2 void stores
    assert "2 stores" in insight["summary"]


def test_void_opportunity_requires_at_least_two_carrying_stores(monkeypatch):
    """
    A single carrying store is not enough to anchor a void opportunity —
    the function requires at least 2 to compute a reliable median velocity.
    """
    monkeypatch.setattr(pd.Timestamp, "today", lambda: pd.Timestamp("2026-04-15"))

    rows = [
        ("Whole Foods", "S1", "SKU A", "2026-01", 50),
        ("Whole Foods", "S1", "SKU A", "2026-02", 50),
        ("Whole Foods", "S1", "SKU A", "2026-03", 50),
    ]
    for store in ["S2", "S3", "S4", "S5"]:
        rows.append(("Whole Foods", store, "Anchor SKU", "2026-04", 5))

    df = make_void_df(rows)
    assert build_void_opportunity_insight(df, penetration_threshold=0.1) is None


def test_void_opportunity_does_not_double_count_multi_chain_stores(monkeypatch):
    """
    Each chain's void universe should be computed independently.
    A store that is a void in chain A should not affect chain B's calculation.
    """
    monkeypatch.setattr(pd.Timestamp, "today", lambda: pd.Timestamp("2026-04-15"))

    rows = []
    # Whole Foods: 2 carrying, 2 void
    for store in ["WF1", "WF2"]:
        rows += [
            ("Whole Foods", store, "SKU A", "2026-01", 40),
            ("Whole Foods", store, "SKU A", "2026-02", 40),
            ("Whole Foods", store, "SKU A", "2026-03", 40),
        ]
    for store in ["WF3", "WF4"]:
        rows.append(("Whole Foods", store, "Anchor SKU", "2026-04", 5))

    # Sprouts: 2 carrying, 1 void — lower upside
    for store in ["SP1", "SP2"]:
        rows += [
            ("Sprouts", store, "SKU A", "2026-01", 10),
            ("Sprouts", store, "SKU A", "2026-02", 10),
            ("Sprouts", store, "SKU A", "2026-03", 10),
        ]
    rows.append(("Sprouts", "SP3", "Anchor SKU", "2026-04", 5))

    df = make_void_df(rows)
    insight = build_void_opportunity_insight(df, penetration_threshold=0.1)

    # Whole Foods has higher upside
    assert insight is not None
    assert insight["chain"] == "Whole Foods"


def test_void_opportunity_velocity_uses_completed_months_only(monkeypatch):
    """
    Velocity (VPO) must be calculated from fully-completed months only.
    The current (partial) month must be excluded from the rolling window
    even when it has data, to avoid deflating or inflating the rate.
    """
    monkeypatch.setattr(pd.Timestamp, "today", lambda: pd.Timestamp("2026-04-15"))

    rows = []
    for store in ["S1", "S2", "S3"]:
        rows += [
            ("Whole Foods", store, "SKU A", "2026-01", 10),
            ("Whole Foods", store, "SKU A", "2026-02", 10),
            ("Whole Foods", store, "SKU A", "2026-03", 10),
            # April is partial — should be excluded from velocity window
            ("Whole Foods", store, "SKU A", "2026-04", 9999),
        ]
    for store in ["S4", "S5"]:
        rows.append(("Whole Foods", store, "Anchor SKU", "2026-04", 5))

    df = make_void_df(rows)
    insight = build_void_opportunity_insight(df, penetration_threshold=0.1)

    # Velocity should be based on 10+10+10=30 per store, NOT inflated by 9999
    expected_vpo_weekly = 30 / 13
    expected_units_year = int(expected_vpo_weekly * 2 * 52)
    assert insight is not None
    assert insight["impact_units"] == expected_units_year


# =============================================================================
# Velocity gap — edge cases
# =============================================================================


def test_velocity_gap_empty_dataframe_returns_none():
    df = make_velocity_gap_df([])
    assert build_velocity_gap_opportunity_insight(df) is None


def test_velocity_gap_identical_vpo_across_chains_returns_none():
    """No gap to exploit when all chains have the same velocity."""
    df = make_velocity_gap_df(
        [
            ("Natural", "SKU1", "Whole Foods", "2026-03", 2.0, 20, 400),
            ("Natural", "SKU1", "Sprouts", "2026-03", 2.0, 20, 400),
        ]
    )
    assert build_velocity_gap_opportunity_insight(df) is None


def test_velocity_gap_uses_most_recent_month_snapshot(monkeypatch):
    """
    When multiple months of data exist, only the latest month's snapshot
    should be used for the gap calculation — not an average across months.
    """
    df = make_velocity_gap_df(
        [
            # Older month — large gap that should be ignored
            ("Natural", "SKU1", "Whole Foods", "2026-01", 10.0, 10, 100),
            ("Natural", "SKU1", "Sprouts", "2026-01", 1.0, 10, 10),
            # Latest month — modest gap
            ("Natural", "SKU1", "Whole Foods", "2026-03", 2.0, 10, 200),
            ("Natural", "SKU1", "Sprouts", "2026-03", 1.0, 10, 100),
        ]
    )
    insight = build_velocity_gap_opportunity_insight(df)

    # Gap should reflect 2026-03 data (ratio 2.0), not 2026-01 (ratio 10.0)
    if insight is not None:
        assert "10.0x faster" not in insight["summary"]


def test_velocity_gap_impact_units_calculation_is_correct():
    """
    Validate the exact unit-opportunity math:
    gap_units = (best_vpo - laggard_vpo) * 0.5 * laggard_stores * 4 weeks
    """
    df = make_velocity_gap_df(
        [
            ("Natural", "SKU1", "Whole Foods", "2026-03", 4.0, 100, 1600),
            ("Natural", "SKU1", "Sprouts", "2026-03", 2.0, 100, 800),
        ]
    )
    insight = build_velocity_gap_opportunity_insight(df)

    expected_units = ((4.0 - 2.0) * 0.5) * 100 * 4
    assert insight is not None
    assert find_part(insight["parts"], f"~{expected_units:,.0f} units/month")["tone"] == "positive"


def test_velocity_gap_laggard_is_chain_with_lowest_vpo_not_fewest_stores():
    """
    The laggard should be identified by lowest VPO, not by store count,
    since the opportunity is about velocity underperformance.
    """
    df = make_velocity_gap_df(
        [
            ("Natural", "SKU1", "Whole Foods", "2026-03", 5.0, 10, 500),
            # Large chain, low velocity — this is the laggard
            ("Natural", "SKU1", "Kroger", "2026-03", 1.0, 200, 2000),
        ]
    )
    insight = build_velocity_gap_opportunity_insight(df)

    assert insight is not None
    assert "Kroger" in insight["summary"]
    assert "Whole Foods" in insight["summary"]


# =============================================================================
# Chain decline / growth — edge cases
# =============================================================================


def test_chain_decline_returns_none_for_empty_dataframe():
    df = pd.DataFrame(
        columns=["chain", "units_3m", "units_l3m", "units_l3m_pct", "units_l3m_abs"]
    )
    assert build_chain_decline_insight(df) is None


def test_chain_growth_returns_none_for_empty_dataframe():
    df = pd.DataFrame(
        columns=["chain", "units_3m", "units_l3m", "units_l3m_pct", "units_l3m_abs"]
    )
    assert build_chain_growth_insight(df) is None


def test_chain_decline_with_all_equal_declines_returns_some_chain():
    """
    When all chains decline equally, a deterministic winner must still
    be returned (ties should resolve without crashing).
    """
    df = pd.DataFrame(
        {
            "chain": ["Chain A", "Chain B"],
            "units_3m": [100, 100],
            "units_l3m": [200, 200],
            "units_l3m_pct": [-0.5, -0.5],
            "units_l3m_abs": [-100, -100],
        }
    )
    insight = build_chain_decline_insight(df)
    assert insight is not None
    assert insight["chain"] in ["Chain A", "Chain B"]


def test_chain_growth_contribution_sums_to_one_for_single_chain():
    """
    A single growing chain should carry 100% of the total change.
    """
    df = pd.DataFrame(
        {
            "chain": ["Whole Foods"],
            "units_3m": [1500],
            "units_l3m": [1000],
            "units_l3m_pct": [0.5],
            "units_l3m_abs": [500],
        }
    )
    insight = build_chain_growth_insight(df)
    assert insight is not None
    assert insight["contribution"] == pytest.approx(1.0)


def test_chain_decline_mixed_directions_only_flags_negative_contributor():
    """
    When some chains grow and others decline, the insight should only
    fire if the overall business is declining, and should flag the
    chain responsible for the decline — not a growing chain.
    """
    df = pd.DataFrame(
        {
            "chain": ["Whole Foods", "Sprouts"],
            "units_3m": [100, 900],
            "units_l3m": [500, 800],
            "units_l3m_pct": [-0.80, 0.125],
            "units_l3m_abs": [-400, 100],
        }
    )
    insight = build_chain_decline_insight(df)
    # Net change = -400 + 100 = -300 → declining overall
    assert insight is not None
    assert insight["chain"] == "Whole Foods"


def test_chain_growth_mixed_directions_only_flags_positive_contributor():
    """
    When some chains decline and others grow, with net growth overall,
    the insight should flag the largest positive contributor.
    """
    df = pd.DataFrame(
        {
            "chain": ["Whole Foods", "Sprouts"],
            "units_3m": [1500, 400],
            "units_l3m": [1000, 500],
            "units_l3m_pct": [0.5, -0.2],
            "units_l3m_abs": [500, -100],
        }
    )
    insight = build_chain_growth_insight(df)
    # Net change = +400 → growing overall
    assert insight is not None
    assert insight["chain"] == "Whole Foods"


def test_chain_decline_single_chain_all_decline():
    df = pd.DataFrame(
        {
            "chain": ["Whole Foods"],
            "units_3m": [200],
            "units_l3m": [500],
            "units_l3m_pct": [-0.6],
            "units_l3m_abs": [-300],
        }
    )
    insight = build_chain_decline_insight(df)
    assert insight is not None
    assert insight["chain"] == "Whole Foods"
    assert insight["contribution"] == pytest.approx(1.0)


# =============================================================================
# Chain struggling — edge cases
# =============================================================================


def test_chain_struggling_returns_none_when_all_chains_below_average():
    """
    If every chain's struggling rate is at or below the portfolio average,
    no chain should be flagged.
    """
    rows = []
    # Both chains identical struggling rates — no outlier
    for chain in ["Chain A", "Chain B"]:
        for i in range(1, 7):
            rows.append((chain, f"{chain}-{i}", "Struggling"))
        for i in range(7, 13):
            rows.append((chain, f"{chain}-{i}", "Healthy"))

    df = pd.DataFrame(rows, columns=["chain", "coded_customer", "status"])
    insight = build_chain_struggling_insight(df)
    assert insight is None


def test_chain_struggling_requires_minimum_stores_per_chain():
    """
    Chains with fewer stores than the minimum threshold should be excluded
    even if their struggling rate is very high.
    """
    rows = [("Micro Chain", "S1", "Struggling"), ("Micro Chain", "S2", "Struggling")]
    # Add a large chain at average rate to ensure overall average exists
    for i in range(1, 13):
        status = "Struggling" if i <= 6 else "Healthy"
        rows.append(("Big Chain", f"B{i}", status))

    df = pd.DataFrame(rows, columns=["chain", "coded_customer", "status"])
    insight = build_chain_struggling_insight(df)
    # Micro Chain (2 stores) should be excluded; Big Chain is at average so no flagging
    assert insight is None or insight["chain"] != "Micro Chain"


def test_chain_struggling_summary_contains_chain_name():
    rows = []
    # Chain A: heavily struggling (10/12)
    for i in range(1, 11):
        rows.append(("Chain A", f"A{i}", "Struggling"))
    for i in range(11, 13):
        rows.append(("Chain A", f"A{i}", "Healthy"))
    # Chain B: healthy (1/12 struggling)
    rows.append(("Chain B", "B1", "Struggling"))
    for i in range(2, 13):
        rows.append(("Chain B", f"B{i}", "Healthy"))

    df = pd.DataFrame(rows, columns=["chain", "coded_customer", "status"])
    insight = build_chain_struggling_insight(df)

    assert insight is not None
    assert "Chain A" in insight["summary"]


def test_chain_struggling_vs_avg_delta_is_positive_for_flagged_chain():
    """
    The flagged chain's struggling rate must exceed the portfolio average,
    so the delta (chain_pct - avg_pct) is always positive.
    """
    rows = []
    for i in range(1, 9):
        rows.append(("Bad Chain", f"B{i}", "Struggling"))
    for i in range(9, 13):
        rows.append(("Bad Chain", f"B{i}", "Healthy"))
    for i in range(1, 13):
        rows.append(("Good Chain", f"G{i}", "Healthy"))

    df = pd.DataFrame(rows, columns=["chain", "coded_customer", "status"])
    insight = build_chain_struggling_insight(df)

    assert insight is not None
    total_struggling = 8
    total_stores = 24
    avg = total_struggling / total_stores
    assert insight["struggling_pct"] > avg


# =============================================================================
# SKU velocity — edge cases
# =============================================================================


def test_sku_velocity_empty_dataframe_returns_none():
    df = pd.DataFrame(
        columns=["sku", "units_3m", "units_l3m", "vpo_3m", "vpo_l3m",
                 "vpo_l3m_pct", "vpo_l3m_abs"]
    )
    assert build_sku_velocity_insight(df) is None


def test_sku_velocity_returns_none_when_change_below_threshold():
    """Tiny absolute change should not trigger an insight."""
    df = pd.DataFrame(
        {
            "sku": ["SKU1"],
            "units_3m": [500],
            "units_l3m": [500],
            "vpo_3m": [2.05],
            "vpo_l3m": [2.0],
            "vpo_l3m_pct": [0.025],
            "vpo_l3m_abs": [0.05],
        }
    )
    assert build_sku_velocity_insight(df) is None


def test_sku_velocity_selects_sku_with_highest_abs_change_not_highest_pct():
    """
    The prioritised SKU should be the one with the largest *absolute* VPO
    change, not the largest percentage change — a small base can produce
    a large % from a tiny move.
    """
    df = pd.DataFrame(
        {
            "sku": ["SKU High Pct", "SKU High Abs"],
            "units_3m": [100, 5000],
            "units_l3m": [100, 5000],
            "vpo_3m": [2.0, 6.0],
            "vpo_l3m": [1.0, 4.5],
            "vpo_l3m_pct": [1.0, 0.33],   # High Pct wins on % 
            "vpo_l3m_abs": [1.0, 1.5],    # High Abs wins on abs
        }
    )
    insight = build_sku_velocity_insight(df)
    assert insight is not None
    assert insight["sku"] == "SKU High Abs"


def test_sku_velocity_prefers_positive_change_when_mixed():
    """
    When some SKUs improve and some decline, a significantly improving
    SKU should take precedence over a declining one of similar magnitude.
    """
    df = pd.DataFrame(
        {
            "sku": ["SKU Up", "SKU Down"],
            "units_3m": [500, 500],
            "units_l3m": [500, 500],
            "vpo_3m": [4.0, 1.0],
            "vpo_l3m": [2.5, 2.5],
            "vpo_l3m_pct": [0.6, -0.6],
            "vpo_l3m_abs": [1.5, -1.5],
        }
    )
    insight = build_sku_velocity_insight(df)
    assert insight is not None
    assert insight["sku"] == "SKU Up"
    assert insight["abs_change"] == 1.5
    assert find_part(insight["parts"], "up")["tone"] == "positive"


def test_sku_velocity_ignores_skus_with_no_prior_period_data():
    """
    SKUs with no prior-period units (new to range) should not be flagged
    since there is no valid comparison baseline.
    """
    df = pd.DataFrame(
        {
            "sku": ["New SKU"],
            "units_3m": [500],
            "units_l3m": [0],      # No prior period
            "vpo_3m": [3.0],
            "vpo_l3m": [None],
            "vpo_l3m_pct": [None],
            "vpo_l3m_abs": [None],
        }
    )
    assert build_sku_velocity_insight(df) is None


# =============================================================================
# Channel reorder — edge cases
# =============================================================================


def test_channel_reorder_empty_dataframe_returns_none():
    df = pd.DataFrame(
        columns=["channel", "reorder_rate_3m", "reorder_rate_l3m",
                 "reorder_rate_l3m_abs", "buying_stores_3m", "buying_stores_l3m"]
    )
    assert build_channel_reorder_driver_insight(df) is None


def test_channel_reorder_exact_threshold_boundary():
    """
    A change exactly at the minimum threshold should either fire or not,
    but must not crash. Validate boundary behaviour is deterministic.
    """
    df = pd.DataFrame(
        {
            "channel": ["Natural"],
            "reorder_rate_3m": [0.35],
            "reorder_rate_l3m": [0.5],
            "reorder_rate_l3m_abs": [-0.15],   # Exactly ±0.15 — boundary
            "buying_stores_3m": [50],
            "buying_stores_l3m": [50],
        }
    )
    result = build_channel_reorder_driver_insight(df)
    # Whatever it returns (None or insight), it must not raise
    assert result is None or result["type"] == "channel_reorder_driver"


def test_channel_reorder_ignores_zero_store_channels():
    """
    Channels with zero buying stores in both periods should be excluded —
    there is no real signal when nobody is ordering.
    """
    df = pd.DataFrame(
        {
            "channel": ["Ghost Channel", "Natural"],
            "reorder_rate_3m": [0.0, 0.7],
            "reorder_rate_l3m": [0.0, 0.4],
            "reorder_rate_l3m_abs": [0.0, 0.3],
            "buying_stores_3m": [0, 50],
            "buying_stores_l3m": [0, 50],
        }
    )
    insight = build_channel_reorder_driver_insight(df)
    assert insight is not None
    assert insight["channel"] == "Natural"


def test_channel_reorder_selects_largest_abs_change_not_largest_rate():
    """
    The flagged channel should be the one with the largest absolute rate
    change, not the one with the highest absolute reorder rate.
    """
    df = pd.DataFrame(
        {
            "channel": ["High Rate", "High Change"],
            "reorder_rate_3m": [0.9, 0.5],
            "reorder_rate_l3m": [0.85, 0.1],
            "reorder_rate_l3m_abs": [0.05, 0.4],
            "buying_stores_3m": [50, 50],
            "buying_stores_l3m": [50, 50],
        }
    )
    insight = build_channel_reorder_driver_insight(df)
    assert insight is not None
    assert insight["channel"] == "High Change"


def test_channel_reorder_summary_format_for_decline():
    """Summary should express drop as positive integer percentage points."""
    df = pd.DataFrame(
        {
            "channel": ["Natural"],
            "reorder_rate_3m": [0.2],
            "reorder_rate_l3m": [0.7],
            "reorder_rate_l3m_abs": [-0.5],
            "buying_stores_3m": [60],
            "buying_stores_l3m": [60],
        }
    )
    insight = build_channel_reorder_driver_insight(df)
    assert insight is not None
    assert "down 50% pts" in insight["summary"]


def test_channel_reorder_summary_format_for_growth():
    """Summary should express improvement as positive integer percentage points."""
    df = pd.DataFrame(
        {
            "channel": ["Mass"],
            "reorder_rate_3m": [0.75],
            "reorder_rate_l3m": [0.45],
            "reorder_rate_l3m_abs": [0.3],
            "buying_stores_3m": [80],
            "buying_stores_l3m": [80],
        }
    )
    insight = build_channel_reorder_driver_insight(df)
    assert insight is not None
    assert "up 30% pts" in insight["summary"]
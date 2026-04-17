import pandas as pd
import pandas.testing as pdt
import pytest

from backend.metrics.monthly_metric_calculators import (
    calculate_monthly_revenue,
    calculate_monthly_units,
    calculate_monthly_buying_stores,
    calculate_monthly_active_pods,
    calculate_monthly_vpo,
    calculate_monthly_existing_buyers,
    calculate_monthly_repeat_buyers,
    calculate_monthly_reorder_rate,
    calculate_monthly_new_pods,
)


# =============================================================================
# SHARED HELPERS
# =============================================================================

def make_period(s):
    return pd.Period(s, freq="M")


def make_periods(*args):
    return [make_period(s) for s in args]


# =============================================================================
# calculate_monthly_revenue
# =============================================================================

def build_revenue_df():
    data = [
        ("A", "A1", "2026-01", 100.0),
        ("A", "A1", "2026-02", 200.0),
        ("A", "A2", "2026-01", 50.0),
        ("B", "B1", "2026-01", 300.0),
    ]
    df = pd.DataFrame(data, columns=["chain", "coded_customer", "month_year", "revenue"])
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    return df


def test_monthly_revenue_no_group():
    df = build_revenue_df()
    result = calculate_monthly_revenue(df, group_cols=[])
    expected = pd.DataFrame({
        "month_year": pd.PeriodIndex(["2026-01", "2026-02"], freq="M"),
        "revenue": [450.0, 200.0],
    })
    pdt.assert_frame_equal(result.sort_values("month_year").reset_index(drop=True), expected)


def test_monthly_revenue_with_group():
    df = build_revenue_df()
    result = calculate_monthly_revenue(df, group_cols=["chain"])
    expected = pd.DataFrame({
        "month_year": pd.PeriodIndex(["2026-01", "2026-02", "2026-01"], freq="M"),
        "chain": ["A", "A", "B"],
        "revenue": [150.0, 200.0, 300.0],
    })
    pdt.assert_frame_equal(
        result.sort_values(["chain", "month_year"]).reset_index(drop=True),
        expected.sort_values(["chain", "month_year"]).reset_index(drop=True),
    )


# =============================================================================
# calculate_monthly_units
# =============================================================================

def build_units_df():
    data = [
        ("A", "2026-01", 10),
        ("A", "2026-01", 5),
        ("A", "2026-02", 20),
        ("B", "2026-01", 30),
    ]
    df = pd.DataFrame(data, columns=["chain", "month_year", "units"])
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    return df


def test_monthly_units_no_group():
    df = build_units_df()
    result = calculate_monthly_units(df, group_cols=[])
    expected = pd.DataFrame({
        "month_year": pd.PeriodIndex(["2026-01", "2026-02"], freq="M"),
        "units": [45, 20],
    })
    pdt.assert_frame_equal(result.sort_values("month_year").reset_index(drop=True), expected)


def test_monthly_units_with_group():
    df = build_units_df()
    result = calculate_monthly_units(df, group_cols=["chain"])
    expected = pd.DataFrame({
        "month_year": pd.PeriodIndex(["2026-01", "2026-02", "2026-01"], freq="M"),
        "chain": ["A", "A", "B"],
        "units": [15, 20, 30],
    })
    pdt.assert_frame_equal(
        result.sort_values(["chain", "month_year"]).reset_index(drop=True),
        expected.sort_values(["chain", "month_year"]).reset_index(drop=True),
    )


# =============================================================================
# calculate_monthly_buying_stores
# =============================================================================

def build_buying_stores_df():
    data = [
        ("A", "A1", "2026-01"),
        ("A", "A1", "2026-01"),  # duplicate — should count once
        ("A", "A2", "2026-01"),
        ("A", "A1", "2026-02"),
        ("B", "B1", "2026-01"),
    ]
    df = pd.DataFrame(data, columns=["chain", "coded_customer", "month_year"])
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    return df


def test_monthly_buying_stores_deduplicates():
    df = build_buying_stores_df()
    result = calculate_monthly_buying_stores(df, group_cols=["chain"])
    row = result[(result["chain"] == "A") & (result["month_year"] == make_period("2026-01"))].iloc[0]
    assert row["buying_stores"] == 2  # A1 and A2, not 3


def test_monthly_buying_stores_no_group():
    df = build_buying_stores_df()
    result = calculate_monthly_buying_stores(df, group_cols=[])
    row = result[result["month_year"] == make_period("2026-01")].iloc[0]
    assert row["buying_stores"] == 3  # A1, A2, B1


# =============================================================================
# calculate_monthly_new_pods
# =============================================================================

def build_new_pods_df():
    data = [
        ("A", "P1", "2026-01", 1),
        ("A", "P2", "2026-01", 1),
        ("A", "P1", "2026-02", 0),  # not new
        ("B", "P3", "2026-01", 1),
    ]
    df = pd.DataFrame(data, columns=["chain", "pod_helper", "month_year", "first_pod_flag"])
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    return df


def test_monthly_new_pods_with_group():
    df = build_new_pods_df()
    result = calculate_monthly_new_pods(df, group_cols=["chain"])
    row_a_jan = result[(result["chain"] == "A") & (result["month_year"] == make_period("2026-01"))].iloc[0]
    row_a_feb = result[(result["chain"] == "A") & (result["month_year"] == make_period("2026-02"))].iloc[0]
    assert row_a_jan["new_pods"] == 2
    assert row_a_feb["new_pods"] == 0


def test_monthly_new_pods_no_group():
    df = build_new_pods_df()
    result = calculate_monthly_new_pods(df, group_cols=[])
    row = result[result["month_year"] == make_period("2026-01")].iloc[0]
    assert row["new_pods"] == 3


# =============================================================================
# calculate_monthly_active_pods
# =============================================================================

def build_active_pods_df():
    """
    Chain A:
      P1 first appears Jan 2026 (pre-window pod doesn't exist here)
      P2 first appears Feb 2026
    Chain B:
      P3 first appears Dec 2025 (pre-window)
    """
    data = [
        # chain, pod_helper, month_year, first_pod_flag
        ("A", "P1", "2026-01", 1),
        ("A", "P1", "2026-02", 0),
        ("A", "P2", "2026-02", 1),
        ("B", "P3", "2025-12", 1),
        ("B", "P3", "2026-01", 0),
        ("B", "P3", "2026-02", 0),
    ]
    df = pd.DataFrame(data, columns=["chain", "pod_helper", "month_year", "first_pod_flag"])
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    return df


def test_active_pods_cumulates_correctly():
    df = build_active_pods_df()
    start = make_period("2026-01")
    end = make_period("2026-02")
    df_filtered = df[(df["month_year"] >= start) & (df["month_year"] <= end)]

    result = calculate_monthly_active_pods(
        df_filtered, df, group_cols=["chain"],
        selected_years=[2026]
    )

    # Chain A: Jan=1 pod, Feb=2 pods
    a_jan = result[(result["chain"] == "A") & (result["month_year"] == start)].iloc[0]
    a_feb = result[(result["chain"] == "A") & (result["month_year"] == end)].iloc[0]
    assert a_jan["active_pods"] == 1
    assert a_feb["active_pods"] == 2


def test_active_pods_carries_forward_pre_window_pods():
    df = build_active_pods_df()
    start = make_period("2026-01")
    end = make_period("2026-02")
    df_filtered = df[(df["month_year"] >= start) & (df["month_year"] <= end)]

    result = calculate_monthly_active_pods(
        df_filtered, df, group_cols=["chain"],
        selected_years=[2026]
    )

    # Chain B: P3 appeared in Dec 2025 (pre-window), should carry forward as 1 in Jan and Feb
    b_jan = result[(result["chain"] == "B") & (result["month_year"] == start)].iloc[0]
    b_feb = result[(result["chain"] == "B") & (result["month_year"] == end)].iloc[0]
    assert b_jan["active_pods"] == 1
    assert b_feb["active_pods"] == 1


def test_active_pods_no_group_cols():
    df = build_active_pods_df()
    start = make_period("2026-01")
    end = make_period("2026-02")
    df_filtered = df[(df["month_year"] >= start) & (df["month_year"] <= end)]

    result = calculate_monthly_active_pods(
        df_filtered, df, group_cols=[],
        selected_years=[2026]
    )

    # Jan: P1 + P3 = 2 active, Feb: P1 + P2 + P3 = 3 active
    jan = result[result["month_year"] == start].iloc[0]
    feb = result[result["month_year"] == end].iloc[0]
    assert jan["active_pods"] == 2
    assert feb["active_pods"] == 3


# =============================================================================
# calculate_monthly_vpo
# =============================================================================

def build_vpo_df():
    """
    Chain A:
      P1: first appears Jan, orders Jan + Feb
      P2: first appears Jan, orders Jan only
    Chain B:
      P3: first appears Dec 2025 (pre-window), orders Jan
    """
    data = [
        ("A", "A1", "P1", "2026-01", 1, 8),
        ("A", "A1", "P1", "2026-02", 0, 4),
        ("A", "A2", "P2", "2026-01", 1, 4),
        ("B", "B1", "P3", "2025-12", 1, 0),
        ("B", "B1", "P3", "2026-01", 0, 8),
    ]
    df = pd.DataFrame(data, columns=["chain", "coded_customer", "pod_helper", "month_year", "first_pod_flag", "units"])
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    return df


def test_monthly_vpo_basic():
    df = build_vpo_df()
    start = make_period("2026-01")
    end = make_period("2026-02")
    df_filtered = df[(df["month_year"] >= start) & (df["month_year"] <= end)]

    result = calculate_monthly_vpo(df_filtered, df, group_cols=["chain"])

    # Chain A Jan: 2 active pods, 12 units → vpo = 12 / 2 / 4 = 1.5
    a_jan = result[(result["chain"] == "A") & (result["month_year"] == start)].iloc[0]
    assert abs(a_jan["vpo"] - (12 / 2 / 4)) < 1e-9

    # Chain A Feb: 2 active pods, 4 units → vpo = 4 / 2 / 4 = 0.5
    a_feb = result[(result["chain"] == "A") & (result["month_year"] == end)].iloc[0]
    assert abs(a_feb["vpo"] - (4 / 2 / 4)) < 1e-9


def test_monthly_vpo_pre_window_pod_counts():
    df = build_vpo_df()
    start = make_period("2026-01")
    end = make_period("2026-02")
    df_filtered = df[(df["month_year"] >= start) & (df["month_year"] <= end)]

    result = calculate_monthly_vpo(df_filtered, df, group_cols=["chain"])

    # Chain B Jan: P3 appeared Dec (pre-window), so 1 active pod, 8 units → vpo = 8 / 1 / 4 = 2.0
    b_jan = result[(result["chain"] == "B") & (result["month_year"] == start)].iloc[0]
    assert abs(b_jan["vpo"] - (8 / 1 / 4)) < 1e-9


def test_monthly_vpo_zero_units_not_nan():
    df = build_vpo_df()
    start = make_period("2026-01")
    end = make_period("2026-02")
    df_filtered = df[(df["month_year"] >= start) & (df["month_year"] <= end)]

    result = calculate_monthly_vpo(df_filtered, df, group_cols=["chain"])

    # Chain B Feb: 1 active pod, 0 units → vpo = 0.0 not NaN
    b_feb = result[(result["chain"] == "B") & (result["month_year"] == end)].iloc[0]
    assert b_feb["vpo"] == 0.0


# =============================================================================
# calculate_monthly_existing_buyers
# =============================================================================

def build_existing_buyers_df():
    """
    Chain A:
      A1: first appears Dec 2025 (pre-window)
      A2: first appears Jan 2026
    Chain B:
      B1: first appears Jan 2026
      B2: first appears Feb 2026
    """
    data = [
        ("A", "A1", "2025-12", 1),
        ("A", "A1", "2026-01", 0),
        ("A", "A1", "2026-02", 0),
        ("A", "A2", "2026-01", 1),
        ("A", "A2", "2026-02", 0),
        ("B", "B1", "2026-01", 1),
        ("B", "B1", "2026-02", 0),
        ("B", "B2", "2026-02", 1),
    ]
    df = pd.DataFrame(data, columns=["chain", "coded_customer", "month_year", "first_store_flag"])
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    return df


def test_existing_buyers_pre_window_store_counted():
    df = build_existing_buyers_df()
    start = make_period("2026-01")
    end = make_period("2026-02")
    df_filtered = df[(df["month_year"] >= start) & (df["month_year"] <= end)]

    result = calculate_monthly_existing_buyers(
        df_filtered, df, group_cols=["chain"], selected_years=[2026]
    )

    # Chain A Jan: A1 is pre-window → 1 existing buyer, A2 is new → not existing
    a_jan = result[(result["chain"] == "A") & (result["month_year"] == start)].iloc[0]
    assert a_jan["existing_buyers"] == 1


def test_existing_buyers_accumulates():
    df = build_existing_buyers_df()
    start = make_period("2026-01")
    end = make_period("2026-02")
    df_filtered = df[(df["month_year"] >= start) & (df["month_year"] <= end)]

    result = calculate_monthly_existing_buyers(
        df_filtered, df, group_cols=["chain"], selected_years=[2026]
    )

    # Chain A Feb: A1 (pre-window) + A2 (new in Jan) = 2 existing buyers
    a_feb = result[(result["chain"] == "A") & (result["month_year"] == end)].iloc[0]
    assert a_feb["existing_buyers"] == 2


def test_existing_buyers_new_store_has_zero():
    df = build_existing_buyers_df()
    start = make_period("2026-01")
    end = make_period("2026-02")
    df_filtered = df[(df["month_year"] >= start) & (df["month_year"] <= end)]

    result = calculate_monthly_existing_buyers(
        df_filtered, df, group_cols=["chain"], selected_years=[2026]
    )

    # Chain B Jan: B1 is new → 0 existing buyers
    b_jan = result[(result["chain"] == "B") & (result["month_year"] == start)].iloc[0]
    assert b_jan["existing_buyers"] == 0


def test_existing_buyers_no_group_cols():
    df = build_existing_buyers_df()
    start = make_period("2026-01")
    end = make_period("2026-02")
    df_filtered = df[(df["month_year"] >= start) & (df["month_year"] <= end)]

    result = calculate_monthly_existing_buyers(
        df_filtered, df, group_cols=[], selected_years=[2026]
    )

    # Jan: only A1 is pre-window → 1 existing buyer globally
    jan = result[result["month_year"] == start].iloc[0]
    assert jan["existing_buyers"] == 1

    # Feb: A1 + A2 + B1 = 3 existing buyers
    feb = result[result["month_year"] == end].iloc[0]
    assert feb["existing_buyers"] == 3


# =============================================================================
# calculate_monthly_repeat_buyers
# =============================================================================

def build_repeat_buyers_df():
    data = [
        ("A", "A1", "2026-01", 1),  # reorder
        ("A", "A1", "2026-02", 0),  # not a reorder
        ("A", "A2", "2026-01", 0),
        ("A", "A2", "2026-02", 1),  # reorder
        ("B", "B1", "2026-01", 1),
        ("B", "B1", "2026-02", 1),
    ]
    df = pd.DataFrame(data, columns=["chain", "coded_customer", "month_year", "reorder_flag"])
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    return df


def test_repeat_buyers_basic():
    df = build_repeat_buyers_df()
    start = make_period("2026-01")
    end = make_period("2026-02")
    df_filtered = df[(df["month_year"] >= start) & (df["month_year"] <= end)]

    result = calculate_monthly_repeat_buyers(
        df_filtered, group_cols=["chain"], selected_years=[2026]
    )

    # Chain A Jan: A1 reordered → 1 repeat buyer
    a_jan = result[(result["chain"] == "A") & (result["month_year"] == start)].iloc[0]
    assert a_jan["repeat_buyers"] == 1

    # Chain A Feb: A2 reordered → 1 repeat buyer
    a_feb = result[(result["chain"] == "A") & (result["month_year"] == end)].iloc[0]
    assert a_feb["repeat_buyers"] == 1


def test_repeat_buyers_fills_missing_months_with_zero():
    """Store exists in spine but has no reorders in a month → should be 0 not NaN"""
    data = [
        ("A", "A1", "2026-01", 1),
        ("A", "A1", "2026-03", 1),  # gap in Feb
    ]
    df = pd.DataFrame(data, columns=["chain", "coded_customer", "month_year", "reorder_flag"])
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    df_filtered = df.copy()

    result = calculate_monthly_repeat_buyers(
        df_filtered, group_cols=["chain"], selected_years=[2026]
    )

    feb = result[(result["chain"] == "A") & (result["month_year"] == make_period("2026-02"))]
    assert len(feb) == 1
    assert feb.iloc[0]["repeat_buyers"] == 0


def test_repeat_buyers_no_group_cols():
    df = build_repeat_buyers_df()
    start = make_period("2026-01")
    end = make_period("2026-02")
    df_filtered = df[(df["month_year"] >= start) & (df["month_year"] <= end)]

    result = calculate_monthly_repeat_buyers(
        df_filtered, group_cols=[], selected_years=[2026]
    )

    # Jan: A1 + B1 = 2 repeat buyers
    jan = result[result["month_year"] == start].iloc[0]
    assert jan["repeat_buyers"] == 2


# =============================================================================
# calculate_monthly_reorder_rate
# =============================================================================

def build_reorder_rate_df():
    """
    Chain A:
      A1: first appears Dec 2025 (pre-window), orders Jan + Feb, reorders both
      A2: first appears Jan 2026, orders Jan + Feb, reorders Feb only
    Chain B:
      B1: first appears Jan 2026, orders Jan only, no reorder
    """
    data = [
        ("A", "A1", "2025-12", 1, 0),  # first_store_flag=1, reorder=0
        ("A", "A1", "2026-01", 0, 1),
        ("A", "A1", "2026-02", 0, 1),
        ("A", "A2", "2026-01", 1, 0),
        ("A", "A2", "2026-02", 0, 1),
        ("B", "B1", "2026-01", 1, 0),
    ]
    df = pd.DataFrame(data, columns=["chain", "coded_customer", "month_year", "first_store_flag", "reorder_flag"])
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    return df


def test_monthly_reorder_rate_pre_window_store_is_existing_buyer():
    df = build_reorder_rate_df()
    start = make_period("2026-01")
    end = make_period("2026-02")
    df_filtered = df[(df["month_year"] >= start) & (df["month_year"] <= end)]

    result = calculate_monthly_reorder_rate(
        df_filtered, df, group_cols=["chain"], selected_years=[2026]
    )

    # Chain A Jan:
    # existing_buyers = 1 (A1 is pre-window), repeat_buyers = 1 (A1 reordered)
    # rate = 1/1
    a_jan = result[(result["chain"] == "A") & (result["month_year"] == start)].iloc[0]
    assert abs(a_jan["reorder_rate"] - 1.0) < 1e-9


def test_monthly_reorder_rate_new_store_has_zero_denominator():
    df = build_reorder_rate_df()
    start = make_period("2026-01")
    end = make_period("2026-02")
    df_filtered = df[(df["month_year"] >= start) & (df["month_year"] <= end)]

    result = calculate_monthly_reorder_rate(
        df_filtered, df, group_cols=["chain"], selected_years=[2026]
    )

    # Chain B Jan: B1 is new → 0 existing buyers → reorder_rate = NaN or 0
    b_jan = result[(result["chain"] == "B") & (result["month_year"] == start)].iloc[0]
    assert b_jan["reorder_rate"] == 0.0 or pd.isna(b_jan["reorder_rate"])


def test_monthly_reorder_rate_accumulates_existing_buyers():
    df = build_reorder_rate_df()
    start = make_period("2026-01")
    end = make_period("2026-02")
    df_filtered = df[(df["month_year"] >= start) & (df["month_year"] <= end)]

    result = calculate_monthly_reorder_rate(
        df_filtered, df, group_cols=["chain"], selected_years=[2026]
    )

    # Chain A Feb:
    # existing_buyers = 2 (A1 pre-window + A2 new in Jan)
    # repeat_buyers = 2 (A1 + A2 both reordered)
    # rate = 2/2 = 1.0
    a_feb = result[(result["chain"] == "A") & (result["month_year"] == end)].iloc[0]
    assert abs(a_feb["reorder_rate"] - 1.0) < 1e-9


def test_monthly_reorder_rate_no_group_cols():
    df = build_reorder_rate_df()
    start = make_period("2026-01")
    end = make_period("2026-02")
    df_filtered = df[(df["month_year"] >= start) & (df["month_year"] <= end)]

    result = calculate_monthly_reorder_rate(
        df_filtered, df, group_cols=[], selected_years=[2026]
    )

    # Jan globally: existing = 1 (A1), repeat = 1 (A1) → rate = 1.0
    jan = result[result["month_year"] == start].iloc[0]
    assert abs(jan["reorder_rate"] - 1.0) < 1e-9

    # Feb globally: existing = 3 (A1 + A2 + B1), repeat = 2 (A1 + A2) → rate = 2/3
    feb = result[result["month_year"] == end].iloc[0]
    assert abs(feb["reorder_rate"] - (2 / 3)) < 1e-9
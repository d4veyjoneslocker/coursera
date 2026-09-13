import pandas as pd
import pytest

from backend.metrics.metric_comparisons import compare_metric

from backend.metrics.metric_growth_rates import (
    calculate_buying_stores_3m,
    calculate_vpo_3m,
    calculate_reorder_rate_3m,
)


# =========================================================
# Helpers
# =========================================================

def p(x: str) -> pd.Period:
    return pd.Period(x, freq="M")


Q1_2026_MONTHS = list(
    pd.period_range("2026-01", "2026-03", freq="M")
)


# =========================================================
# Fixtures
# =========================================================

def build_period_test_df():
    """
    Includes:
    - Q4 2025 so compare_metric(... comparison="PP") has a comparison period
    - Q1 2026 as the period under test
    - Multiple stores
    - A missing February row for A2
    - Prior history so velocity / reorder calculations have context
    """

    data = [
        # -------------------------------------------------
        # Prior history
        # -------------------------------------------------
        ("A", "A1", "P1", "2025-09", 5, 1, 1, 0),
        ("A", "A2", "P2", "2025-09", 4, 1, 1, 0),

        # -------------------------------------------------
        # Q4 2025 — comparison period
        # -------------------------------------------------
        ("A", "A1", "P1", "2025-10", 10, 0, 0, 1),
        ("A", "A2", "P2", "2025-10", 5, 0, 0, 1),

        ("A", "A1", "P1", "2025-11", 12, 0, 0, 1),
        ("A", "A2", "P2", "2025-11", 6, 0, 0, 1),

        ("A", "A1", "P1", "2025-12", 14, 0, 0, 1),
        ("A", "A2", "P2", "2025-12", 7, 0, 0, 1),

        # -------------------------------------------------
        # Q1 2026 — current period
        # -------------------------------------------------
        ("A", "A1", "P1", "2026-01", 20, 0, 0, 1),
        ("A", "A2", "P2", "2026-01", 10, 0, 0, 1),

        ("A", "A1", "P1", "2026-02", 25, 0, 0, 1),
        # A2 intentionally has no February row

        ("A", "A1", "P1", "2026-03", 30, 0, 0, 1),
        ("A", "A2", "P2", "2026-03", 15, 0, 0, 1),
    ]

    df = pd.DataFrame(
        data,
        columns=[
            "chain",
            "coded_customer",
            "pod_helper",
            "month_year",
            "units",
            "first_pod_flag",
            "first_store_flag",
            "reorder_flag",
        ],
    )

    df["month_year"] = pd.PeriodIndex(
        df["month_year"],
        freq="M",
    )

    return df


def build_zero_reorder_denominator_df():
    """
    Current period contains only a brand-new buyer,
    so existing buyers / reorder denominator should be zero.
    """

    data = [
        # Q4 comparison row
        ("A", "A0", "P0", "2025-12", 5, 1, 1, 0),

        # Q1 current row — brand new store
        ("A", "A1", "P1", "2026-03", 10, 1, 1, 0),
    ]

    df = pd.DataFrame(
        data,
        columns=[
            "chain",
            "coded_customer",
            "pod_helper",
            "month_year",
            "units",
            "first_pod_flag",
            "first_store_flag",
            "reorder_flag",
        ],
    )

    df["month_year"] = pd.PeriodIndex(
        df["month_year"],
        freq="M",
    )

    return df


# =========================================================
# Units
# =========================================================

def test_compare_metric_units_matches_direct_period_sum():
    df = build_period_test_df()

    q1_df = df[df["month_year"].isin(Q1_2026_MONTHS)]

    expected = (
        q1_df.groupby("chain")["units"]
        .sum()
        .loc["A"]
    )

    result = compare_metric(
        df=df,
        df_full=df,
        metric="units",
        period="Q1",
        year=2026,
        comparison="PP",
        group_cols=["chain"],
    )

    row = result[result["chain"] == "A"].iloc[0]

    assert row["value_current"] == expected


# =========================================================
# Buying Stores
# =========================================================

def test_compare_metric_buying_stores_matches_existing_3m_logic():
    df = build_period_test_df()

    q1_df = df[df["month_year"].isin(Q1_2026_MONTHS)]

    old_result = calculate_buying_stores_3m(
        df=q1_df,
        group_cols=["chain", "month_year"],
        selected_months=Q1_2026_MONTHS,
    )

    old_value = old_result.loc[
        (
            (old_result["chain"] == "A")
            & (old_result["month_year"] == p("2026-03"))
        ),
        "buying_stores_3m",
    ].iloc[0]

    new_result = compare_metric(
        df=df,
        df_full=df,
        metric="buying_stores",
        period="Q1",
        year=2026,
        comparison="PP",
        group_cols=["chain"],
    )

    new_value = new_result.loc[
        new_result["chain"] == "A",
        "value_current",
    ].iloc[0]

    assert new_value == old_value


# =========================================================
# Velocity
# =========================================================

def test_compare_metric_velocity_matches_existing_3m_logic():
    df = build_period_test_df()

    q1_df = df[df["month_year"].isin(Q1_2026_MONTHS)]

    old_result = calculate_vpo_3m(
        df_filtered=q1_df,
        df_full=df,
        group_cols=["chain"],
        selected_months=Q1_2026_MONTHS,
    )

    old_value = old_result.loc[
        (
            (old_result["chain"] == "A")
            & (old_result["month_year"] == p("2026-03"))
        ),
        "vpo_3m",
    ].iloc[0]

    new_result = compare_metric(
        df=df,
        df_full=df,
        metric="velocity",
        period="Q1",
        year=2026,
        comparison="PP",
        group_cols=["chain"],
    )

    new_value = new_result.loc[
        new_result["chain"] == "A",
        "value_current",
    ].iloc[0]

    assert new_value == pytest.approx(old_value)


def test_compare_metric_velocity_handles_missing_month_row():
    """
    A2 has sales in January and March but no February row.

    The new period calculation should still match the old
    spine-based 3M calculation.
    """

    df = build_period_test_df()

    assert not (
        (df["coded_customer"] == "A2")
        & (df["month_year"] == p("2026-02"))
    ).any()

    q1_df = df[df["month_year"].isin(Q1_2026_MONTHS)]

    old_result = calculate_vpo_3m(
        df_filtered=q1_df,
        df_full=df,
        group_cols=["chain"],
        selected_months=Q1_2026_MONTHS,
    )

    old_value = old_result.loc[
        (
            (old_result["chain"] == "A")
            & (old_result["month_year"] == p("2026-03"))
        ),
        "vpo_3m",
    ].iloc[0]

    new_result = compare_metric(
        df=df,
        df_full=df,
        metric="velocity",
        period="Q1",
        year=2026,
        comparison="PP",
        group_cols=["chain"],
    )

    new_value = new_result.loc[
        new_result["chain"] == "A",
        "value_current",
    ].iloc[0]

    assert new_value == pytest.approx(old_value)


# =========================================================
# Reorder Rate
# =========================================================

def test_compare_metric_reorder_rate_matches_existing_3m_logic():
    df = build_period_test_df()

    q1_df = df[df["month_year"].isin(Q1_2026_MONTHS)]

    old_result = calculate_reorder_rate_3m(
        df_filtered=q1_df,
        df_full=df,
        group_cols=["chain"],
        selected_months=Q1_2026_MONTHS,
    )

    old_value = old_result.loc[
        (
            (old_result["chain"] == "A")
            & (old_result["month_year"] == p("2026-03"))
        ),
        "reorder_rate_3m",
    ].iloc[0]

    new_result = compare_metric(
        df=df,
        df_full=df,
        metric="reorder_rate",
        period="Q1",
        year=2026,
        comparison="PP",
        group_cols=["chain"],
    )

    new_value = new_result.loc[
        new_result["chain"] == "A",
        "value_current",
    ].iloc[0]

    assert new_value == pytest.approx(old_value)


def test_compare_metric_reorder_rate_zero_denominator_matches_existing_logic():
    df = build_zero_reorder_denominator_df()

    q1_df = df[df["month_year"].isin(Q1_2026_MONTHS)]

    old_result = calculate_reorder_rate_3m(
        df_filtered=q1_df,
        df_full=df,
        group_cols=["chain"],
        selected_months=Q1_2026_MONTHS,
    )

    old_value = old_result.loc[
        (
            (old_result["chain"] == "A")
            & (old_result["month_year"] == p("2026-03"))
        ),
        "reorder_rate_3m",
    ].iloc[0]

    new_result = compare_metric(
        df=df,
        df_full=df,
        metric="reorder_rate",
        period="Q1",
        year=2026,
        comparison="PP",
        group_cols=["chain"],
    )

    new_value = new_result.loc[
        new_result["chain"] == "A",
        "value_current",
    ].iloc[0]

    assert old_value == pytest.approx(0.0)
    assert new_value == pytest.approx(old_value)


# =========================================================
# Comparison Math
# =========================================================

def test_compare_metric_returns_correct_changes():
    df = build_period_test_df()

    result = compare_metric(
        df=df,
        df_full=df,
        metric="units",
        period="Q1",
        year=2026,
        comparison="PP",
        group_cols=["chain"],
    )

    row = result[result["chain"] == "A"].iloc[0]

    expected_abs = (
        row["value_current"]
        - row["value_comparison"]
    )

    expected_pct = (
        row["value_current"]
        / row["value_comparison"]
        - 1
    )

    assert row["abs_change"] == pytest.approx(expected_abs)
    assert row["pct_change"] == pytest.approx(expected_pct)
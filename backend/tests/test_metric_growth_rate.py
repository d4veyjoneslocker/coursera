import pandas as pd
import pandas.testing as pdt
import pytest

from backend.metrics.metric_growth_rates import (
    add_additive_metric_3m,
    calculate_buying_stores_3m,
    add_prior_month_columns,
    calculate_vpo_3m,
    calculate_reorder_rate_3m,
    add_pct_change_columns
)


def p(x: str) -> pd.Period:
    return pd.Period(x, freq="M")


# ---------------------------------------------------------
# Helper-only fixtures
# ---------------------------------------------------------

def build_monthly_units_gap_df():
    return pd.DataFrame(
        {
            "chain": ["A", "A"],
            "month_year": pd.PeriodIndex(["2026-01", "2026-03"], freq="M"),
            "units": [10, 20],
        }
    )


def build_buying_stores_two_month_df():
    return pd.DataFrame(
        {
            "chain": ["A", "A"],
            "coded_customer": ["A1", "A2"],
            "month_year": pd.PeriodIndex(["2026-01", "2026-02"], freq="M"),
        }
    )


# ---------------------------------------------------------
# Integration fixture for VPO / reorder 3m
# ---------------------------------------------------------

def build_three_month_integration_df():
    data = [
        # Chain A, pre-window active store/pod
        # This one should still get a March row via the monthly calculators
        # even though it has no March transaction.
        ("A", "A1", "P1", "2025-12", 5, 1, 1, 0),
        ("A", "A1", "P1", "2026-01", 4, 0, 0, 1),
        ("A", "A1", "P1", "2026-02", 6, 0, 0, 1),

        # Chain B only exists to anchor reporting end at March
        ("B", "B1", "P2", "2026-03", 1, 1, 1, 0),
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
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    return df


# ---------------------------------------------------------
# add_additive_metric_3m
# ---------------------------------------------------------

def test_add_additive_metric_3m_fills_missing_middle_month_and_rolls_zero():
    df = build_monthly_units_gap_df()

    result = (
        add_additive_metric_3m(df, ["chain", "month_year"], "units")
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    expected = pd.DataFrame(
        {
            "chain": ["A", "A", "A"],
            "month_year": pd.PeriodIndex(["2026-01", "2026-02", "2026-03"], freq="M"),
            "units": [10.0, 0.0, 20.0],
            "units_3m": [None, None, 30.0],
        }
    )

    pdt.assert_frame_equal(result, expected, check_exact=False, rtol=1e-9)


# ---------------------------------------------------------
# add_prior_month_columns
# ---------------------------------------------------------

def test_add_prior_month_columns_preserves_nan_for_missing_prior_month():
    df = build_monthly_units_gap_df()

    result = (
        add_prior_month_columns(df, ["chain", "month_year"], "units", l1m=True)
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    # Jan has no prior month
    assert pd.isna(result.loc[0, "units_l1m"])

    # Feb exists in the spine but has no units value
    assert pd.isna(result.loc[1, "units"])
    assert result.loc[1, "units_l1m"] == 10

    # Mar's prior month is Feb, which is missing -> should stay NaN
    assert pd.isna(result.loc[2, "units_l1m"])


# ---------------------------------------------------------
# calculate_buying_stores_3m
# ---------------------------------------------------------

def test_calculate_buying_stores_3m_under_three_months_returns_zero_rows_not_error():
    df = build_buying_stores_two_month_df()

    result = (
        calculate_buying_stores_3m(df, ["chain", "month_year"])
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    expected = pd.DataFrame(
        {
            "chain": ["A", "A", "A"],
            "month_year": pd.PeriodIndex(["2026-01", "2026-02", "2026-03"], freq="M"),
            "buying_stores_3m": [0.0, 0.0, 2.0],
        }
    )

    pdt.assert_frame_equal(result, expected, check_exact=False, rtol=1e-9)


# ---------------------------------------------------------
# calculate_vpo_3m
# ---------------------------------------------------------

def test_calculate_vpo_3m_uses_zero_for_missing_latest_month_when_reporting_end_extends():
    df_full = build_three_month_integration_df()
    df_filtered = df_full[
        (df_full["month_year"] >= p("2026-01")) &
        (df_full["month_year"] <= p("2026-03"))
    ]

    result = (
        calculate_vpo_3m(
            df_filtered=df_filtered,
            df_full=df_full,
            group_cols=["chain"],
            selected_years=[2026],
            selected_months=[p("2026-01"), p("2026-02"), p("2026-03")],
        )
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    chain_a_mar = result[
        (result["chain"] == "A") & (result["month_year"] == p("2026-03"))
    ].iloc[0]

    # Chain A monthly units should behave like Jan=4, Feb=6, Mar=0
    # Active pods should behave like Jan=1, Feb=1, Mar=1
    # So March 3m VPO = (4+6+0) / (1+1+1) / 4
    assert chain_a_mar["vpo_3m"] == pytest.approx(10 / 3 / 4)


# ---------------------------------------------------------
# calculate_reorder_rate_3m
# ---------------------------------------------------------

def test_calculate_reorder_rate_3m_uses_zero_for_missing_latest_month_when_reporting_end_extends():
    df_full = build_three_month_integration_df()
    df_filtered = df_full[
        (df_full["month_year"] >= p("2026-01")) &
        (df_full["month_year"] <= p("2026-03"))
    ]

    result = (
        calculate_reorder_rate_3m(
            df_filtered=df_filtered,
            df_full=df_full,
            group_cols=["chain"],
            selected_years=[2026],
            selected_months=[p("2026-01"), p("2026-02"), p("2026-03")],
        )
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    chain_a_mar = result[
        (result["chain"] == "A") & (result["month_year"] == p("2026-03"))
    ].iloc[0]

    # Chain A existing buyers should behave like Jan=1, Feb=1, Mar=1
    # Chain A repeat buyers should behave like Jan=1, Feb=1, Mar=0
    # So March 3m reorder rate = 2 / 3
    assert chain_a_mar["reorder_rate_3m"] == pytest.approx(2 / 3)

def p(x: str) -> pd.Period:
    return pd.Period(x, freq="M")


# =========================================================
# Helper fixtures
# =========================================================

def build_additive_gap_df():
    return pd.DataFrame(
        {
            "chain": ["A", "A"],
            "month_year": pd.PeriodIndex(["2026-01", "2026-03"], freq="M"),
            "units": [10, 20],
        }
    )


def build_additive_no_group_df():
    return pd.DataFrame(
        {
            "month_year": pd.PeriodIndex(["2026-01", "2026-02", "2026-03"], freq="M"),
            "units": [5, 10, 15],
        }
    )


def build_buying_stores_two_month_df():
    return pd.DataFrame(
        {
            "chain": ["A", "A"],
            "coded_customer": ["A1", "A2"],
            "month_year": pd.PeriodIndex(["2026-01", "2026-02"], freq="M"),
        }
    )


def build_buying_stores_three_month_df():
    return pd.DataFrame(
        {
            "chain": ["A", "A", "A", "A"],
            "coded_customer": ["A1", "A2", "A1", "A3"],
            "month_year": pd.PeriodIndex(
                ["2026-01", "2026-02", "2026-03", "2026-03"], freq="M"
            ),
        }
    )


def build_vpo_reorder_integration_df():
    data = [
        # chain A store active before window, orders Jan and Feb, missing Mar
        ("A", "A1", "P1", "2025-12", 5, 1, 1, 0),
        ("A", "A1", "P1", "2026-01", 4, 0, 0, 1),
        ("A", "A1", "P1", "2026-02", 6, 0, 0, 1),

        # chain B exists only to anchor reporting end at Mar 2026
        ("B", "B1", "P2", "2026-03", 1, 1, 1, 0),
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
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    return df


def build_zero_pod_df():
    data = [
        # no first_pod_flag anywhere in reporting months, so active_pods_3m should be 0
        ("A", "A1", "P1", "2026-01", 4, 0, 0, 1),
        ("A", "A1", "P1", "2026-02", 6, 0, 0, 1),
        ("B", "B1", "P2", "2026-03", 1, 0, 1, 0),
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
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    return df


# =========================================================
# add_pct_change_columns
# =========================================================

def test_add_pct_change_columns_l1m_and_l3m():
    df = pd.DataFrame(
        {
            "units": [100, 120],
            "units_l1m": [50, 100],
            "units_3m": [125, 150],
            "units_l3m": [80, 120],
        }
    )

    result = add_pct_change_columns(df.copy(), "units", l1m=True, l3m=True)

    assert result.loc[0, "units_l1m_pct"] == pytest.approx(1.0)      # 100/50 - 1
    assert result.loc[1, "units_l1m_pct"] == pytest.approx(0.2)      # 120/100 - 1
    assert result.loc[0, "units_l3m_pct"] == pytest.approx((125 - 80) / 80)
    assert result.loc[1, "units_l3m_pct"] == pytest.approx((150 - 120) / 120)


def test_add_pct_change_columns_returns_nan_when_prior_not_positive():
    df = pd.DataFrame(
        {
            "units": [100, 120],
            "units_l1m": [0, -5],
        }
    )

    result = add_pct_change_columns(df.copy(), "units", l1m=True)

    assert pd.isna(result.loc[0, "units_l1m_pct"])
    assert pd.isna(result.loc[1, "units_l1m_pct"])


# =========================================================
# add_additive_metric_3m
# =========================================================

def test_add_additive_metric_3m_fills_missing_middle_month_and_rolls():
    df = build_additive_gap_df()

    result = (
        add_additive_metric_3m(df, ["chain", "month_year"], "units")
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    expected = pd.DataFrame(
        {
            "chain": ["A", "A", "A"],
            "month_year": pd.PeriodIndex(["2026-01", "2026-02", "2026-03"], freq="M"),
            "units": [10.0, 0.0, 20.0],
            "units_3m": [None, None, 30.0],
        }
    )

    pdt.assert_frame_equal(result, expected, check_exact=False, rtol=1e-9)


def test_add_additive_metric_3m_no_group_cols():
    df = build_additive_no_group_df()

    result = (
        add_additive_metric_3m(df, ["month_year"], "units")
        .sort_values("month_year")
        .reset_index(drop=True)
    )

    expected = pd.DataFrame(
        {
            "month_year": pd.PeriodIndex(["2026-01", "2026-02", "2026-03"], freq="M"),
            "units": [5, 10, 15],
            "units_3m": [None, None, 30.0],
        }
    )

    pdt.assert_frame_equal(result, expected, check_exact=False, rtol=1e-9)


# =========================================================
# add_prior_month_columns
# =========================================================

def test_add_prior_month_columns_l1m_preserves_nan_for_missing_prior():
    df = build_additive_gap_df()

    result = (
        add_prior_month_columns(df, ["chain", "month_year"], "units", l1m=True)
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    # Jan has no prior month
    assert pd.isna(result.loc[0, "units_l1m"])

    # Feb is created by spine, units stays NaN, prior is Jan's 10
    assert pd.isna(result.loc[1, "units"])
    assert result.loc[1, "units_l1m"] == 10

    # Mar's prior month is Feb, which is missing -> should stay NaN
    assert pd.isna(result.loc[2, "units_l1m"])


def test_add_prior_month_columns_l3m_uses_metric_3m_shift():
    df = pd.DataFrame(
        {
            "chain": ["A", "A", "A", "A", "A", "A"],
            "month_year": pd.PeriodIndex(
                ["2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03"],
                freq="M",
            ),
            "units": [10, 20, 30, 40, 50, 60],
            "units_3m": [None, None, 60, 90, 120, 150],
        }
    )

    result = (
        add_prior_month_columns(df, ["chain", "month_year"], "units", l3m=True)
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    # March l3m should be December's 3m block, since shift(3)
    mar_row = result[result["month_year"] == p("2026-03")].iloc[0]
    assert mar_row["units_l3m"] == 60

    # Earlier rows should still be NaN where not enough history exists
    oct_row = result[result["month_year"] == p("2025-10")].iloc[0]
    jan_row = result[result["month_year"] == p("2026-01")].iloc[0]
    assert pd.isna(oct_row["units_l3m"])
    assert pd.isna(jan_row["units_l3m"])


def test_add_prior_month_columns_py_shift():
    df = pd.DataFrame(
        {
            "month_year": pd.PeriodIndex(
                [
                    "2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06",
                    "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12",
                    "2026-01",
                ],
                freq="M",
            ),
            "units": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 100],
        }
    )

    result = (
        add_prior_month_columns(df, ["month_year"], "units", py=True)
        .sort_values("month_year")
        .reset_index(drop=True)
    )

    jan_2026 = result[result["month_year"] == p("2026-01")].iloc[0]
    assert jan_2026["units_py"] == 1


# =========================================================
# calculate_buying_stores_3m
# =========================================================

def test_calculate_buying_stores_3m_under_three_months_returns_zero_rows_not_error():
    df = build_buying_stores_two_month_df()

    result = (
        calculate_buying_stores_3m(df, ["chain", "month_year"])
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    expected = pd.DataFrame(
        {
            "chain": ["A", "A", "A"],
            "month_year": pd.PeriodIndex(["2026-01", "2026-02", "2026-03"], freq="M"),
            "buying_stores_3m": [0.0, 0.0, 2.0],
        }
    )

    pdt.assert_frame_equal(result, expected, check_exact=False, rtol=1e-9)


def test_calculate_buying_stores_3m_counts_distinct_stores_across_window():
    df = build_buying_stores_three_month_df()

    result = (
        calculate_buying_stores_3m(df, ["chain", "month_year"])
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    mar_row = result[result["month_year"] == p("2026-03")].iloc[0]

    # Jan-Mar window includes A1, A2, A3 -> 3 unique stores
    assert mar_row["buying_stores_3m"] == 3


# =========================================================
# calculate_vpo_3m
# =========================================================

def test_calculate_vpo_3m_uses_zero_for_missing_latest_month_when_reporting_end_extends():
    df_full = build_vpo_reorder_integration_df()
    df_filtered = df_full[
        (df_full["month_year"] >= p("2026-01")) &
        (df_full["month_year"] <= p("2026-03"))
    ]

    result = (
        calculate_vpo_3m(
            df_filtered=df_filtered,
            df_full=df_full,
            group_cols=["chain"],
            selected_years=[2026],
            selected_months=[p("2026-01"), p("2026-02"), p("2026-03")],
        )
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    chain_a_mar = result[
        (result["chain"] == "A") & (result["month_year"] == p("2026-03"))
    ].iloc[0]

    # Chain A:
    # units by month = Jan 4, Feb 6, Mar 0
    # active pods by month = Jan 1, Feb 1, Mar 1
    # vpo_3m at Mar = (4 + 6 + 0) / (1 + 1 + 1) / 4 = 10 / 3 / 4
    assert chain_a_mar["vpo_3m"] == pytest.approx(10 / 3 / 4)


def test_calculate_vpo_3m_returns_nan_when_active_pods_3m_is_zero():
    df_full = build_zero_pod_df()
    df_filtered = df_full[
        (df_full["month_year"] >= p("2026-01")) &
        (df_full["month_year"] <= p("2026-03"))
    ]

    result = (
        calculate_vpo_3m(
            df_filtered=df_filtered,
            df_full=df_full,
            group_cols=["chain"],
            selected_years=[2026],
            selected_months=[p("2026-01"), p("2026-02"), p("2026-03")],
        )
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    chain_a_mar = result[
        (result["chain"] == "A") & (result["month_year"] == p("2026-03"))
    ].iloc[0]

    assert pd.isna(chain_a_mar["vpo_3m"])


# =========================================================
# calculate_reorder_rate_3m
# =========================================================

def test_calculate_reorder_rate_3m_uses_zero_for_missing_latest_month_when_reporting_end_extends():
    df_full = build_vpo_reorder_integration_df()
    df_filtered = df_full[
        (df_full["month_year"] >= p("2026-01")) &
        (df_full["month_year"] <= p("2026-03"))
    ]

    result = (
        calculate_reorder_rate_3m(
            df_filtered=df_filtered,
            df_full=df_full,
            group_cols=["chain"],
            selected_years=[2026],
            selected_months=[p("2026-01"), p("2026-02"), p("2026-03")],
        )
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    chain_a_mar = result[
        (result["chain"] == "A") & (result["month_year"] == p("2026-03"))
    ].iloc[0]

    # Chain A:
    # repeat buyers by month = Jan 1, Feb 1, Mar 0
    # existing buyers by month = Jan 1, Feb 1, Mar 1
    # reorder_rate_3m at Mar = (1 + 1 + 0) / (1 + 1 + 1) = 2 / 3
    assert chain_a_mar["reorder_rate_3m"] == pytest.approx(2 / 3)


def test_calculate_reorder_rate_3m_returns_nan_when_existing_buyers_3m_is_zero():
    data = [
        ("A", "A1", "P1", "2026-03", 4, 1, 1, 0),
    ]
    df_full = pd.DataFrame(
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
    df_full["month_year"] = pd.PeriodIndex(df_full["month_year"], freq="M")

    df_filtered = df_full[df_full["month_year"] == p("2026-03")]

    result = (
        calculate_reorder_rate_3m(
            df_filtered=df_filtered,
            df_full=df_full,
            group_cols=["chain"],
            selected_years=[2026],
            selected_months=[p("2026-03")],
        )
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    row = result[(result["chain"] == "A") & (result["month_year"] == p("2026-03"))].iloc[0]
    assert pd.isna(row["reorder_rate_3m"])
import pandas as pd
import pandas.testing as pdt
import pytest

from backend.metrics.metric_growth_rates import (
    add_additive_metric_3m,
    calculate_buying_stores_3m,
    add_prior_month_columns,
    calculate_vpo_3m,
    calculate_reorder_rate_3m,
    add_pct_change_columns,
)


def p(x: str) -> pd.Period:
    return pd.Period(x, freq="M")


def reporting_end():
    return pd.Period(pd.Timestamp.today(), freq="M") - 1


def month_offset(n: int):
    return reporting_end() + n


def month_str(n: int):
    return str(month_offset(n))


# =========================================================
# Fixtures
# =========================================================

def build_monthly_units_gap_df():
    return pd.DataFrame(
        {
            "chain": ["A", "A"],
            "month_year": pd.PeriodIndex(
                [month_str(-2), month_str(0)],
                freq="M",
            ),
            "units": [10, 20],
        }
    )


def build_additive_gap_df():
    return build_monthly_units_gap_df()


def build_additive_no_group_df():
    return pd.DataFrame(
        {
            "month_year": pd.PeriodIndex(
                [month_str(-2), month_str(-1), month_str(0)],
                freq="M",
            ),
            "units": [5, 10, 15],
        }
    )


def build_buying_stores_two_month_df():
    return pd.DataFrame(
        {
            "chain": ["A", "A"],
            "coded_customer": ["A1", "A2"],
            "month_year": pd.PeriodIndex(
                [month_str(-2), month_str(-1)],
                freq="M",
            ),
        }
    )


def build_buying_stores_three_month_df():
    return pd.DataFrame(
        {
            "chain": ["A", "A", "A", "A"],
            "coded_customer": ["A1", "A2", "A1", "A3"],
            "month_year": pd.PeriodIndex(
                [month_str(-2), month_str(-1), month_str(0), month_str(0)],
                freq="M",
            ),
        }
    )


def build_vpo_reorder_integration_df():
    data = [
        ("A", "A1", "P1", month_str(-3), 5, 1, 1, 0),
        ("A", "A1", "P1", month_str(-2), 4, 0, 0, 1),
        ("A", "A1", "P1", month_str(-1), 6, 0, 0, 1),

        # Chain B anchors latest full month
        ("B", "B1", "P2", month_str(0), 1, 1, 1, 0),
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

    assert result.loc[0, "units_l1m_pct"] == pytest.approx(1.0)
    assert result.loc[1, "units_l1m_pct"] == pytest.approx(0.2)
    assert result.loc[0, "units_l3m_pct"] == pytest.approx((125 - 80) / 80)
    assert result.loc[1, "units_l3m_pct"] == pytest.approx((150 - 120) / 120)


def test_add_pct_change_columns_returns_nan_when_prior_zero_but_allows_negative_prior():
    df = pd.DataFrame(
        {
            "units": [100, 120],
            "units_l1m": [0, -5],
        }
    )

    result = add_pct_change_columns(df.copy(), "units", l1m=True)

    assert pd.isna(result.loc[0, "units_l1m_pct"])
    assert result.loc[1, "units_l1m_pct"] == pytest.approx(-25.0)


# =========================================================
# add_additive_metric_3m
# =========================================================

def test_add_additive_metric_3m_fills_missing_middle_month_and_rolls_zero():
    df = build_monthly_units_gap_df()

    result = (
        add_additive_metric_3m(df, ["chain", "month_year"], "units")
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    expected = pd.DataFrame(
        {
            "chain": ["A", "A", "A", "A"],
            "month_year": pd.PeriodIndex(
                [month_str(-2), month_str(-1), month_str(0), month_str(1)],
                freq="M",
            ),
            "units": [10.0, 0.0, 20.0, 0.0],
            "units_3m": [None, None, 30.0, 20.0],
        }
    )

    pdt.assert_frame_equal(result, expected, check_exact=False, rtol=1e-9)


def test_add_additive_metric_3m_fills_missing_middle_month_and_rolls():
    df = build_additive_gap_df()

    result = (
        add_additive_metric_3m(df, ["chain", "month_year"], "units")
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    expected = pd.DataFrame(
        {
            "chain": ["A", "A", "A", "A"],
            "month_year": pd.PeriodIndex(
                [month_str(-2), month_str(-1), month_str(0), month_str(1)],
                freq="M",
            ),
            "units": [10.0, 0.0, 20.0, 0.0],
            "units_3m": [None, None, 30.0, 20.0],
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
            "month_year": pd.PeriodIndex(
                [month_str(-2), month_str(-1), month_str(0), month_str(1)],
                freq="M",
            ),
            "units": [5.0, 10.0, 15.0, 0.0],
            "units_3m": [None, None, 30.0, 25.0],
        }
    )

    pdt.assert_frame_equal(result, expected, check_exact=False, rtol=1e-9)


# =========================================================
# add_prior_month_columns
# =========================================================

def test_add_prior_month_columns_preserves_nan_for_missing_prior_month():
    df = build_monthly_units_gap_df()

    result = (
        add_prior_month_columns(df, ["chain", "month_year"], "units", l1m=True)
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    assert pd.isna(result.loc[0, "units_l1m"])
    assert pd.isna(result.loc[1, "units"])
    assert result.loc[1, "units_l1m"] == 10
    assert pd.isna(result.loc[2, "units_l1m"])


def test_add_prior_month_columns_l1m_preserves_nan_for_missing_prior():
    df = build_additive_gap_df()

    result = (
        add_prior_month_columns(df, ["chain", "month_year"], "units", l1m=True)
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    assert pd.isna(result.loc[0, "units_l1m"])
    assert pd.isna(result.loc[1, "units"])
    assert result.loc[1, "units_l1m"] == 10
    assert pd.isna(result.loc[2, "units_l1m"])


def test_add_prior_month_columns_l3m_uses_metric_3m_shift():
    df = pd.DataFrame(
        {
            "chain": ["A", "A", "A", "A", "A", "A"],
            "month_year": pd.PeriodIndex(
                [
                    str(month_offset(-5)),
                    str(month_offset(-4)),
                    str(month_offset(-3)),
                    str(month_offset(-2)),
                    str(month_offset(-1)),
                    str(month_offset(0)),
                ],
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

    latest_row = result[result["month_year"] == month_offset(0)].iloc[0]
    assert latest_row["units_l3m"] == 60

    first_row = result[result["month_year"] == month_offset(-5)].iloc[0]
    early_row = result[result["month_year"] == month_offset(-2)].iloc[0]

    assert pd.isna(first_row["units_l3m"])
    assert pd.isna(early_row["units_l3m"])


def test_add_prior_month_columns_py_shift():
    start = month_offset(-12)
    months = pd.period_range(start, periods=13, freq="M")

    df = pd.DataFrame(
        {
            "month_year": months,
            "units": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 100],
        }
    )

    result = (
        add_prior_month_columns(df, ["month_year"], "units", py=True)
        .sort_values("month_year")
        .reset_index(drop=True)
    )

    latest = result[result["month_year"] == month_offset(0)].iloc[0]
    assert latest["units_py"] == 1


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
            "chain": ["A", "A", "A", "A"],
            "month_year": pd.PeriodIndex(
                [month_str(-2), month_str(-1), month_str(0), month_str(1)],
                freq="M",
            ),
            "buying_stores_3m": [None, None, 2.0, 1.0],
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

    latest_row = result[result["month_year"] == month_offset(0)].iloc[0]

    assert latest_row["buying_stores_3m"] == 3


# =========================================================
# calculate_vpo_3m
# =========================================================

def test_calculate_vpo_3m_uses_zero_for_missing_latest_month_when_reporting_end_extends():
    df_full = build_vpo_reorder_integration_df()
    df_filtered = df_full[
        (df_full["month_year"] >= month_offset(-2))
        & (df_full["month_year"] <= month_offset(0))
    ]

    result = (
        calculate_vpo_3m(
            df_filtered=df_filtered,
            df_full=df_full,
            group_cols=["chain"],
            selected_years=[reporting_end().year],
            selected_months=[month_offset(-2), month_offset(-1), month_offset(0)],
        )
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    chain_a_latest = result[
        (result["chain"] == "A") & (result["month_year"] == month_offset(0))
    ].iloc[0]

    assert chain_a_latest["vpo_3m"] == pytest.approx(10 / 3 / 4)


# =========================================================
# calculate_reorder_rate_3m
# =========================================================

def test_calculate_reorder_rate_3m_uses_zero_for_missing_latest_month_when_reporting_end_extends():
    df_full = build_vpo_reorder_integration_df()
    df_filtered = df_full[
        (df_full["month_year"] >= month_offset(-2))
        & (df_full["month_year"] <= month_offset(0))
    ]

    result = (
        calculate_reorder_rate_3m(
            df_filtered=df_filtered,
            df_full=df_full,
            group_cols=["chain"],
            selected_years=[reporting_end().year],
            selected_months=[month_offset(-2), month_offset(-1), month_offset(0)],
        )
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    chain_a_latest = result[
        (result["chain"] == "A") & (result["month_year"] == month_offset(0))
    ].iloc[0]

    assert chain_a_latest["reorder_rate_3m"] == pytest.approx(2 / 3)


def test_calculate_reorder_rate_3m_returns_nan_when_existing_buyers_3m_is_zero():
    df_full = pd.DataFrame(
        [
            ("A", "A1", "P1", month_str(0), 4, 1, 1, 0),
        ],
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

    df_filtered = df_full[df_full["month_year"] == month_offset(0)]

    result = (
        calculate_reorder_rate_3m(
            df_filtered=df_filtered,
            df_full=df_full,
            group_cols=["chain"],
            selected_years=[reporting_end().year],
            selected_months=[month_offset(0)],
        )
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    row = result[
        (result["chain"] == "A") & (result["month_year"] == month_offset(0))
    ].iloc[0]

    assert pd.isna(row["reorder_rate_3m"])


def test_debug_additive_3m_spine_months():
    df = pd.DataFrame(
        {
            "chain": ["A", "A"],
            "month_year": pd.PeriodIndex(
                [month_str(-2), month_str(0)],
                freq="M",
            ),
            "units": [10, 20],
        }
    )

    result = (
        add_additive_metric_3m(df, ["chain", "month_year"], "units")
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    assert result["month_year"].tolist() == [
        month_offset(-2),
        month_offset(-1),
        month_offset(0),
        month_offset(1),
    ]
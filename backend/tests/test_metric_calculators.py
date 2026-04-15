import pandas as pd
import pytest

from backend.metrics.metric_calculators import (
    calculate_units,
    calculate_buying_stores,
    calculate_active_pods,
    calculate_vpo,
    calculate_reorder_rate,
)

from backend.metrics.monthly_metric_calculators import (
    grouped_cumsum,
    calculate_monthly_units,
    calculate_monthly_buying_stores,
    calculate_monthly_active_pods,
    calculate_monthly_vpo,
    calculate_monthly_reorder_rate,
)

from backend.metrics.metric_growth_rates import (
    add_additive_metric_3m,
    add_prior_month_columns,
    add_pct_change_columns,
    add_buying_stores_3m,
    add_vpo_3m,
    add_reorder_rate_3m,
)




@pytest.fixture
def sample_df():
    data = [
        # Chain A, Store 1, SKU 1
        {
            "month_year": pd.Period("2024-01", freq="M"),
            "chain": "A",
            "sku": "sku1",
            "coded_customer": "s1",
            "pod_helper": "s1_sku1",
            "units": 10,
            "first_pod_flag": 1,
            "first_store_flag": 1,
            "reorder_flag": 0,
        },
        {
            "month_year": pd.Period("2024-02", freq="M"),
            "chain": "A",
            "sku": "sku1",
            "coded_customer": "s1",
            "pod_helper": "s1_sku1",
            "units": 20,
            "first_pod_flag": 0,
            "first_store_flag": 0,
            "reorder_flag": 1,
        },
        {
            "month_year": pd.Period("2024-03", freq="M"),
            "chain": "A",
            "sku": "sku1",
            "coded_customer": "s1",
            "pod_helper": "s1_sku1",
            "units": 30,
            "first_pod_flag": 0,
            "first_store_flag": 0,
            "reorder_flag": 1,
        },

        # Chain A, Store 2, SKU 1
        {
            "month_year": pd.Period("2024-02", freq="M"),
            "chain": "A",
            "sku": "sku1",
            "coded_customer": "s2",
            "pod_helper": "s2_sku1",
            "units": 5,
            "first_pod_flag": 1,
            "first_store_flag": 1,
            "reorder_flag": 0,
        },
        {
            "month_year": pd.Period("2024-03", freq="M"),
            "chain": "A",
            "sku": "sku1",
            "coded_customer": "s2",
            "pod_helper": "s2_sku1",
            "units": 15,
            "first_pod_flag": 0,
            "first_store_flag": 0,
            "reorder_flag": 1,
        },

        # Chain B, Store 3, SKU 1
        {
            "month_year": pd.Period("2024-01", freq="M"),
            "chain": "B",
            "sku": "sku1",
            "coded_customer": "s3",
            "pod_helper": "s3_sku1",
            "units": 8,
            "first_pod_flag": 1,
            "first_store_flag": 1,
            "reorder_flag": 0,
        },
        {
            "month_year": pd.Period("2024-03", freq="M"),
            "chain": "B",
            "sku": "sku1",
            "coded_customer": "s3",
            "pod_helper": "s3_sku1",
            "units": 12,
            "first_pod_flag": 0,
            "first_store_flag": 0,
            "reorder_flag": 1,
        },
    ]

    return pd.DataFrame(data)


def test_grouped_cumsum_single_series():
    df = pd.DataFrame(
        {
            "month_year": [1, 2, 3],
            "new_pods": [1, 2, 3],
        }
    )

    result = grouped_cumsum(df, "new_pods", ["month_year"])
    assert result.tolist() == [1, 3, 6]


def test_grouped_cumsum_by_chain():
    df = pd.DataFrame(
        {
            "chain": ["A", "A", "B", "B"],
            "month_year": [1, 2, 1, 2],
            "new_pods": [1, 2, 3, 4],
        }
    ).sort_values(["chain", "month_year"]).reset_index(drop=True)

    result = grouped_cumsum(df, "new_pods", ["chain", "month_year"])
    assert result.tolist() == [1, 3, 3, 7]


def test_calculate_units_total_by_chain(sample_df):
    result = calculate_units(sample_df, ["chain"]).sort_values("chain").reset_index(drop=True)

    expected = pd.DataFrame(
        {
            "chain": ["A", "B"],
            "units": [80, 20],
        }
    )

    pd.testing.assert_frame_equal(result, expected)


def test_calculate_monthly_units_by_chain(sample_df):
    result = (
        calculate_monthly_units(sample_df, ["chain"])
        .sort_values(["month_year", "chain"])
        .reset_index(drop=True)
    )

    expected = pd.DataFrame(
        {
            "month_year": [
                pd.Period("2024-01", freq="M"),
                pd.Period("2024-01", freq="M"),
                pd.Period("2024-02", freq="M"),
                pd.Period("2024-03", freq="M"),
                pd.Period("2024-03", freq="M"),
            ],
            "chain": ["A", "B", "A", "A", "B"],
            "units": [10, 8, 25, 45, 12],
        }
    )

    pd.testing.assert_frame_equal(result, expected)


def test_calculate_buying_stores_total_by_chain(sample_df):
    result = calculate_buying_stores(sample_df, ["chain"]).sort_values("chain").reset_index(drop=True)

    expected = pd.DataFrame(
        {
            "chain": ["A", "B"],
            "buying_stores": [2, 1],
        }
    )

    pd.testing.assert_frame_equal(result, expected)


def test_calculate_monthly_buying_stores_by_chain(sample_df):
    result = (
        calculate_monthly_buying_stores(sample_df, ["chain"])
        .sort_values(["month_year", "chain"])
        .reset_index(drop=True)
    )

    expected = pd.DataFrame(
        {
            "month_year": [
                pd.Period("2024-01", freq="M"),
                pd.Period("2024-01", freq="M"),
                pd.Period("2024-02", freq="M"),
                pd.Period("2024-03", freq="M"),
                pd.Period("2024-03", freq="M"),
            ],
            "chain": ["A", "B", "A", "A", "B"],
            "buying_stores": [1, 1, 2, 2, 1],
        }
    )

    pd.testing.assert_frame_equal(result, expected)


def test_calculate_active_pods_total_by_chain(sample_df):
    result = calculate_active_pods(sample_df, ["chain"]).sort_values("chain").reset_index(drop=True)

    expected = pd.DataFrame(
        {
            "chain": ["A", "B"],
            "active_pods": [2, 1],
        }
    )

    pd.testing.assert_frame_equal(result, expected)


def test_calculate_monthly_active_pods_by_chain(sample_df):
    result = (
        calculate_monthly_active_pods(sample_df, ["chain"])
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    expected = pd.DataFrame(
        {
            "chain": ["A", "A", "A", "B", "B"],
            "month_year": [
                pd.Period("2024-01", freq="M"),
                pd.Period("2024-02", freq="M"),
                pd.Period("2024-03", freq="M"),
                pd.Period("2024-01", freq="M"),
                pd.Period("2024-03", freq="M"),
            ],
            "active_pods": [1, 2, 2, 1, 1],
        }
    )

    pd.testing.assert_frame_equal(result, expected)


def test_calculate_monthly_vpo_by_chain(sample_df):
    result = (
        calculate_monthly_vpo(sample_df, ["chain"])
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    expected = pd.DataFrame(
    {
        "month_year": [
            pd.Period("2024-01", freq="M"),
            pd.Period("2024-02", freq="M"),
            pd.Period("2024-03", freq="M"),
            pd.Period("2024-01", freq="M"),
            pd.Period("2024-03", freq="M"),
        ],
        "chain": ["A", "A", "A", "B", "B"],
        "vpo": [10.0, 12.5, 22.5, 8.0, 12.0],
    }
    )

    print(result.columns.tolist())
    print(expected.columns.tolist())

    pd.testing.assert_frame_equal(result, expected)


def test_calculate_vpo_total_by_chain(sample_df):
    result = calculate_vpo(sample_df, ["chain"]).sort_values("chain").reset_index(drop=True)

    expected = pd.DataFrame(
        {
            "chain": ["A", "B"],
            "vpo": [16.0, 10.0],
        }
    )

    pd.testing.assert_frame_equal(result, expected)


def test_calculate_monthly_reorder_rate_by_chain(sample_df):
    result = (
        calculate_monthly_reorder_rate(sample_df, ["chain"])
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    expected = pd.DataFrame(
        {
            "chain": ["A", "A", "A", "B", "B"],
            "month_year": [
                pd.Period("2024-01", freq="M"),
                pd.Period("2024-02", freq="M"),
                pd.Period("2024-03", freq="M"),
                pd.Period("2024-01", freq="M"),
                pd.Period("2024-03", freq="M"),
            ],
            "reorder_rate": [None, 1.0, 1.0, None, 1.0],
        }
    )

    pd.testing.assert_frame_equal(result, expected)


def test_calculate_reorder_rate_total_by_chain(sample_df):
    result = calculate_reorder_rate(sample_df, ["chain"]).sort_values("chain").reset_index(drop=True)

    expected = pd.DataFrame(
        {
            "chain": ["A", "B"],
            "reorder_rate": [1.0, 1.0],
        }
    )

    pd.testing.assert_frame_equal(result, expected)




@pytest.fixture
def monthly_metric_df():
    months = pd.period_range("2024-01", "2025-03", freq="M")
    return pd.DataFrame(
        {
            "month_year": months,
            "units": [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150],
        }
    )


@pytest.fixture
def monthly_metric_by_chain_df():
    months = pd.period_range("2024-01", "2024-06", freq="M")
    rows = []

    a_units = [10, 20, 30, 40, 50, 60]
    b_units = [1, 2, 3, 4, 5, 6]

    for month, a, b in zip(months, a_units, b_units):
        rows.append({"chain": "A", "month_year": month, "units": a})
        rows.append({"chain": "B", "month_year": month, "units": b})

    return pd.DataFrame(rows)


@pytest.fixture
def raw_sales_df():
    data = [
        # Chain A, s1, sku1
        {"month_year": pd.Period("2024-01", freq="M"), "chain": "A", "sku": "sku1", "coded_customer": "s1", "pod_helper": "s1_sku1", "units": 10, "first_pod_flag": 1, "first_store_flag": 1, "reorder_flag": 0},
        {"month_year": pd.Period("2024-02", freq="M"), "chain": "A", "sku": "sku1", "coded_customer": "s1", "pod_helper": "s1_sku1", "units": 20, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        {"month_year": pd.Period("2024-03", freq="M"), "chain": "A", "sku": "sku1", "coded_customer": "s1", "pod_helper": "s1_sku1", "units": 30, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        {"month_year": pd.Period("2024-04", freq="M"), "chain": "A", "sku": "sku1", "coded_customer": "s1", "pod_helper": "s1_sku1", "units": 40, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},

        # Chain A, s2, sku1
        {"month_year": pd.Period("2024-02", freq="M"), "chain": "A", "sku": "sku1", "coded_customer": "s2", "pod_helper": "s2_sku1", "units": 5, "first_pod_flag": 1, "first_store_flag": 1, "reorder_flag": 0},
        {"month_year": pd.Period("2024-03", freq="M"), "chain": "A", "sku": "sku1", "coded_customer": "s2", "pod_helper": "s2_sku1", "units": 15, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        {"month_year": pd.Period("2024-04", freq="M"), "chain": "A", "sku": "sku1", "coded_customer": "s2", "pod_helper": "s2_sku1", "units": 25, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},

        # Chain B, s3, sku1
        {"month_year": pd.Period("2024-01", freq="M"), "chain": "B", "sku": "sku1", "coded_customer": "s3", "pod_helper": "s3_sku1", "units": 8, "first_pod_flag": 1, "first_store_flag": 1, "reorder_flag": 0},
        {"month_year": pd.Period("2024-03", freq="M"), "chain": "B", "sku": "sku1", "coded_customer": "s3", "pod_helper": "s3_sku1", "units": 12, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        {"month_year": pd.Period("2024-04", freq="M"), "chain": "B", "sku": "sku1", "coded_customer": "s3", "pod_helper": "s3_sku1", "units": 20, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
    ]

    return pd.DataFrame(data)


def assert_series_matches_with_nans(actual, expected):
    assert len(actual) == len(expected)

    for a, e in zip(actual, expected):
        if pd.isna(e):
            assert pd.isna(a), f"Expected NaN, got {a}"
        else:
            assert a == pytest.approx(e), f"Expected {e}, got {a}"


def test_add_additive_metric_3m_no_groups(monthly_metric_df):
    result = add_additive_metric_3m(monthly_metric_df, [], "units")

    expected = [None, None, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 360.0, 390.0, 420.0]
    assert_series_matches_with_nans(result["units_3m"].tolist(), expected)


def test_add_additive_metric_3m_by_chain(monthly_metric_by_chain_df):
    result = (
        add_additive_metric_3m(monthly_metric_by_chain_df, ["chain"], "units")
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    a = result[result["chain"] == "A"].reset_index(drop=True)
    b = result[result["chain"] == "B"].reset_index(drop=True)

    assert_series_matches_with_nans(a["units_3m"].tolist(), [None, None, 60.0, 90.0, 120.0, 150.0])
    assert_series_matches_with_nans(b["units_3m"].tolist(), [None, None, 6.0, 9.0, 12.0, 15.0])


def test_add_prior_month_columns(monthly_metric_df):
    result = add_additive_metric_3m(monthly_metric_df, [], "units")
    result = add_prior_month_columns(result, [], "units", l1m=True, l3m=True, py=True)

    assert pd.isna(result.loc[0, "units_l1m"])
    assert result.loc[1, "units_l1m"] == 10
    assert result.loc[14, "units_l1m"] == 140

    assert pd.isna(result.loc[4, "units_l3m"])
    assert result.loc[5, "units_l3m"] == 60.0
    assert result.loc[6, "units_l3m"] == 90.0

    assert pd.isna(result.loc[11, "units_py"])
    assert result.loc[12, "units_py"] == 10
    assert result.loc[13, "units_py"] == 20
    assert result.loc[14, "units_py"] == 30


def test_add_prior_month_columns_by_chain(monthly_metric_by_chain_df):
    result = add_additive_metric_3m(monthly_metric_by_chain_df, ["chain"], "units")
    result = (
        add_prior_month_columns(result, ["chain"], "units", l1m=True, l3m=True)
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    a = result[result["chain"] == "A"].reset_index(drop=True)
    b = result[result["chain"] == "B"].reset_index(drop=True)

    assert pd.isna(a.loc[0, "units_l1m"])
    assert a.loc[1, "units_l1m"] == 10
    assert a.loc[5, "units_l1m"] == 50

    assert pd.isna(b.loc[0, "units_l1m"])
    assert b.loc[1, "units_l1m"] == 1
    assert b.loc[5, "units_l1m"] == 5

    assert pd.isna(a.loc[4, "units_l3m"])
    assert a.loc[5, "units_l3m"] == 60.0

    assert pd.isna(b.loc[4, "units_l3m"])
    assert b.loc[5, "units_l3m"] == 6.0


def test_add_pct_change_columns(monthly_metric_df):
    result = add_additive_metric_3m(monthly_metric_df, [], "units")
    result = add_prior_month_columns(result, [], "units", l1m=True, l3m=True, py=True)
    result = add_pct_change_columns(result, "units", l1m=True, l3m=True, py=True)

    assert pd.isna(result.loc[0, "units_l1m_pct"])
    assert result.loc[1, "units_l1m_pct"] == 1.0
    assert result.loc[2, "units_l1m_pct"] == 0.5

    assert pd.isna(result.loc[4, "units_l3m_pct"])
    assert result.loc[5, "units_l3m_pct"] == 0.0
    assert result.loc[6, "units_l3m_pct"] == (70 - 90.0) / 90.0

    assert pd.isna(result.loc[11, "units_py_pct"])
    assert result.loc[12, "units_py_pct"] == 12.0
    assert result.loc[13, "units_py_pct"] == 6.0
    assert result.loc[14, "units_py_pct"] == 4.0


def test_calculate_buying_stores_3m_no_groups(raw_sales_df):
    result = add_buying_stores_3m(raw_sales_df, []).sort_values("month_year").reset_index(drop=True)

    expected = pd.DataFrame(
        {
            "month_year": [
                pd.Period("2024-03", freq="M"),
                pd.Period("2024-04", freq="M"),
            ],
            "buying_stores_3m": [3, 3],
        }
    )

    pd.testing.assert_frame_equal(result, expected)


def test_calculate_buying_stores_3m_by_chain(raw_sales_df):
    result = (
        add_buying_stores_3m(raw_sales_df, ["chain"])
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    expected = pd.DataFrame(
        {
            "chain": ["A", "A", "B", "B"],
            "buying_stores_3m": [2, 2, 1, 1],
            "month_year": [
                pd.Period("2024-03", freq="M"),
                pd.Period("2024-04", freq="M"),
                pd.Period("2024-03", freq="M"),
                pd.Period("2024-04", freq="M"),
            ],
        }
    )

    pd.testing.assert_frame_equal(result, expected)


def test_add_vpo_3m_by_chain(raw_sales_df):
    monthly = pd.DataFrame(
        {
            "chain": ["A", "A", "A", "A", "B", "B", "B"],
            "month_year": [
                pd.Period("2024-01", freq="M"),
                pd.Period("2024-02", freq="M"),
                pd.Period("2024-03", freq="M"),
                pd.Period("2024-04", freq="M"),
                pd.Period("2024-01", freq="M"),
                pd.Period("2024-03", freq="M"),
                pd.Period("2024-04", freq="M"),
            ],
            "units": [10, 25, 45, 65, 8, 12, 20],
            "active_pods": [1, 2, 2, 2, 1, 1, 1],
        }
    )

    result = (
        add_vpo_3m(monthly, ["chain"])
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    # chain A
    # Mar: units_3m = 10+25+45 = 80 ; active_pods_3m = 1+2+2 = 5 ; /4 => 4.0
    # Apr: units_3m = 25+45+65 = 135 ; active_pods_3m = 2+2+2 = 6 ; /4 => 5.625
    # chain B
    # Mar cannot form 3 rows because Jan, Mar only before Apr in this monthly table structure
    # Apr also only Jan, Mar, Apr rows for B => 8+12+20 = 40 ; 1+1+1 = 3 ; /4 => 3.3333333333333335

    expected = pd.DataFrame(
        {
            "chain": ["A", "A", "A", "A", "B", "B", "B"],
            "month_year": [
                pd.Period("2024-01", freq="M"),
                pd.Period("2024-02", freq="M"),
                pd.Period("2024-03", freq="M"),
                pd.Period("2024-04", freq="M"),
                pd.Period("2024-01", freq="M"),
                pd.Period("2024-03", freq="M"),
                pd.Period("2024-04", freq="M"),
            ],
            "vpo_3m": [None, None, 4.0, 5.625, None, None, 40 / 3 / 4],
        }
    )

    assert result["chain"].tolist() == expected["chain"].tolist()
    assert result["month_year"].tolist() == expected["month_year"].tolist()
    assert_series_matches_with_nans(
        result["vpo_3m"].tolist(),
        expected["vpo_3m"].tolist(),
    )

    


def test_add_reorder_rate_3m_by_chain(raw_sales_df):
    result = (
        add_reorder_rate_3m(raw_sales_df, ["chain"])
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    # Chain A:
    # Jan: no 3m
    # Feb: no 3m
    # Mar:
    #   repeat_buyers by month = [0,1,2] => 3m = 3
    #   existing_buyers by month = [0,1,2] => 3m = 3
    #   rate = 1.0
    # Apr:
    #   repeat_buyers by month = [1,2,2] => 5
    #   existing_buyers by month = [1,2,2] => 5
    #   rate = 1.0
    #
    # Chain B:
    # Jan: no 3m
    # Mar: no 3m
    # Apr:
    # rows are sparse but rolling uses row windows, not calendar-complete months
    # repeat_buyers rows for B = [0,1,1] => Apr 3m = 2 if there are only 3 rows total including Jan/Mar/Apr after agg
    # existing_buyers rows for B = [0,0,1] => Apr 3m = 1
    # rate = 2.0 based on row-wise rolling
    #
    # If you later force complete month scaffolding, this expected value will change.

    expected = pd.DataFrame(
        {
            "chain": ["A", "A", "A", "A", "B", "B", "B"],
            "month_year": [
                pd.Period("2024-01", freq="M"),
                pd.Period("2024-02", freq="M"),
                pd.Period("2024-03", freq="M"),
                pd.Period("2024-04", freq="M"),
                pd.Period("2024-01", freq="M"),
                pd.Period("2024-03", freq="M"),
                pd.Period("2024-04", freq="M"),
            ],
            "reorder_rate_3m": [None, None, 1.0, 1.0, None, None, 1.0],
        }
    )

    assert result["chain"].tolist() == expected["chain"].tolist()
    assert result["month_year"].tolist() == expected["month_year"].tolist()
    assert_series_matches_with_nans(
        result["reorder_rate_3m"].tolist(),
        expected["reorder_rate_3m"].tolist(),
    )
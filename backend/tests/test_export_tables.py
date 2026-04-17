import pandas as pd
import pytest
from unittest.mock import patch
from datetime import datetime

# export layer (integration targets)
from backend.exports.ai_ready.export_tables import (
    export_monthly_summary,
    export_summary_by_grain,
    export_store_level_table,
)

# metric helpers used directly in tests
from backend.metrics.metric_growth_rates import (
    add_additive_metric_3m,
    add_prior_month_columns,
    add_pct_change_columns,
)

from backend.metrics.metric_growth_rates import calculate_reorder_rate_3m


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────

def assert_value(actual, expected, tol=1e-9):
    if pd.isna(expected):
        assert pd.isna(actual), f"Expected NaN, got {actual}"
    elif isinstance(expected, float):
        assert actual == pytest.approx(expected, rel=tol, abs=tol), f"Expected {expected}, got {actual}"
    else:
        assert actual == expected, f"Expected {expected}, got {actual}"


MOCK_TODAY = datetime(2024, 8, 1)
DATETIME_PATH = "backend.metrics.metric_helpers.datetime"


# ─────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────

@pytest.fixture
def sample_monthly_summary_df():
    data = [
        # JAN
        {"month_year": pd.Period("2024-01", freq="M"), "coded_customer": "s1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 10, "revenue": 100, "first_pod_flag": 1, "first_store_flag": 1, "reorder_flag": 0},
        # FEB
        {"month_year": pd.Period("2024-02", freq="M"), "coded_customer": "s1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 20, "revenue": 200, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        {"month_year": pd.Period("2024-02", freq="M"), "coded_customer": "s2", "sku": "skuA", "pod_helper": "s2_skuA", "units": 5, "revenue": 50, "first_pod_flag": 1, "first_store_flag": 1, "reorder_flag": 0},
        # MAR
        {"month_year": pd.Period("2024-03", freq="M"), "coded_customer": "s1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 30, "revenue": 300, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        {"month_year": pd.Period("2024-03", freq="M"), "coded_customer": "s2", "sku": "skuA", "pod_helper": "s2_skuA", "units": 15, "revenue": 150, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        {"month_year": pd.Period("2024-03", freq="M"), "coded_customer": "s1", "sku": "skuB", "pod_helper": "s1_skuB", "units": 7, "revenue": 70, "first_pod_flag": 1, "first_store_flag": 0, "reorder_flag": 0},
        # APR
        {"month_year": pd.Period("2024-04", freq="M"), "coded_customer": "s1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 40, "revenue": 400, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        {"month_year": pd.Period("2024-04", freq="M"), "coded_customer": "s2", "sku": "skuA", "pod_helper": "s2_skuA", "units": 25, "revenue": 250, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        {"month_year": pd.Period("2024-04", freq="M"), "coded_customer": "s1", "sku": "skuB", "pod_helper": "s1_skuB", "units": 14, "revenue": 140, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        {"month_year": pd.Period("2024-04", freq="M"), "coded_customer": "s3", "sku": "skuA", "pod_helper": "s3_skuA", "units": 9, "revenue": 90, "first_pod_flag": 1, "first_store_flag": 1, "reorder_flag": 0},
        # MAY
        {"month_year": pd.Period("2024-05", freq="M"), "coded_customer": "s1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 50, "revenue": 500, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        {"month_year": pd.Period("2024-05", freq="M"), "coded_customer": "s1", "sku": "skuB", "pod_helper": "s1_skuB", "units": 21, "revenue": 210, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        {"month_year": pd.Period("2024-05", freq="M"), "coded_customer": "s3", "sku": "skuA", "pod_helper": "s3_skuA", "units": 18, "revenue": 180, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        # JUN
        {"month_year": pd.Period("2024-06", freq="M"), "coded_customer": "s1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 60, "revenue": 600, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        {"month_year": pd.Period("2024-06", freq="M"), "coded_customer": "s2", "sku": "skuA", "pod_helper": "s2_skuA", "units": 13, "revenue": 130, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        {"month_year": pd.Period("2024-06", freq="M"), "coded_customer": "s1", "sku": "skuB", "pod_helper": "s1_skuB", "units": 28, "revenue": 280, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        {"month_year": pd.Period("2024-06", freq="M"), "coded_customer": "s3", "sku": "skuA", "pod_helper": "s3_skuA", "units": 27, "revenue": 270, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        # JUL
        {"month_year": pd.Period("2024-07", freq="M"), "coded_customer": "s1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 70, "revenue": 700, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        {"month_year": pd.Period("2024-07", freq="M"), "coded_customer": "s2", "sku": "skuA", "pod_helper": "s2_skuA", "units": 17, "revenue": 170, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        {"month_year": pd.Period("2024-07", freq="M"), "coded_customer": "s1", "sku": "skuB", "pod_helper": "s1_skuB", "units": 35, "revenue": 350, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        {"month_year": pd.Period("2024-07", freq="M"), "coded_customer": "s3", "sku": "skuA", "pod_helper": "s3_skuA", "units": 33, "revenue": 330, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
    ]
    return pd.DataFrame(data)


@pytest.fixture
def sample_export_df():
    data = [
        # CHAIN A / STORE 1
        {"month_year": pd.Period("2024-01", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 10, "revenue": 100, "first_pod_flag": 1, "first_store_flag": 1, "reorder_flag": 0, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-02", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 20, "revenue": 200, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-03", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 30, "revenue": 300, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-04", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 40, "revenue": 400, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-05", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 50, "revenue": 500, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-06", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 60, "revenue": 600, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        # extra sku for store 1
        {"month_year": pd.Period("2024-03", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuB", "pod_helper": "s1_skuB", "units": 7, "revenue": 70, "first_pod_flag": 1, "first_store_flag": 0, "reorder_flag": 0, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-04", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuB", "pod_helper": "s1_skuB", "units": 14, "revenue": 140, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-05", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuB", "pod_helper": "s1_skuB", "units": 21, "revenue": 210, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-06", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuB", "pod_helper": "s1_skuB", "units": 28, "revenue": 280, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        # CHAIN A / STORE 2
        {"month_year": pd.Period("2024-02", freq="M"), "coded_customer": "s2", "chain": "A", "city": "Orlando", "state": "FL", "zip": "32801", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s2_skuA", "units": 5, "revenue": 50, "first_pod_flag": 1, "first_store_flag": 1, "reorder_flag": 0, "status": "Healthy", "first_month_purchased": pd.Period("2024-02", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-03", freq="M"), "coded_customer": "s2", "chain": "A", "city": "Orlando", "state": "FL", "zip": "32801", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s2_skuA", "units": 15, "revenue": 150, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-02", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-04", freq="M"), "coded_customer": "s2", "chain": "A", "city": "Orlando", "state": "FL", "zip": "32801", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s2_skuA", "units": 25, "revenue": 250, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-02", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-06", freq="M"), "coded_customer": "s2", "chain": "A", "city": "Orlando", "state": "FL", "zip": "32801", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s2_skuA", "units": 13, "revenue": 130, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-02", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        # CHAIN B / STORE 3
        {"month_year": pd.Period("2024-01", freq="M"), "coded_customer": "s3", "chain": "B", "city": "Tampa", "state": "FL", "zip": "33601", "channel": "Mass", "distributor": "KeHE", "dc": "DC2", "sku": "skuA", "pod_helper": "s3_skuA", "units": 8, "revenue": 80, "first_pod_flag": 1, "first_store_flag": 1, "reorder_flag": 0, "status": "Struggling", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-03", freq="M"), "coded_customer": "s3", "chain": "B", "city": "Tampa", "state": "FL", "zip": "33601", "channel": "Mass", "distributor": "KeHE", "dc": "DC2", "sku": "skuA", "pod_helper": "s3_skuA", "units": 12, "revenue": 120, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Struggling", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-04", freq="M"), "coded_customer": "s3", "chain": "B", "city": "Tampa", "state": "FL", "zip": "33601", "channel": "Mass", "distributor": "KeHE", "dc": "DC2", "sku": "skuA", "pod_helper": "s3_skuA", "units": 20, "revenue": 200, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Struggling", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-05", freq="M"), "coded_customer": "s3", "chain": "B", "city": "Tampa", "state": "FL", "zip": "33601", "channel": "Mass", "distributor": "KeHE", "dc": "DC2", "sku": "skuA", "pod_helper": "s3_skuA", "units": 18, "revenue": 180, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Struggling", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-06", freq="M"), "coded_customer": "s3", "chain": "B", "city": "Tampa", "state": "FL", "zip": "33601", "channel": "Mass", "distributor": "KeHE", "dc": "DC2", "sku": "skuA", "pod_helper": "s3_skuA", "units": 27, "revenue": 270, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Struggling", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
    ]
    return pd.DataFrame(data)


# ─────────────────────────────────────────
# Tests
# ─────────────────────────────────────────

def test_monthly_summary_full_output(sample_monthly_summary_df):
    with patch(DATETIME_PATH) as mock_dt:
        mock_dt.today.return_value = MOCK_TODAY

        result = (
            export_monthly_summary(sample_monthly_summary_df)
            .sort_values("month_year")
            .reset_index(drop=True)
        )

    expected_cols = [
        "month_year", "revenue", "units", "new_pods", "active_pods",
        "buying_stores", "vpo", "reorder_rate", "average_skus_per_store",
        "revenue_3m", "units_3m", "new_pods_3m", "buying_stores_3m",
        "vpo_3m", "reorder_rate_3m",
        "revenue_l3m_pct", "units_l3m_pct", "new_pods_l3m_pct",
        "buying_stores_l3m_pct", "vpo_l3m_pct", "reorder_rate_l3m_pct",
    ]
    assert list(result.columns) == expected_cols

    assert len(result) == 7

    assert result["revenue"].tolist() == [100, 250, 520, 880, 890, 1280, 1550]
    assert result["units"].tolist() == [10, 25, 52, 88, 89, 128, 155]
    assert result["new_pods"].tolist() == [1, 1, 1, 1, 0, 0, 0]
    assert result["buying_stores"].tolist() == [1, 2, 2, 3, 2, 3, 3]
    assert result["active_pods"].tolist() == [1, 2, 3, 4, 4, 4, 4]

    # vpo monthly
    expected_vpo = [10/1/4, 25/2/4, 52/3/4, 88/4/4, 89/4/4, 128/4/4, 155/4/4]
    for i, ev in enumerate(expected_vpo):
        assert_value(result["vpo"].iloc[i], ev)

    # reorder_rate monthly
    expected_rr = [None, 1.0, 1.0, 1.0, 2/3, 1.0, 1.0]
    for i, ev in enumerate(expected_rr):
        assert_value(result["reorder_rate"].iloc[i], ev if ev is None else float(ev))

    # avg skus / store
    expected_skus = [1.0, 1.0, 1.5, 4/3, 1.5, 4/3, 4/3]
    for i, ev in enumerate(expected_skus):
        assert_value(result["average_skus_per_store"].iloc[i], ev)

    # 3m additive
    assert pd.isna(result["revenue_3m"].iloc[0])
    assert pd.isna(result["revenue_3m"].iloc[1])
    assert_value(result["revenue_3m"].iloc[2], 870)
    assert_value(result["revenue_3m"].iloc[3], 1650)
    assert_value(result["revenue_3m"].iloc[4], 2290)
    assert_value(result["revenue_3m"].iloc[5], 3050)
    assert_value(result["revenue_3m"].iloc[6], 3720)

    assert_value(result["units_3m"].iloc[2], 87)
    assert_value(result["units_3m"].iloc[3], 165)
    assert_value(result["units_3m"].iloc[4], 229)
    assert_value(result["units_3m"].iloc[5], 305)
    assert_value(result["units_3m"].iloc[6], 372)

    assert_value(result["new_pods_3m"].iloc[2], 3)
    assert_value(result["new_pods_3m"].iloc[3], 3)
    assert_value(result["new_pods_3m"].iloc[4], 2)
    assert_value(result["new_pods_3m"].iloc[5], 1)
    assert_value(result["new_pods_3m"].iloc[6], 0)

    assert_value(result["buying_stores_3m"].iloc[2], 2)
    assert_value(result["buying_stores_3m"].iloc[3], 3)
    assert_value(result["buying_stores_3m"].iloc[4], 3)
    assert_value(result["buying_stores_3m"].iloc[5], 3)
    assert_value(result["buying_stores_3m"].iloc[6], 3)

    # 3m ratios
    assert pd.isna(result["vpo_3m"].iloc[0])
    assert pd.isna(result["vpo_3m"].iloc[1])
    assert_value(result["vpo_3m"].iloc[2], 87/6/4)
    assert_value(result["vpo_3m"].iloc[3], 165/9/4)
    assert_value(result["vpo_3m"].iloc[4], 229/11/4)
    assert_value(result["vpo_3m"].iloc[5], 305/12/4)
    assert_value(result["vpo_3m"].iloc[6], 372/12/4)

    assert pd.isna(result["reorder_rate_3m"].iloc[0])
    assert pd.isna(result["reorder_rate_3m"].iloc[1])
    assert_value(result["reorder_rate_3m"].iloc[2], 1.0)
    assert_value(result["reorder_rate_3m"].iloc[3], 1.0)
    assert_value(result["reorder_rate_3m"].iloc[4], 6/7)
    assert_value(result["reorder_rate_3m"].iloc[5], 7/8)
    assert_value(result["reorder_rate_3m"].iloc[6], 8/9)

    # l3m pct = current 3m vs prior 3m
    for col in [
        "revenue_l3m_pct", "units_l3m_pct", "new_pods_l3m_pct",
        "buying_stores_l3m_pct", "vpo_l3m_pct", "reorder_rate_l3m_pct"
    ]:
        for i in range(5):
            assert pd.isna(result[col].iloc[i]), f"{col} row {i} should be NaN"

    assert_value(result["revenue_l3m_pct"].iloc[5], (3050 - 870) / 870)
    assert_value(result["revenue_l3m_pct"].iloc[6], (3720 - 1650) / 1650)

    assert_value(result["units_l3m_pct"].iloc[5], (305 - 87) / 87)
    assert_value(result["units_l3m_pct"].iloc[6], (372 - 165) / 165)

    assert_value(result["new_pods_l3m_pct"].iloc[5], (1 - 3) / 3)
    assert_value(result["new_pods_l3m_pct"].iloc[6], (0 - 3) / 3)

    assert_value(result["buying_stores_l3m_pct"].iloc[5], (3 - 2) / 2)
    assert_value(result["buying_stores_l3m_pct"].iloc[6], (3 - 3) / 3)

    assert_value(result["vpo_l3m_pct"].iloc[5], ((305/12/4) - (87/6/4)) / (87/6/4))
    assert_value(result["vpo_l3m_pct"].iloc[6], ((372/12/4) - (165/9/4)) / (165/9/4))

    assert_value(result["reorder_rate_l3m_pct"].iloc[5], ((7/8) - 1.0) / 1.0)
    assert_value(result["reorder_rate_l3m_pct"].iloc[6], ((8/9) - 1.0) / 1.0)


def test_export_summary_by_grain_chain(sample_export_df):
    with patch(DATETIME_PATH) as mock_dt:
        mock_dt.today.return_value = MOCK_TODAY

        result = (
            export_summary_by_grain(sample_export_df, ["chain"])
            .sort_values("chain")
            .reset_index(drop=True)
        )

    expected_cols = [
        "chain", "revenue", "units", "new_pods", "active_pods", "buying_stores",
        "vpo", "reorder_rate", "average_skus_per_store",
        "revenue_3m", "units_3m", "new_pods_3m", "buying_stores_3m",
        "vpo_3m", "reorder_rate_3m",
        "revenue_l3m_pct", "units_l3m_pct", "new_pods_l3m_pct",
        "buying_stores_l3m_pct", "vpo_l3m_pct", "reorder_rate_l3m_pct",
    ]
    assert list(result.columns) == expected_cols
    assert result["chain"].tolist() == ["A", "B"]

    row_a = result[result["chain"] == "A"].iloc[0]
    row_b = result[result["chain"] == "B"].iloc[0]

    # Chain A base metrics
    assert_value(row_a["revenue"], 3380)
    assert_value(row_a["units"], 338)
    assert_value(row_a["new_pods"], 3)
    assert_value(row_a["active_pods"], 3)
    assert_value(row_a["buying_stores"], 2)
    assert_value(row_a["average_skus_per_store"], 1.5)
    assert_value(row_a["vpo"], 338 / 18 / 4)
    assert_value(row_a["reorder_rate"], 8 / 11)

    # Chain A latest row is Jul, so 3m = May+Jun+Jul
    assert_value(row_a["revenue_3m"], 1720)
    assert_value(row_a["units_3m"], 172)
    assert_value(row_a["new_pods_3m"], 0)
    assert_value(row_a["buying_stores_3m"], 2)
    assert_value(row_a["vpo_3m"], 172 / 9 / 4)
    assert_value(row_a["reorder_rate_3m"], 3 / 6)

    # Chain A l3m pct compares Jul-window vs Apr-window
    assert_value(row_a["revenue_l3m_pct"], (1720 - 1560) / 1560)
    assert_value(row_a["units_l3m_pct"], (172 - 156) / 156)
    assert_value(row_a["new_pods_l3m_pct"], (0 - 1) / 1)
    assert_value(row_a["buying_stores_l3m_pct"], (2 - 2) / 2)
    assert_value(row_a["vpo_l3m_pct"], ((172/9/4) - (156/8/4)) / (156/8/4))
    assert_value(row_a["reorder_rate_l3m_pct"], ((3/6) - (5/5)) / (5/5))

    # Chain B base metrics
    assert_value(row_b["revenue"], 850)
    assert_value(row_b["units"], 85)
    assert_value(row_b["new_pods"], 1)
    assert_value(row_b["active_pods"], 1)
    assert_value(row_b["buying_stores"], 1)
    assert_value(row_b["average_skus_per_store"], 1.0)
    assert_value(row_b["vpo"], 85 / 7 / 4)
    assert_value(row_b["reorder_rate"], 4 / 6)

    # Chain B latest row is Jul, so 3m = May+Jun+Jul
    assert_value(row_b["revenue_3m"], 450)
    assert_value(row_b["units_3m"], 45)
    assert_value(row_b["new_pods_3m"], 0)
    assert_value(row_b["buying_stores_3m"], 1)
    assert_value(row_b["vpo_3m"], 45 / 3 / 4)
    assert_value(row_b["reorder_rate_3m"], 2 / 3)

    # Chain B l3m pct compares Jul-window vs Apr-window
    assert_value(row_b["revenue_l3m_pct"], (450 - 320) / 320)
    assert_value(row_b["units_l3m_pct"], (45 - 32) / 32)
    assert pd.isna(row_b["new_pods_l3m_pct"])
    assert_value(row_b["buying_stores_l3m_pct"], (1 - 1) / 1)
    assert_value(row_b["vpo_l3m_pct"], ((45/3/4) - (32/3/4)) / (32/3/4))
    assert_value(row_b["reorder_rate_l3m_pct"], ((2/3) - (3/3)) / (3/3))


def test_export_store_level_table_basic(sample_export_df):
    with patch(DATETIME_PATH) as mock_dt:
        mock_dt.today.return_value = MOCK_TODAY

        result = (
            export_store_level_table(sample_export_df, [])
            .sort_values("coded_customer")
            .reset_index(drop=True)
        )

    expected_cols = [
        "coded_customer", "chain", "city", "state", "zip", "channel",
        "distributor", "dc", "revenue", "units", "vpo",
        "first_month_purchased", "last_month_purchased", "status",
        "skus_carrying", "reorders",
        "revenue_3m", "units_3m", "vpo_3m",
        "revenue_l3m_pct", "units_l3m_pct", "vpo_l3m_pct",
    ]
    assert list(result.columns) == expected_cols
    assert result["coded_customer"].tolist() == ["s1", "s2", "s3"]

    row1 = result[result["coded_customer"] == "s1"].iloc[0]
    row2 = result[result["coded_customer"] == "s2"].iloc[0]
    row3 = result[result["coded_customer"] == "s3"].iloc[0]

    # s1
    assert_value(row1["revenue"], 2800)
    assert_value(row1["units"], 280)
    assert_value(row1["reorders"], 5)
    assert_value(row1["vpo"], 280 / 12 / 4)

    # latest row is Jul, so 3m = May+Jun+Jul
    assert_value(row1["revenue_3m"], 1590)
    assert_value(row1["units_3m"], 159)
    assert_value(row1["vpo_3m"], 159 / 6 / 4)

    # l3m pct compares Jul-window vs Apr-window
    assert_value(row1["revenue_l3m_pct"], (1590 - 1110) / 1110)
    assert_value(row1["units_l3m_pct"], (159 - 111) / 111)
    assert_value(row1["vpo_l3m_pct"], ((159/6/4) - (111/5/4)) / (111/5/4))

    # s2
    assert_value(row2["revenue"], 580)
    assert_value(row2["units"], 58)
    assert_value(row2["reorders"], 3)
    assert_value(row2["vpo"], 58 / 6 / 4)

    assert_value(row2["revenue_3m"], 130)
    assert_value(row2["units_3m"], 13)
    assert_value(row2["vpo_3m"], 13 / 3 / 4)

    assert_value(row2["revenue_l3m_pct"], (130 - 450) / 450)
    assert_value(row2["units_l3m_pct"], (13 - 45) / 45)
    assert_value(row2["vpo_l3m_pct"], ((13/3/4) - (45/3/4)) / (45/3/4))

    # s3
    assert_value(row3["revenue"], 850)
    assert_value(row3["units"], 85)
    assert_value(row3["reorders"], 4)
    assert_value(row3["vpo"], 85 / 7 / 4)

    assert_value(row3["revenue_3m"], 450)
    assert_value(row3["units_3m"], 45)
    assert_value(row3["vpo_3m"], 45 / 3 / 4)

    assert_value(row3["revenue_l3m_pct"], (450 - 320) / 320)
    assert_value(row3["units_l3m_pct"], (45 - 32) / 32)
    assert_value(row3["vpo_l3m_pct"], ((45/3/4) - (32/3/4)) / (32/3/4))





def assert_value(actual, expected, tol=1e-9):
    if pd.isna(expected):
        assert pd.isna(actual), f"Expected NaN, got {actual}"
    elif isinstance(expected, float):
        assert actual == pytest.approx(expected, rel=tol, abs=tol), f"Expected {expected}, got {actual}"
    else:
        assert actual == expected, f"Expected {expected}, got {actual}"


DATETIME_PATH = "backend.metrics.metric_helpers.datetime"


# ─────────────────────────────────────────────────────────────────────────────
# Fixture: store that ordered only once (no reorders ever)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def single_order_df():
    return pd.DataFrame([
        {
            "month_year": pd.Period("2024-03", freq="M"),
            "coded_customer": "s1",
            "chain": "A",
            "city": "Miami",
            "state": "FL",
            "zip": "33101",
            "channel": "Natural",
            "distributor": "UNFI",
            "dc": "DC1",
            "sku": "skuA",
            "pod_helper": "s1_skuA",
            "units": 20,
            "revenue": 200,
            "first_pod_flag": 1,
            "first_store_flag": 1,
            "reorder_flag": 0,
            "status": "Healthy",
            "first_month_purchased": pd.Period("2024-03", freq="M"),
            "last_month_purchased": pd.Period("2024-03", freq="M"),
        },
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Fixture: store that drops off completely mid-period
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def dropoff_df():
    return pd.DataFrame([
        # s1: orders Jan, Feb, Mar then stops
        {"month_year": pd.Period("2024-01", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 10, "revenue": 100, "first_pod_flag": 1, "first_store_flag": 1, "reorder_flag": 0, "status": "Churned", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-03", freq="M")},
        {"month_year": pd.Period("2024-02", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 15, "revenue": 150, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Churned", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-03", freq="M")},
        {"month_year": pd.Period("2024-03", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 20, "revenue": 200, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Churned", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-03", freq="M")},
        # s2: orders Jan-Jun consistently
        {"month_year": pd.Period("2024-01", freq="M"), "coded_customer": "s2", "chain": "A", "city": "Orlando", "state": "FL", "zip": "32801", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s2_skuA", "units": 10, "revenue": 100, "first_pod_flag": 1, "first_store_flag": 1, "reorder_flag": 0, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-02", freq="M"), "coded_customer": "s2", "chain": "A", "city": "Orlando", "state": "FL", "zip": "32801", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s2_skuA", "units": 10, "revenue": 100, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-03", freq="M"), "coded_customer": "s2", "chain": "A", "city": "Orlando", "state": "FL", "zip": "32801", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s2_skuA", "units": 10, "revenue": 100, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-04", freq="M"), "coded_customer": "s2", "chain": "A", "city": "Orlando", "state": "FL", "zip": "32801", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s2_skuA", "units": 10, "revenue": 100, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-05", freq="M"), "coded_customer": "s2", "chain": "A", "city": "Orlando", "state": "FL", "zip": "32801", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s2_skuA", "units": 10, "revenue": 100, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-06", freq="M"), "coded_customer": "s2", "chain": "A", "city": "Orlando", "state": "FL", "zip": "32801", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s2_skuA", "units": 10, "revenue": 100, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Fixture: multi-grain (chain + channel)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def multi_grain_df():
    return pd.DataFrame([
        {"month_year": pd.Period("2024-01", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 10, "revenue": 100, "first_pod_flag": 1, "first_store_flag": 1, "reorder_flag": 0, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-02", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 10, "revenue": 100, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-03", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 10, "revenue": 100, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-04", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 10, "revenue": 100, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-05", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 10, "revenue": 100, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-06", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 10, "revenue": 100, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-03", freq="M"), "coded_customer": "s2", "chain": "B", "city": "Tampa", "state": "FL", "zip": "33601", "channel": "Mass", "distributor": "KeHE", "dc": "DC2", "sku": "skuA", "pod_helper": "s2_skuA", "units": 20, "revenue": 200, "first_pod_flag": 1, "first_store_flag": 1, "reorder_flag": 0, "status": "Healthy", "first_month_purchased": pd.Period("2024-03", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-04", freq="M"), "coded_customer": "s2", "chain": "B", "city": "Tampa", "state": "FL", "zip": "33601", "channel": "Mass", "distributor": "KeHE", "dc": "DC2", "sku": "skuA", "pod_helper": "s2_skuA", "units": 20, "revenue": 200, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-03", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-05", freq="M"), "coded_customer": "s2", "chain": "B", "city": "Tampa", "state": "FL", "zip": "33601", "channel": "Mass", "distributor": "KeHE", "dc": "DC2", "sku": "skuA", "pod_helper": "s2_skuA", "units": 20, "revenue": 200, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-03", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-06", freq="M"), "coded_customer": "s2", "chain": "B", "city": "Tampa", "state": "FL", "zip": "33601", "channel": "Mass", "distributor": "KeHE", "dc": "DC2", "sku": "skuA", "pod_helper": "s2_skuA", "units": 20, "revenue": 200, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-03", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
    ])


def test_single_order_store(single_order_df):
    with patch(DATETIME_PATH) as mock_dt:
        mock_dt.today.return_value = datetime(2024, 8, 1)

        summary = export_summary_by_grain(single_order_df, ["chain"])
        store = export_store_level_table(single_order_df, [])

    row = summary[summary["chain"] == "A"].iloc[0]

    assert_value(row["revenue"], 200)
    assert_value(row["units"], 20)
    assert_value(row["new_pods"], 1)
    assert_value(row["active_pods"], 1)
    assert_value(row["buying_stores"], 1)

    # spine Mar-Jul = 5 months
    assert_value(row["vpo"], 20 / 5 / 4)
    assert_value(row["reorder_rate"], 0.0)

    # 3m exists by Jul because spine has 5 rows; current window = May+Jun+Jul
    assert_value(row["revenue_3m"], 0)
    assert_value(row["units_3m"], 0)
    assert_value(row["new_pods_3m"], 0)
    assert_value(row["buying_stores_3m"], 0)
    assert_value(row["vpo_3m"], 0.0)

    # fewer than 6 rows -> l3m_pct should be NaN
    assert pd.isna(row["revenue_l3m_pct"])
    assert pd.isna(row["units_l3m_pct"])
    assert pd.isna(row["vpo_l3m_pct"])

    # reorder_rate_3m should be 0 if existing buyers > 0 but repeats = 0
    assert pd.isna(row["reorder_rate_3m"])

    store_row = store[store["coded_customer"] == "s1"].iloc[0]
    assert_value(store_row["reorders"], 0)
    assert_value(store_row["vpo"], 20 / 5 / 4)
    assert_value(store_row["revenue_3m"], 0)
    assert_value(store_row["units_3m"], 0)
    assert_value(store_row["vpo_3m"], 0.0)
    assert pd.isna(store_row["revenue_l3m_pct"])
    assert pd.isna(store_row["units_l3m_pct"])
    assert pd.isna(store_row["vpo_l3m_pct"])


def test_dropoff_store(dropoff_df):
    with patch(DATETIME_PATH) as mock_dt:
        mock_dt.today.return_value = datetime(2024, 8, 1)

        store = (
            export_store_level_table(dropoff_df, [])
            .sort_values("coded_customer")
            .reset_index(drop=True)
        )
        grain = (
            export_summary_by_grain(dropoff_df, ["chain"])
            .sort_values("chain")
            .reset_index(drop=True)
        )

    s1 = store[store["coded_customer"] == "s1"].iloc[0]
    s2 = store[store["coded_customer"] == "s2"].iloc[0]

    assert_value(s1["revenue"], 450)
    assert_value(s1["units"], 45)
    assert_value(s1["reorders"], 2)
    assert_value(s1["vpo"], 45 / 7 / 4)
    assert_value(s1["revenue_3m"], 0)
    assert_value(s1["units_3m"], 0)
    assert_value(s1["vpo_3m"], 0.0)
    assert_value(s1["revenue_l3m_pct"], (0 - 350) / 350)
    assert_value(s1["units_l3m_pct"], (0 - 35) / 35)
    assert_value(s1["vpo_l3m_pct"], (0 - (35/3/4)) / (35/3/4))

    assert_value(s2["revenue"], 600)
    assert_value(s2["units"], 60)
    assert_value(s2["reorders"], 5)
    assert_value(s2["vpo"], 60 / 7 / 4)
    assert_value(s2["revenue_3m"], 200)
    assert_value(s2["units_3m"], 20)
    assert_value(s2["vpo_3m"], 20 / 3 / 4)
    assert_value(s2["revenue_l3m_pct"], (200 - 300) / 300)
    assert_value(s2["units_l3m_pct"], (20 - 30) / 30)
    assert_value(s2["vpo_l3m_pct"], ((20/3/4) - (30/3/4)) / (30/3/4))

    row_a = grain[grain["chain"] == "A"].iloc[0]

    assert_value(row_a["revenue"], 1050)
    assert_value(row_a["units"], 105)
    assert_value(row_a["new_pods"], 2)
    assert_value(row_a["active_pods"], 2)
    assert_value(row_a["buying_stores"], 2)
    assert_value(row_a["vpo"], 105 / 14 / 4)
    assert_value(row_a["reorder_rate"], 7 / 12)

    assert_value(row_a["revenue_3m"], 200)
    assert_value(row_a["units_3m"], 20)
    assert_value(row_a["vpo_3m"], 20 / 6 / 4)
    assert_value(row_a["revenue_l3m_pct"], (200 - 650) / 650)
    assert_value(row_a["units_l3m_pct"], (20 - 65) / 65)

    assert s1["vpo"] > 0
    assert s2["vpo"] > 0
    assert_value(s1["revenue_3m"], 0)
    assert_value(s1["revenue_l3m_pct"], -1.0)
    assert s2["revenue_3m"] > 0
    assert s2["vpo_3m"] > 0


def test_multi_grain_chain_channel(multi_grain_df):
    with patch(DATETIME_PATH) as mock_dt:
        mock_dt.today.return_value = datetime(2024, 8, 1)

        result = (
            export_summary_by_grain(multi_grain_df, ["chain", "channel"])
            .sort_values(["chain", "channel"])
            .reset_index(drop=True)
        )

    assert set(result.columns[:2]) == {"chain", "channel"}
    assert len(result) == 2

    row_a = result[(result["chain"] == "A") & (result["channel"] == "Natural")].iloc[0]
    row_b = result[(result["chain"] == "B") & (result["channel"] == "Mass")].iloc[0]

    assert_value(row_a["revenue"], 600)
    assert_value(row_a["units"], 60)
    assert_value(row_a["new_pods"], 1)
    assert_value(row_a["active_pods"], 1)
    assert_value(row_a["buying_stores"], 1)
    assert_value(row_a["vpo"], 60 / 7 / 4)
    assert_value(row_a["reorder_rate"], 5 / 6)
    assert_value(row_a["revenue_3m"], 200)
    assert_value(row_a["units_3m"], 20)
    assert_value(row_a["vpo_3m"], 20 / 3 / 4)
    assert_value(row_a["revenue_l3m_pct"], (200 - 300) / 300)
    assert_value(row_a["units_l3m_pct"], (20 - 30) / 30)
    assert_value(row_a["vpo_l3m_pct"], ((20/3/4) - (30/3/4)) / (30/3/4))

    assert_value(row_b["revenue"], 800)
    assert_value(row_b["units"], 80)
    assert_value(row_b["new_pods"], 1)
    assert_value(row_b["active_pods"], 1)
    assert_value(row_b["buying_stores"], 1)
    assert_value(row_b["vpo"], 80 / 5 / 4)
    assert_value(row_b["reorder_rate"], 3 / 4)
    assert_value(row_b["revenue_3m"], 400)
    assert_value(row_b["units_3m"], 40)
    assert_value(row_b["vpo_3m"], 40 / 3 / 4)

    # only 5 rows in spine (Mar-Jul), so l3m_pct should be NaN
    assert pd.isna(row_b["revenue_l3m_pct"])
    assert pd.isna(row_b["units_l3m_pct"])
    assert pd.isna(row_b["vpo_l3m_pct"])

    assert row_a["revenue"] != row_b["revenue"]
    assert row_a["vpo"] != row_b["vpo"]
    assert row_a["revenue_3m"] >= 0
    assert row_b["revenue_3m"] >= 0
    assert row_a["vpo_3m"] > 0
    assert row_b["vpo_3m"] > 0


def test_new_store_started_in_latest_month():
    df = pd.DataFrame([
        {"month_year": pd.Period("2024-06", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 50, "revenue": 500, "first_pod_flag": 1, "first_store_flag": 1, "reorder_flag": 0, "status": "New", "first_month_purchased": pd.Period("2024-06", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
    ])

    with patch(DATETIME_PATH) as mock_dt:
        mock_dt.today.return_value = datetime(2024, 8, 1)

        store = export_store_level_table(df, [])
        grain = export_summary_by_grain(df, ["chain"])

    s1 = store[store["coded_customer"] == "s1"].iloc[0]
    row_a = grain[grain["chain"] == "A"].iloc[0]

    assert_value(s1["revenue"], 500)
    assert_value(s1["units"], 50)
    assert_value(s1["reorders"], 0)
    assert_value(s1["vpo"], 50 / 2 / 4)

    # only 2 rows in spine (Jun-Jul) -> 3m should be NaN
    assert pd.isna(s1["revenue_3m"])
    assert pd.isna(s1["units_3m"])
    assert pd.isna(s1["vpo_3m"])

    assert pd.isna(s1["revenue_l3m_pct"])
    assert pd.isna(s1["units_l3m_pct"])
    assert pd.isna(s1["vpo_l3m_pct"])

    assert_value(row_a["revenue"], 500)
    assert_value(row_a["vpo"], 50 / 2 / 4)
    assert_value(row_a["reorder_rate"], 0.0)
    assert pd.isna(row_a["revenue_3m"])
    assert pd.isna(row_a["revenue_l3m_pct"])


def test_monthly_summary_with_gap():
    df = pd.DataFrame([
        {"month_year": pd.Period("2024-01", freq="M"), "coded_customer": "s1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 10, "revenue": 100, "first_pod_flag": 1, "first_store_flag": 1, "reorder_flag": 0},
        {"month_year": pd.Period("2024-02", freq="M"), "coded_customer": "s1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 10, "revenue": 100, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        {"month_year": pd.Period("2024-04", freq="M"), "coded_customer": "s1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 10, "revenue": 100, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        {"month_year": pd.Period("2024-05", freq="M"), "coded_customer": "s1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 10, "revenue": 100, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
    ])

    with patch(DATETIME_PATH) as mock_dt:
        mock_dt.today.return_value = datetime(2024, 6, 1)

        result = (
            export_monthly_summary(df)
            .sort_values("month_year")
            .reset_index(drop=True)
        )

    assert len(result) == 5
    assert result["month_year"].tolist() == list(pd.period_range("2024-01", "2024-05", freq="M"))
    assert result["revenue"].tolist() == [100, 100, 0, 100, 100]
    assert result["units"].tolist() == [10, 10, 0, 10, 10]
    assert result["active_pods"].tolist() == [1, 1, 1, 1, 1]
    assert result["new_pods"].tolist() == [1, 0, 0, 0, 0]

    assert_value(result["vpo"].iloc[2], 0.0)
    assert_value(result["reorder_rate"].iloc[2], 0.0)

    assert_value(result["revenue_3m"].iloc[4], 200)
    assert_value(result["units_3m"].iloc[4], 20)
    assert_value(result["vpo_3m"].iloc[4], 20 / 3 / 4)

    # only 5 rows in spine -> l3m_pct still NaN
    assert pd.isna(result["revenue_l3m_pct"].iloc[4])

    assert_value(result["reorder_rate_3m"].iloc[4], 2 / 3)


def test_multi_sku_vpo_calculation():
    df = pd.DataFrame([
        {"month_year": pd.Period("2024-01", freq="M"), "coded_customer": "s1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 10, "revenue": 100, "first_pod_flag": 1, "first_store_flag": 1, "reorder_flag": 0},
        {"month_year": pd.Period("2024-02", freq="M"), "coded_customer": "s1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 10, "revenue": 100, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        {"month_year": pd.Period("2024-03", freq="M"), "coded_customer": "s1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 10, "revenue": 100, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        {"month_year": pd.Period("2024-03", freq="M"), "coded_customer": "s1", "sku": "skuB", "pod_helper": "s1_skuB", "units": 5, "revenue": 50, "first_pod_flag": 1, "first_store_flag": 0, "reorder_flag": 0},
        {"month_year": pd.Period("2024-04", freq="M"), "coded_customer": "s1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 10, "revenue": 100, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        {"month_year": pd.Period("2024-04", freq="M"), "coded_customer": "s1", "sku": "skuB", "pod_helper": "s1_skuB", "units": 5, "revenue": 50, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
    ])

    with patch(DATETIME_PATH) as mock_dt:
        mock_dt.today.return_value = datetime(2024, 5, 1)

        result = export_monthly_summary(df).sort_values("month_year").reset_index(drop=True)

    assert result["active_pods"].tolist() == [1, 1, 2, 2]
    assert result["new_pods"].tolist() == [1, 0, 1, 0]

    assert_value(result["vpo"].iloc[0], 10/1/4)
    assert_value(result["vpo"].iloc[1], 10/1/4)
    assert_value(result["vpo"].iloc[2], 15/2/4)
    assert_value(result["vpo"].iloc[3], 15/2/4)

    assert_value(result["vpo_3m"].iloc[3], 40/5/4)
    assert_value(result["average_skus_per_store"].iloc[2], 2.0)
    assert_value(result["average_skus_per_store"].iloc[3], 2.0)


def test_global_invariants(dropoff_df):
    with patch(DATETIME_PATH) as mock_dt:
        mock_dt.today.return_value = datetime(2024, 8, 1)

        monthly = export_monthly_summary(dropoff_df).sort_values("month_year").reset_index(drop=True)
        by_chain = export_summary_by_grain(dropoff_df, ["chain"])
        store = export_store_level_table(dropoff_df, [])

    assert (monthly["active_pods"].diff().fillna(0) >= 0).all()
    assert (monthly["new_pods"] >= 0).all()
    assert (monthly["active_pods"] == monthly["new_pods"].cumsum()).all()
    assert (monthly["revenue"] >= 0).all()
    assert (monthly["units"] >= 0).all()

    mask = monthly["active_pods"] > 0
    assert (monthly.loc[mask, "vpo"] >= 0).all()

    rr = monthly["reorder_rate"].dropna()
    assert (rr >= 0).all() and (rr <= 1).all()

    assert monthly["revenue_3m"].isna().sum() == 2
    assert monthly["vpo_3m"].isna().sum() == 2
    assert monthly["reorder_rate_3m"].isna().sum() == 2
    assert monthly["revenue_l3m_pct"].isna().sum() == 5

    assert (by_chain["active_pods"] > 0).all()
    assert (by_chain["vpo"] > 0).all()

    # only chain A exists in this fixture
    grain_rev = by_chain[by_chain["chain"] == "A"]["revenue"].iloc[0]
    store_rev = store["revenue"].sum()
    assert_value(grain_rev, float(store_rev))

    assert (store["skus_carrying"] >= 1).all()
    for _, row in store.iterrows():
        assert row["reorders"] >= 0

    assert (store["vpo"] > 0).all()
    assert (store["revenue_3m"] >= 0).all()
    assert (store["vpo_3m"] >= 0).all()

# ─────────────────────────────────────────────────────────────────────────────
# Additional lock-in tests
# ─────────────────────────────────────────────────────────────────────────────

def test_l3m_shift_is_exactly_metric_3m_shifted_3_rows():
    """
    Proves metric_l3m is literally metric_3m.shift(3), not a reconstructed window.
    """
    df = pd.DataFrame(
        {
            "month_year": pd.period_range("2024-01", "2024-06", freq="M"),
            "revenue": [10, 20, 30, 40, 50, 60],
            "revenue_3m": [None, None, 60, 90, 120, 150],
        }
    )

    result = (
        add_prior_month_columns(df, [], "revenue", l3m=True)
        .sort_values("month_year")
        .reset_index(drop=True)
    )

    expected_l3m = [None, None, None, None, None, 60]
    for i, ev in enumerate(expected_l3m):
        assert_value(result.loc[i, "revenue_l3m"], ev)


def test_l3m_pct_requires_exactly_six_rows_boundary():
    """
    5 rows -> l3m_pct should still be NaN
    6 rows -> l3m_pct should become valid on the 6th row
    """
    df_5 = pd.DataFrame(
        {
            "month_year": pd.period_range("2024-01", "2024-05", freq="M"),
            "revenue": [10, 20, 30, 40, 50],
        }
    )
    df_6 = pd.DataFrame(
        {
            "month_year": pd.period_range("2024-01", "2024-06", freq="M"),
            "revenue": [10, 20, 30, 40, 50, 60],
        }
    )

    res_5 = add_additive_metric_3m(df_5, [], "revenue")
    res_5 = add_prior_month_columns(res_5, [], "revenue", l3m=True)
    res_5 = add_pct_change_columns(res_5, "revenue", l3m=True)
    res_5 = res_5.sort_values("month_year").reset_index(drop=True)

    assert pd.isna(res_5.loc[4, "revenue_l3m_pct"])

    res_6 = add_additive_metric_3m(df_6, [], "revenue")
    res_6 = add_prior_month_columns(res_6, [], "revenue", l3m=True)
    res_6 = add_pct_change_columns(res_6, "revenue", l3m=True)
    res_6 = res_6.sort_values("month_year").reset_index(drop=True)

    # revenue_3m at Jun = Apr+May+Jun = 40+50+60 = 150
    # revenue_l3m at Jun = Mar row's revenue_3m = Jan+Feb+Mar = 60
    assert_value(res_6.loc[5, "revenue_l3m_pct"], (150 - 60) / 60)


def test_multi_group_l3m_pct_one_group_valid_one_group_nan():
    """
    Group A has 6 rows -> valid l3m_pct
    Group B has only 5 rows -> l3m_pct should be NaN
    """
    df = pd.DataFrame(
        {
            "chain": ["A"] * 6 + ["B"] * 5,
            "month_year": list(pd.period_range("2024-01", "2024-06", freq="M"))
            + list(pd.period_range("2024-02", "2024-06", freq="M")),
            "revenue": [10, 20, 30, 40, 50, 60, 5, 10, 15, 20, 25],
        }
    )

    result = add_additive_metric_3m(df, ["chain", "month_year"], "revenue")
    result = add_prior_month_columns(result, ["chain", "month_year"], "revenue", l3m=True)
    result = add_pct_change_columns(result, "revenue", l3m=True)
    result = result.sort_values(["chain", "month_year"]).reset_index(drop=True)

    a_jun = result[(result["chain"] == "A") & (result["month_year"] == pd.Period("2024-06", freq="M"))].iloc[0]
    b_jun = result[(result["chain"] == "B") & (result["month_year"] == pd.Period("2024-06", freq="M"))].iloc[0]

    # A: valid
    # A revenue_3m at Jun = 40+50+60 = 150
    # A revenue_l3m at Jun = Mar revenue_3m = 10+20+30 = 60
    assert_value(a_jun["revenue_l3m_pct"], (150 - 60) / 60)

    # B: only 5 rows total -> invalid
    assert pd.isna(b_jun["revenue_l3m_pct"])


def test_reorder_rate_3m_zero_vs_nan_distinction():
    """
    Case A: denominator exists but repeats = 0 -> reorder_rate_3m = 0.0
    Case B: denominator does not exist -> reorder_rate_3m = NaN
    """
    # Case A: existing buyer persists through 3m window but never repeats there
    df_zero = pd.DataFrame(
        [
            # store exists before window
            {"chain": "A", "coded_customer": "A1", "pod_helper": "P1", "month_year": pd.Period("2024-03", freq="M"), "units": 10, "first_pod_flag": 1, "first_store_flag": 1, "reorder_flag": 0},
            {"chain": "A", "coded_customer": "A1", "pod_helper": "P1", "month_year": pd.Period("2024-04", freq="M"), "units": 10, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
            # anchor group/month so reporting end extends to Jul
            {"chain": "B", "coded_customer": "B1", "pod_helper": "P2", "month_year": pd.Period("2024-07", freq="M"), "units": 1, "first_pod_flag": 1, "first_store_flag": 1, "reorder_flag": 0},
        ]
    )

    res_zero = (
        calculate_reorder_rate_3m(
            df_filtered=df_zero[df_zero["month_year"] >= pd.Period("2024-04", freq="M")],
            df_full=df_zero,
            group_cols=["chain"],
            selected_years=[2024],
            selected_months=[pd.Period("2024-04", freq="M"), pd.Period("2024-05", freq="M"), pd.Period("2024-06", freq="M"), pd.Period("2024-07", freq="M")],
        )
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    a_jul = res_zero[(res_zero["chain"] == "A") & (res_zero["month_year"] == pd.Period("2024-07", freq="M"))].iloc[0]

    # Apr-May-Jun-Jul spine for A means Jul current 3m window = May+Jun+Jul
    # Existing buyers present, repeats in that window = 0 -> should be 0.0
    assert_value(a_jul["reorder_rate_3m"], 0.0)

    # Case B: brand new store only, no denominator
    df_nan = pd.DataFrame(
        [
            {"chain": "A", "coded_customer": "A1", "pod_helper": "P1", "month_year": pd.Period("2024-07", freq="M"), "units": 10, "first_pod_flag": 1, "first_store_flag": 1, "reorder_flag": 0},
        ]
    )

    res_nan = (
        calculate_reorder_rate_3m(
            df_filtered=df_nan,
            df_full=df_nan,
            group_cols=["chain"],
            selected_years=[2024],
            selected_months=[pd.Period("2024-07", freq="M")],
        )
        .sort_values(["chain", "month_year"])
        .reset_index(drop=True)
    )

    a_only = res_nan.iloc[0]
    assert pd.isna(a_only["reorder_rate_3m"])


def test_store_internal_gap_active_pod_carries_and_vpo_zero_in_gap_month():
    """
    Store buys Jan, skips Feb, buys Mar.
    Gap month Feb should still appear on the spine.
    active_pods should carry.
    vpo in Feb should be 0, not NaN.
    """
    df = pd.DataFrame(
        [
            {"month_year": pd.Period("2024-01", freq="M"), "coded_customer": "s1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 10, "revenue": 100, "first_pod_flag": 1, "first_store_flag": 1, "reorder_flag": 0},
            {"month_year": pd.Period("2024-03", freq="M"), "coded_customer": "s1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 10, "revenue": 100, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1},
        ]
    )

    with patch(DATETIME_PATH) as mock_dt:
        mock_dt.today.return_value = datetime(2024, 4, 1)

        result = (
            export_monthly_summary(df)
            .sort_values("month_year")
            .reset_index(drop=True)
        )

    # Jan-Feb-Mar
    assert result["month_year"].tolist() == list(pd.period_range("2024-01", "2024-03", freq="M"))
    assert result["revenue"].tolist() == [100, 0, 100]
    assert result["units"].tolist() == [10, 0, 10]
    assert result["active_pods"].tolist() == [1, 1, 1]
    assert_value(result.loc[1, "vpo"], 0.0)


def test_multiple_pods_then_silence_extended_months_affect_vpo_correctly():
    """
    skuA starts Jan, skuB starts Mar, then no sales after Apr.
    With today mocked to Jun 1, reporting end = May.
    Pod-month denominator should include silent May.
    """
    df = pd.DataFrame(
        [
            {"month_year": pd.Period("2024-01", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 10, "revenue": 100, "first_pod_flag": 1, "first_store_flag": 1, "reorder_flag": 0, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-04", freq="M")},
            {"month_year": pd.Period("2024-02", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 10, "revenue": 100, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-04", freq="M")},
            {"month_year": pd.Period("2024-03", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 10, "revenue": 100, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-04", freq="M")},
            {"month_year": pd.Period("2024-03", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuB", "pod_helper": "s1_skuB", "units": 5, "revenue": 50, "first_pod_flag": 1, "first_store_flag": 0, "reorder_flag": 0, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-04", freq="M")},
            {"month_year": pd.Period("2024-04", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s1_skuA", "units": 10, "revenue": 100, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-04", freq="M")},
            {"month_year": pd.Period("2024-04", freq="M"), "coded_customer": "s1", "chain": "A", "city": "Miami", "state": "FL", "zip": "33101", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuB", "pod_helper": "s1_skuB", "units": 5, "revenue": 50, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-04", freq="M")},
        ]
    )

    with patch(DATETIME_PATH) as mock_dt:
        mock_dt.today.return_value = datetime(2024, 6, 1)

        store = export_store_level_table(df, [])

    row = store.iloc[0]

    # base vpo: Jan-May, pod months = skuA(5) + skuB(3) = 8, units = 50
    assert_value(row["vpo"], 50 / 8 / 4)

    # latest row is May, 3m window = Mar+Apr+May
    # units = 15 + 15 + 0 = 30
    # pod months = 2 + 2 + 2 = 6
    assert_value(row["revenue_3m"], 300)
    assert_value(row["units_3m"], 30)
    assert_value(row["vpo_3m"], 30 / 6 / 4)
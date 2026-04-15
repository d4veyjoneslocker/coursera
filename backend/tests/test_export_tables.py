import pandas as pd
import pytest

from backend.exports.ai_ready.export_tables import export_monthly_summary

def assert_value(actual, expected, tol=1e-9):
    if pd.isna(expected):
        assert pd.isna(actual), f"Expected NaN, got {actual}"
    elif isinstance(expected, float):
        assert actual == pytest.approx(expected, rel=tol, abs=tol), f"Expected {expected}, got {actual}"
    else:
        assert actual == expected, f"Expected {expected}, got {actual}"


@pytest.fixture
def sample_monthly_summary_df():
    data = [
        # JAN
        {
            "month_year": pd.Period("2024-01", freq="M"),
            "coded_customer": "s1",
            "sku": "skuA",
            "pod_helper": "s1_skuA",
            "units": 10,
            "revenue": 100,
            "first_pod_flag": 1,
            "first_store_flag": 1,
            "reorder_flag": 0,
        },

        # FEB
        {
            "month_year": pd.Period("2024-02", freq="M"),
            "coded_customer": "s1",
            "sku": "skuA",
            "pod_helper": "s1_skuA",
            "units": 20,
            "revenue": 200,
            "first_pod_flag": 0,
            "first_store_flag": 0,
            "reorder_flag": 1,
        },
        {
            "month_year": pd.Period("2024-02", freq="M"),
            "coded_customer": "s2",
            "sku": "skuA",
            "pod_helper": "s2_skuA",
            "units": 5,
            "revenue": 50,
            "first_pod_flag": 1,
            "first_store_flag": 1,
            "reorder_flag": 0,
        },

        # MAR
        {
            "month_year": pd.Period("2024-03", freq="M"),
            "coded_customer": "s1",
            "sku": "skuA",
            "pod_helper": "s1_skuA",
            "units": 30,
            "revenue": 300,
            "first_pod_flag": 0,
            "first_store_flag": 0,
            "reorder_flag": 1,
        },
        {
            "month_year": pd.Period("2024-03", freq="M"),
            "coded_customer": "s2",
            "sku": "skuA",
            "pod_helper": "s2_skuA",
            "units": 15,
            "revenue": 150,
            "first_pod_flag": 0,
            "first_store_flag": 0,
            "reorder_flag": 1,
        },
        {
            "month_year": pd.Period("2024-03", freq="M"),
            "coded_customer": "s1",
            "sku": "skuB",
            "pod_helper": "s1_skuB",
            "units": 7,
            "revenue": 70,
            "first_pod_flag": 1,
            "first_store_flag": 0,
            "reorder_flag": 0,
        },

        # APR
        {
            "month_year": pd.Period("2024-04", freq="M"),
            "coded_customer": "s1",
            "sku": "skuA",
            "pod_helper": "s1_skuA",
            "units": 40,
            "revenue": 400,
            "first_pod_flag": 0,
            "first_store_flag": 0,
            "reorder_flag": 1,
        },
        {
            "month_year": pd.Period("2024-04", freq="M"),
            "coded_customer": "s2",
            "sku": "skuA",
            "pod_helper": "s2_skuA",
            "units": 25,
            "revenue": 250,
            "first_pod_flag": 0,
            "first_store_flag": 0,
            "reorder_flag": 1,
        },
        {
            "month_year": pd.Period("2024-04", freq="M"),
            "coded_customer": "s1",
            "sku": "skuB",
            "pod_helper": "s1_skuB",
            "units": 14,
            "revenue": 140,
            "first_pod_flag": 0,
            "first_store_flag": 0,
            "reorder_flag": 1,
        },
        {
            "month_year": pd.Period("2024-04", freq="M"),
            "coded_customer": "s3",
            "sku": "skuA",
            "pod_helper": "s3_skuA",
            "units": 9,
            "revenue": 90,
            "first_pod_flag": 1,
            "first_store_flag": 1,
            "reorder_flag": 0,
        },

        # MAY
        {
            "month_year": pd.Period("2024-05", freq="M"),
            "coded_customer": "s1",
            "sku": "skuA",
            "pod_helper": "s1_skuA",
            "units": 50,
            "revenue": 500,
            "first_pod_flag": 0,
            "first_store_flag": 0,
            "reorder_flag": 1,
        },
        {
            "month_year": pd.Period("2024-05", freq="M"),
            "coded_customer": "s1",
            "sku": "skuB",
            "pod_helper": "s1_skuB",
            "units": 21,
            "revenue": 210,
            "first_pod_flag": 0,
            "first_store_flag": 0,
            "reorder_flag": 1,
        },
        {
            "month_year": pd.Period("2024-05", freq="M"),
            "coded_customer": "s3",
            "sku": "skuA",
            "pod_helper": "s3_skuA",
            "units": 18,
            "revenue": 180,
            "first_pod_flag": 0,
            "first_store_flag": 0,
            "reorder_flag": 1,
        },

        # JUN
        {
            "month_year": pd.Period("2024-06", freq="M"),
            "coded_customer": "s1",
            "sku": "skuA",
            "pod_helper": "s1_skuA",
            "units": 60,
            "revenue": 600,
            "first_pod_flag": 0,
            "first_store_flag": 0,
            "reorder_flag": 1,
        },
        {
            "month_year": pd.Period("2024-06", freq="M"),
            "coded_customer": "s2",
            "sku": "skuA",
            "pod_helper": "s2_skuA",
            "units": 13,
            "revenue": 130,
            "first_pod_flag": 0,
            "first_store_flag": 0,
            "reorder_flag": 1,
        },
        {
            "month_year": pd.Period("2024-06", freq="M"),
            "coded_customer": "s1",
            "sku": "skuB",
            "pod_helper": "s1_skuB",
            "units": 28,
            "revenue": 280,
            "first_pod_flag": 0,
            "first_store_flag": 0,
            "reorder_flag": 1,
        },
        {
            "month_year": pd.Period("2024-06", freq="M"),
            "coded_customer": "s3",
            "sku": "skuA",
            "pod_helper": "s3_skuA",
            "units": 27,
            "revenue": 270,
            "first_pod_flag": 0,
            "first_store_flag": 0,
            "reorder_flag": 1,
        },

        # JUL
        {
            "month_year": pd.Period("2024-07", freq="M"),
            "coded_customer": "s1",
            "sku": "skuA",
            "pod_helper": "s1_skuA",
            "units": 70,
            "revenue": 700,
            "first_pod_flag": 0,
            "first_store_flag": 0,
            "reorder_flag": 1,
        },
        {
            "month_year": pd.Period("2024-07", freq="M"),
            "coded_customer": "s2",
            "sku": "skuA",
            "pod_helper": "s2_skuA",
            "units": 17,
            "revenue": 170,
            "first_pod_flag": 0,
            "first_store_flag": 0,
            "reorder_flag": 1,
        },
        {
            "month_year": pd.Period("2024-07", freq="M"),
            "coded_customer": "s1",
            "sku": "skuB",
            "pod_helper": "s1_skuB",
            "units": 35,
            "revenue": 350,
            "first_pod_flag": 0,
            "first_store_flag": 0,
            "reorder_flag": 1,
        },
        {
            "month_year": pd.Period("2024-07", freq="M"),
            "coded_customer": "s3",
            "sku": "skuA",
            "pod_helper": "s3_skuA",
            "units": 33,
            "revenue": 330,
            "first_pod_flag": 0,
            "first_store_flag": 0,
            "reorder_flag": 1,
        },
    ]

    return pd.DataFrame(data)


def test_monthly_summary_full_output(sample_monthly_summary_df):
    result = export_monthly_summary(sample_monthly_summary_df).sort_values("month_year").reset_index(drop=True)

    expected = pd.DataFrame(
        {
            "month_year": pd.period_range("2024-01", "2024-07", freq="M"),
            "revenue": [100, 250, 520, 880, 890, 1280, 1550],
            "units": [10, 25, 52, 88, 89, 128, 155],
            "new_pods": [1, 1, 1, 1, 0, 0, 0],
            "active_pods": [1, 2, 3, 4, 4, 4, 4],
            "buying_stores": [1, 2, 2, 3, 2, 3, 3],
            "vpo": [
                10.0,
                12.5,
                52 / 3,
                22.0,
                22.25,
                32.0,
                38.75,
            ],
            "reorder_rate": [
                None,
                1.0,
                1.0,
                1.0,
                2 / 3,
                1.0,
                1.0,
            ],
            "average_skus_per_store": [
                1.0,
                1.0,
                1.5,
                4 / 3,
                1.5,
                4 / 3,
                4 / 3,
            ],
            "revenue_3m": [
                None,
                None,
                870.0,
                1650.0,
                2290.0,
                3050.0,
                3720.0,
            ],
            "units_3m": [
                None,
                None,
                87.0,
                165.0,
                229.0,
                305.0,
                372.0,
            ],
            "new_pods_3m": [
                None,
                None,
                3.0,
                3.0,
                2.0,
                1.0,
                0.0,
            ],
            "buying_stores_3m": [
                None,
                None,
                2.0,
                3.0,
                3.0,
                3.0,
                3.0,
            ],
            "vpo_3m": [
                None,
                None,
                87 / 6 / 4,
                165 / 9 / 4,
                229 / 11 / 4,
                305 / 12 / 4,
                372 / 12 / 4,
            ],
            "reorder_rate_3m": [
                None,
                None,
                1.0,
                1.0,
                6 / 7,
                7 / 8,
                8 / 9,
            ],
            "revenue_l3m_pct": [
                None,
                None,
                None,
                None,
                None,
                (1280 - 870) / 870,
                (1550 - 1650) / 1650,
            ],
            "units_l3m_pct": [
                None,
                None,
                None,
                None,
                None,
                (128 - 87) / 87,
                (155 - 165) / 165,
            ],
            "new_pods_l3m_pct": [
                None,
                None,
                None,
                None,
                None,
                (0 - 3) / 3,
                (0 - 3) / 3,
            ],
            "buying_stores_l3m_pct": [
                None,
                None,
                None,
                None,
                None,
                (3 - 2) / 2,
                (3 - 3) / 3,
            ],
            "vpo_l3m_pct": [
                None,
                None,
                None,
                None,
                None,
                (32.0 - (87 / 6 / 4)) / (87 / 6 / 4),
                (38.75 - (165 / 9 / 4)) / (165 / 9 / 4),
            ],
            "reorder_rate_l3m_pct": [
                None,
                None,
                None,
                None,
                None,
                (1.0 - 1.0) / 1.0,
                (1.0 - 1.0) / 1.0,
            ],
        }
    )

    assert list(result.columns) == list(expected.columns)
    assert len(result) == 7

    for row_idx in range(len(expected)):
        for col in expected.columns:
            assert_value(result.loc[row_idx, col], expected.loc[row_idx, col])

import pandas as pd
import pytest

from backend.exports.ai_ready.export_tables import (
    export_summary_by_grain,
    export_store_level_table,
)


def assert_value(actual, expected, tol=1e-9):
    if pd.isna(expected):
        assert pd.isna(actual), f"Expected NaN, got {actual}"
    elif isinstance(expected, float):
        assert actual == pytest.approx(expected, rel=tol, abs=tol), f"Expected {expected}, got {actual}"
    else:
        assert actual == expected, f"Expected {expected}, got {actual}"


@pytest.fixture
def sample_export_df():
    data = [
        # -----------------
        # CHAIN A / STORE 1
        # -----------------
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

        # -----------------
        # CHAIN A / STORE 2
        # -----------------
        {"month_year": pd.Period("2024-02", freq="M"), "coded_customer": "s2", "chain": "A", "city": "Orlando", "state": "FL", "zip": "32801", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s2_skuA", "units": 5, "revenue": 50, "first_pod_flag": 1, "first_store_flag": 1, "reorder_flag": 0, "status": "Healthy", "first_month_purchased": pd.Period("2024-02", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-03", freq="M"), "coded_customer": "s2", "chain": "A", "city": "Orlando", "state": "FL", "zip": "32801", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s2_skuA", "units": 15, "revenue": 150, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-02", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-04", freq="M"), "coded_customer": "s2", "chain": "A", "city": "Orlando", "state": "FL", "zip": "32801", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s2_skuA", "units": 25, "revenue": 250, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-02", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-06", freq="M"), "coded_customer": "s2", "chain": "A", "city": "Orlando", "state": "FL", "zip": "32801", "channel": "Natural", "distributor": "UNFI", "dc": "DC1", "sku": "skuA", "pod_helper": "s2_skuA", "units": 13, "revenue": 130, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Healthy", "first_month_purchased": pd.Period("2024-02", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},

        # -----------------
        # CHAIN B / STORE 3
        # -----------------
        {"month_year": pd.Period("2024-01", freq="M"), "coded_customer": "s3", "chain": "B", "city": "Tampa", "state": "FL", "zip": "33601", "channel": "Mass", "distributor": "KeHE", "dc": "DC2", "sku": "skuA", "pod_helper": "s3_skuA", "units": 8, "revenue": 80, "first_pod_flag": 1, "first_store_flag": 1, "reorder_flag": 0, "status": "Struggling", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-03", freq="M"), "coded_customer": "s3", "chain": "B", "city": "Tampa", "state": "FL", "zip": "33601", "channel": "Mass", "distributor": "KeHE", "dc": "DC2", "sku": "skuA", "pod_helper": "s3_skuA", "units": 12, "revenue": 120, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Struggling", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-04", freq="M"), "coded_customer": "s3", "chain": "B", "city": "Tampa", "state": "FL", "zip": "33601", "channel": "Mass", "distributor": "KeHE", "dc": "DC2", "sku": "skuA", "pod_helper": "s3_skuA", "units": 20, "revenue": 200, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Struggling", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-05", freq="M"), "coded_customer": "s3", "chain": "B", "city": "Tampa", "state": "FL", "zip": "33601", "channel": "Mass", "distributor": "KeHE", "dc": "DC2", "sku": "skuA", "pod_helper": "s3_skuA", "units": 18, "revenue": 180, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Struggling", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
        {"month_year": pd.Period("2024-06", freq="M"), "coded_customer": "s3", "chain": "B", "city": "Tampa", "state": "FL", "zip": "33601", "channel": "Mass", "distributor": "KeHE", "dc": "DC2", "sku": "skuA", "pod_helper": "s3_skuA", "units": 27, "revenue": 270, "first_pod_flag": 0, "first_store_flag": 0, "reorder_flag": 1, "status": "Struggling", "first_month_purchased": pd.Period("2024-01", freq="M"), "last_month_purchased": pd.Period("2024-06", freq="M")},
    ]
    return pd.DataFrame(data)


def test_export_summary_by_grain_chain(sample_export_df):
    result = (
        export_summary_by_grain(sample_export_df, ["chain"])
        .sort_values("chain")
        .reset_index(drop=True)
    )

    expected_cols = [
        "chain",
        "revenue",
        "units",
        "new_pods",
        "active_pods",
        "buying_stores",
        "vpo",
        "reorder_rate",
        "average_skus_per_store",
        "revenue_3m",
        "units_3m",
        "new_pods_3m",
        "buying_stores_3m",
        "vpo_3m",
        "reorder_rate_3m",
        "revenue_l3m_pct",
        "units_l3m_pct",
        "new_pods_l3m_pct",
        "buying_stores_l3m_pct",
        "vpo_l3m_pct",
        "reorder_rate_l3m_pct",
    ]

    assert list(result.columns) == expected_cols
    assert result["chain"].tolist() == ["A", "B"]

    row_a = result[result["chain"] == "A"].iloc[0]
    row_b = result[result["chain"] == "B"].iloc[0]

    # -----------------
    # Chain A exacts
    # -----------------
    assert_value(row_a["revenue"], 3380)
    assert_value(row_a["units"], 338)
    assert_value(row_a["new_pods"], 3)
    assert_value(row_a["active_pods"], 3)
    assert_value(row_a["buying_stores"], 2)

    # average skus per store:
    # s1 carries 2, s2 carries 1  => (2 + 1) / 2 = 1.5
    assert_value(row_a["average_skus_per_store"], 1.5)

    # latest full month is Jun 2024
    # Apr+May+Jun revenue = (790 + 710 + 1010) = 2510
    # Apr+May+Jun units   = (79  + 71  + 101 ) = 251
    assert_value(row_a["revenue_3m"], 2510.0)
    assert_value(row_a["units_3m"], 251.0)
    assert_value(row_a["new_pods_3m"], 0.0)
    assert_value(row_a["buying_stores_3m"], 2.0)

    # reorder logic with current denominator:
    # s1: first month Jan -> possible reorders through Jun = 5, actual reorder months = 5
    # s2: first month Feb -> possible reorders through Jun = 4, actual reorder months = 3
    # total reorder_rate = 8 / 9
    assert_value(row_a["reorder_rate"], 8 / 9)

    # 3M reorder rate at Jun:
    # Apr: repeat=2
    # May: repeat=1
    # Jun: repeat=2
    # numerator = 5
    #
    # Apr existing = 2
    # May existing = 2
    # Jun existing = 2
    # denominator = 6
    assert_value(row_a["reorder_rate_3m"], 5 / 6)

    # vpo and vpo_3m should be positive and finite
    assert row_a["vpo"] > 0
    assert row_a["vpo_3m"] > 0

    # -----------------
    # Chain B exacts
    # -----------------
    assert_value(row_b["revenue"], 850)
    assert_value(row_b["units"], 85)
    assert_value(row_b["new_pods"], 1)
    assert_value(row_b["active_pods"], 1)
    assert_value(row_b["buying_stores"], 1)
    assert_value(row_b["average_skus_per_store"], 1.0)

    # Apr+May+Jun
    assert_value(row_b["revenue_3m"], 650.0)
    assert_value(row_b["units_3m"], 65.0)
    assert_value(row_b["new_pods_3m"], 0.0)
    assert_value(row_b["buying_stores_3m"], 1.0)

    # s3 first month Jan -> possible reorders through Jun = 5
    # actual reorder months = Mar, Apr, May, Jun = 4
    assert_value(row_b["reorder_rate"], 4 / 5)

    # 3M reorder rate at Jun:
    # Apr, May, Jun each repeat=1 and existing=1
    assert_value(row_b["reorder_rate_3m"], 1.0)

    # -----------------
    # Rigorous reorder checks
    # -----------------
    # At least one chain should be strictly between 0 and 1
    assert ((result["reorder_rate"] > 0) & (result["reorder_rate"] < 1)).any()
    assert ((result["reorder_rate_3m"] > 0) & (result["reorder_rate_3m"] < 1)).any()

    # No chain should exceed 1
    assert ((result["reorder_rate"] <= 1) | (result["reorder_rate"].isna())).all()
    assert ((result["reorder_rate_3m"] <= 1) | (result["reorder_rate_3m"].isna())).all()


def test_export_store_level_table_basic(sample_export_df):
    result = (
        export_store_level_table(sample_export_df, [])
        .sort_values("coded_customer")
        .reset_index(drop=True)
    )

    expected_cols = [
        "coded_customer",
        "chain",
        "city",
        "state",
        "zip",
        "channel",
        "distributor",
        "dc",
        "skus_carrying",
        "status",
        "first_month_purchased",
        "last_month_purchased",
        "revenue",
        "units",
        "reorders",
        "vpo",
        "reorder_rate",
        "revenue_3m",
        "units_3m",
        "vpo_3m",
        "reorder_rate_3m",
        "revenue_l3m_pct",
        "units_l3m_pct",
        "vpo_l3m_pct",
        "reorder_rate_l3m_pct",
    ]

    assert list(result.columns) == expected_cols
    assert result["coded_customer"].tolist() == ["s1", "s2", "s3"]

    row1 = result[result["coded_customer"] == "s1"].iloc[0]
    row2 = result[result["coded_customer"] == "s2"].iloc[0]
    row3 = result[result["coded_customer"] == "s3"].iloc[0]

    # -----------------
    # s1
    # -----------------
    assert_value(row1["chain"], "A")
    assert_value(row1["city"], "Miami")
    assert_value(row1["state"], "FL")
    assert_value(row1["zip"], "33101")
    assert_value(row1["channel"], "Natural")
    assert_value(row1["distributor"], "UNFI")
    assert_value(row1["dc"], "DC1")
    assert_value(row1["status"], "Healthy")
    assert_value(row1["skus_carrying"], 2)
    assert_value(row1["first_month_purchased"], pd.Period("2024-01", freq="M"))
    assert_value(row1["last_month_purchased"], pd.Period("2024-06", freq="M"))
    assert_value(row1["revenue"], 2800)
    assert_value(row1["units"], 280)

    # reorder events are store-month level, not row level:
    # Feb, Mar, Apr, May, Jun = 5
    assert_value(row1["reorders"], 5)

    # possible reorders through Jun:
    # Jan -> Jun span = 5
    # actual reorder months = 5
    assert_value(row1["reorder_rate"], 1.0)

    # last 3 months Apr/May/Jun: 3 reorder months out of 3 possible
    assert_value(row1["reorder_rate_3m"], 1.0)


    # -----------------
    # s2
    # -----------------
    assert_value(row2["chain"], "A")
    assert_value(row2["city"], "Orlando")
    assert_value(row2["state"], "FL")
    assert_value(row2["zip"], "32801")
    assert_value(row2["channel"], "Natural")
    assert_value(row2["distributor"], "UNFI")
    assert_value(row2["dc"], "DC1")
    assert_value(row2["status"], "Healthy")
    assert_value(row2["skus_carrying"], 1)
    assert_value(row2["first_month_purchased"], pd.Period("2024-02", freq="M"))
    assert_value(row2["last_month_purchased"], pd.Period("2024-06", freq="M"))
    assert_value(row2["revenue"], 580)
    assert_value(row2["units"], 58)

    # reorder months = Mar, Apr, Jun
    assert_value(row2["reorders"], 3)

    # possible reorder months through Jun:
    # Mar, Apr, May, Jun = 4
    assert_value(row2["reorder_rate"], 3 / 4)

    # last 3 months Apr/May/Jun:
    # Apr reorder=1, May reorder=0, Jun reorder=1 => 2 / 3
    assert_value(row2["reorder_rate_3m"], 2 / 3)


    # -----------------
    # s3
    # -----------------
    assert_value(row3["chain"], "B")
    assert_value(row3["city"], "Tampa")
    assert_value(row3["state"], "FL")
    assert_value(row3["zip"], "33601")
    assert_value(row3["channel"], "Mass")
    assert_value(row3["distributor"], "KeHE")
    assert_value(row3["dc"], "DC2")
    assert_value(row3["status"], "Struggling")
    assert_value(row3["skus_carrying"], 1)
    assert_value(row3["first_month_purchased"], pd.Period("2024-01", freq="M"))
    assert_value(row3["last_month_purchased"], pd.Period("2024-06", freq="M"))
    assert_value(row3["revenue"], 850)
    assert_value(row3["units"], 85)

    # reorder months = Mar, Apr, May, Jun
    assert_value(row3["reorders"], 4)

    # Jan -> Jun span = 5 possible reorder months
    assert_value(row3["reorder_rate"], 4 / 5)

    # last 3 months Apr/May/Jun: 3 / 3
    assert_value(row3["reorder_rate_3m"], 1.0)


    # -----------------
    # Rigorous reorder checks
    # -----------------
    # Make sure we truly have a value strictly between 0 and 1
    assert ((result["reorder_rate"] > 0) & (result["reorder_rate"] < 1)).any()
    assert ((result["reorder_rate_3m"] > 0) & (result["reorder_rate_3m"] < 1)).any()

    # No impossible rates
    assert ((result["reorder_rate"] <= 1) | (result["reorder_rate"].isna())).all()
    assert ((result["reorder_rate_3m"] <= 1) | (result["reorder_rate_3m"].isna())).all()
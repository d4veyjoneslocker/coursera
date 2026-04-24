import pandas as pd
import pytest
from backend.filters.filter_table import filter_table
from backend.metrics.features import add_features
from backend.old.core_metrics import monthly_summary, active_store_rate
from backend.old.growth_metrics import add_time_metrics_simple
from backend.old.store_level_metrics import calculate_reorder_stats

import pandas as pd

def load_test_data():
    df = pd.read_csv("backend/tests/data/testing_data.csv")

    string_cols = [
        "helper", "pod_helper", "coded_customer", "customer_name",
        "store_number", "chain", "street_address", "city", "state",
        "zip", "channel", "upc", "sku", "distributor", "dc"
    ]
    for col in string_cols:
        df[col] = df[col].astype(str)

    df["year"] = df["year"].astype("int32")
    df["month"] = df["month"].astype("int32")
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    df["revenue"] = df["revenue"].astype("float64")
    df["units"] = df["units"].astype("int64")

    return df

def load_test_data_6m():
    df = pd.read_csv("backend/tests/data/testing_data_6m.csv")

    string_cols = [
        "helper", "pod_helper", "coded_customer", "customer_name",
        "store_number", "chain", "street_address", "city", "state",
        "zip", "channel", "upc", "sku", "distributor", "dc"
    ]
    for col in string_cols:
        df[col] = df[col].astype(str)

    df["year"] = df["year"].astype("int32")
    df["month"] = df["month"].astype("int32")
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    df["revenue"] = df["revenue"].astype("float64")
    df["units"] = df["units"].astype("int64")

    return df

def load_test_data_status():
    df = pd.read_csv("backend/tests/data/testing_data_status.csv")

    string_cols = [
    "helper", "pod_helper", "coded_customer", "customer_name",
    "store_number", "chain", "street_address", "city", "state",
    "zip", "channel", "upc", "sku", "distributor", "dc"
    ]

    for col in string_cols:
        df[col] = df[col].astype(str)

    df["year"] = df["year"].astype("int32")
    df["month"] = df["month"].astype("int32")
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    df["revenue"] = df["revenue"].astype("float64")
    df["units"] = df["units"].astype("int64")

    return df


def load_edge_case_test_data():
    df = pd.read_csv("backend/tests/data/testing_data_edge_cases.csv")

    string_cols = [
        "helper", "pod_helper", "coded_customer", "customer_name",
        "store_number", "chain", "street_address", "city", "state",
        "zip", "channel", "upc", "sku", "distributor", "dc"
    ]
    for col in string_cols:
        df[col] = df[col].astype(str)

    df["year"] = df["year"].astype("int32")
    df["month"] = df["month"].astype("int32")
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    df["revenue"] = df["revenue"].astype("float64")
    df["units"] = df["units"].astype("int64")

    return df

# FILTERS

def test_filter_chain():
    df = load_test_data()

    result = filter_table(df, chain=["Whole Foods"])

    assert len(result) == 9
    assert result["coded_customer"].nunique() == 3
    assert result["pod_helper"].nunique() == 4
    assert result["units"].sum() == 181

def test_filtered_metrics_single_sku():
    df = load_test_data()
    df_filtered = filter_table(df, sku=["Spicy Beef Ramen"])
    df_features = add_features(df_filtered)

    result = monthly_summary(df_features, df_features)

    jan_row = result[result["month_year"].astype(str) == "2026-01"].iloc[0]
    feb_row = result[result["month_year"].astype(str) == "2026-02"].iloc[0]
    mar_row = result[result["month_year"].astype(str) == "2026-03"].iloc[0]

    assert jan_row["units"] == 45
    assert feb_row["units"] == 45
    assert mar_row["units"] == 53

    assert jan_row["buying_stores"] == 2
    assert feb_row["buying_stores"] == 2
    assert mar_row["buying_stores"] == 2

    assert jan_row["new_pods"] == 2
    assert feb_row["new_pods"] == 0
    assert mar_row["new_pods"] == 0

    assert jan_row["active_pods"] == 2
    assert feb_row["active_pods"] == 2
    assert mar_row["active_pods"] == 2

    assert jan_row["vpo"] == pytest.approx(45 / 2 / 4)
    assert feb_row["vpo"] == pytest.approx(45 / 2 / 4)
    assert mar_row["vpo"] == pytest.approx(53 / 2 / 4)

def test_filter_chain_and_month():
    df = load_test_data()

    result = filter_table(df, chain=["Whole Foods"], month=[1])

    assert len(result) == 3
    assert result["coded_customer"].nunique() == 2

# FEATURE TESTS

def test_purchase_month_features():
    df = load_test_data()

    df_features = add_features(df)

    wf_101 = df_features[df_features["coded_customer"] == "WF_FL_101"]

    assert wf_101["first_month_purchased"].nunique() == 1
    assert str(wf_101["first_month_purchased"].iloc[0]) == "2026-01"

    assert wf_101["second_to_last_month_purchased"].nunique() == 1
    assert str(wf_101["second_to_last_month_purchased"].iloc[0]) == "2026-02"

    assert wf_101["last_month_purchased"].nunique() == 1
    assert str(wf_101["last_month_purchased"].iloc[0]) == "2026-03"

def test_ordering_flags():
    df = load_test_data()
    df_features = add_features(df)

    wf_101 = df_features[df_features["coded_customer"] == "WF_FL_101"]

    # first store flag: both Jan rows should be flagged
    assert wf_101["first_store_flag"].sum() == 2
    assert set(wf_101.loc[wf_101["first_store_flag"], "month_year"].astype(str)) == {"2026-01"}

    # first pod flag: each SKU should have exactly one first pod row
    assert wf_101["first_pod_flag"].sum() == 2
    assert set(wf_101.loc[wf_101["first_pod_flag"], "month_year"].astype(str)) == {"2026-01"}

    # reorder flag at store level: all rows after first month
    assert set(wf_101.loc[wf_101["reorder_flag"], "month_year"].astype(str)) == {"2026-02", "2026-03"}

    # reorder flag at pod level: same result for this store in this dataset
    assert set(wf_101.loc[wf_101["reorder_flag_pod"], "month_year"].astype(str)) == {"2026-02", "2026-03"}

    # first sku month helper column
    assert set(wf_101.loc[wf_101["sku"] == "Spicy Beef Ramen", "first_month_purchased_sku"].astype(str)) == {"2026-01"}
    assert set(wf_101.loc[wf_101["sku"] == "Tom Yum Shrimp Ramen", "first_month_purchased_sku"].astype(str)) == {"2026-01"}

# CALCULATED METRICS TEST

def test_monthly_summary_metrics():
    df = load_test_data()
    df_features = add_features(df)

    result = monthly_summary(df_features, df_features)

    jan_row = result[result["month_year"].astype(str) == "2026-01"].iloc[0]
    feb_row = result[result["month_year"].astype(str) == "2026-02"].iloc[0]
    mar_row = result[result["month_year"].astype(str) == "2026-03"].iloc[0]

    # JAN
    assert jan_row["units"] == 113
    assert jan_row["buying_stores"] == 5
    assert jan_row["active_pods"] == 7
    assert jan_row["vpo"] == pytest.approx(113 / 7 / 4)

    # FEB
    assert feb_row["units"] == 130
    assert feb_row["buying_stores"] == 5
    assert feb_row["active_pods"] == 7
    assert feb_row["vpo"] == pytest.approx(130 / 7 / 4)

    # MAR
    assert mar_row["units"] == 101
    assert mar_row["buying_stores"] == 6
    assert mar_row["active_pods"] == 8
    assert mar_row["vpo"] == pytest.approx(101 / 8 / 4)



def test_growth_metrics():
    df = load_test_data_6m()
    df_features = add_features(df)

    result = monthly_summary(df_features, df_features)
    result = add_time_metrics_simple(
        result,
        ["units", "new_pods"],
        ["buying_stores"],
        ["vpo"],
        ["active_pods"]
    )

    oct_row = result[result["month_year"].astype(str) == "2025-10"].iloc[0]
    nov_row = result[result["month_year"].astype(str) == "2025-11"].iloc[0]
    dec_row = result[result["month_year"].astype(str) == "2025-12"].iloc[0]
    jan_row = result[result["month_year"].astype(str) == "2026-01"].iloc[0]
    feb_row = result[result["month_year"].astype(str) == "2026-02"].iloc[0]
    mar_row = result[result["month_year"].astype(str) == "2026-03"].iloc[0]

    # base monthly values
    assert oct_row["units"] == 105
    assert nov_row["units"] == 121
    assert dec_row["units"] == 122
    assert jan_row["units"] == 130
    assert feb_row["units"] == 140
    assert mar_row["units"] == 141

    assert oct_row["buying_stores"] == 5
    assert nov_row["buying_stores"] == 5
    assert dec_row["buying_stores"] == 5
    assert jan_row["buying_stores"] == 5
    assert feb_row["buying_stores"] == 5
    assert mar_row["buying_stores"] == 5

    assert oct_row["active_pods"] == 7
    assert nov_row["active_pods"] == 8
    assert dec_row["active_pods"] == 8
    assert jan_row["active_pods"] == 8
    assert feb_row["active_pods"] == 8
    assert mar_row["active_pods"] == 8

    assert oct_row["new_pods"] == 7
    assert nov_row["new_pods"] == 1
    assert dec_row["new_pods"] == 0
    assert jan_row["new_pods"] == 0
    assert feb_row["new_pods"] == 0
    assert mar_row["new_pods"] == 0

    # l1m = previous month
    assert pd.isna(oct_row["units_l1m"])
    assert nov_row["units_l1m"] == 105
    assert dec_row["units_l1m"] == 121
    assert jan_row["units_l1m"] == 122
    assert feb_row["units_l1m"] == 130
    assert mar_row["units_l1m"] == 140

    assert pd.isna(oct_row["units_l1m_pct"])
    assert nov_row["units_l1m_pct"] == pytest.approx((121 - 105) / 105)
    assert dec_row["units_l1m_pct"] == pytest.approx((122 - 121) / 121)
    assert jan_row["units_l1m_pct"] == pytest.approx((130 - 122) / 122)
    assert feb_row["units_l1m_pct"] == pytest.approx((140 - 130) / 130)
    assert mar_row["units_l1m_pct"] == pytest.approx((141 - 140) / 140)

    # 3m = current month + previous 2 months
    assert pd.isna(oct_row["units_3m"])
    assert pd.isna(nov_row["units_3m"])
    assert dec_row["units_3m"] == 105 + 121 + 122
    assert jan_row["units_3m"] == 121 + 122 + 130
    assert feb_row["units_3m"] == 122 + 130 + 140
    assert mar_row["units_3m"] == 130 + 140 + 141

    # l3m = 3-month block immediately before current 3m block
    assert pd.isna(oct_row["units_l3m"])
    assert pd.isna(nov_row["units_l3m"])
    assert pd.isna(dec_row["units_l3m"])
    assert pd.isna(jan_row["units_l3m"])
    assert pd.isna(feb_row["units_l3m"])
    assert mar_row["units_l3m"] == 105 + 121 + 122

    assert pd.isna(oct_row["units_l3m_pct"])
    assert pd.isna(nov_row["units_l3m_pct"])
    assert pd.isna(dec_row["units_l3m_pct"])
    assert pd.isna(jan_row["units_l3m_pct"])
    assert pd.isna(feb_row["units_l3m_pct"])
    assert mar_row["units_l3m_pct"] == pytest.approx(
        ((130 + 140 + 141) - (105 + 121 + 122)) / (105 + 121 + 122)
    )

    # buying stores
    assert mar_row["buying_stores_l1m"] == 5
    assert mar_row["buying_stores_3m"] == 5
    assert mar_row["buying_stores_l3m"] == 5
    assert mar_row["buying_stores_l1m_pct"] == pytest.approx(0)
    assert mar_row["buying_stores_l3m_pct"] == pytest.approx(0)

    # active pods
    # monthly active_pods = cumulative pods at that month
    # 3m / l3m = rolling 3-month sums of monthly active_pods
    assert mar_row["active_pods_l1m"] == 8
    mar_row["active_pods_3m"] == 8
    mar_row["active_pods_l3m"] == 8
    assert mar_row["active_pods_l1m_pct"] == pytest.approx(0)
    assert mar_row["active_pods_l3m_pct"] == pytest.approx(
        ((8) - (8)) / (8)
    )

    # new pods
    assert mar_row["new_pods_l1m"] == 0
    assert mar_row["new_pods_3m"] == 0 + 0 + 0
    assert mar_row["new_pods_l3m"] == 7 + 1 + 0

    # vpo
    # monthly vpo = units / active_pods / 4
    # 3m vpo = units_3m / active_pods_3m / 4
    # l3m vpo = units_l3m / active_pods_l3m / 4
    assert mar_row["vpo"] == pytest.approx(141 / 8 / 4)
    assert mar_row["vpo_l1m"] == pytest.approx(140 / 8 / 4)
    assert mar_row["vpo_3m"] == pytest.approx((130 + 140 + 141) / (8 + 8 + 8) / 4)
    assert mar_row["vpo_l3m"] == pytest.approx((105 + 121 + 122) / (7 + 8 + 8) / 4)

    assert mar_row["vpo_l1m_pct"] == pytest.approx(
        ((141 / 8 / 4) - (140 / 8 / 4)) / (140 / 8 / 4)
    )
    assert mar_row["vpo_l3m_pct"] == pytest.approx(
        (
            ((130 + 140 + 141) / (8 + 8 + 8) / 4)
            - ((105 + 121 + 122) / (7 + 8 + 8) / 4)
        ) / ((105 + 121 + 122) / (7 + 8 + 8) / 4)
    )

def test_reorder_stats():
    df = load_test_data()
    df_features = add_features(df)

    result = calculate_reorder_stats(df_features)

    wf_101 = result[result["coded_customer"] == "WF_FL_101"].iloc[0]
    wf_118 = result[result["coded_customer"] == "WF_FL_118"].iloc[0]
    sp_214 = result[result["coded_customer"] == "SP_FL_214"].iloc[0]
    sp_331 = result[result["coded_customer"] == "SP_FL_331"].iloc[0]
    tfm_087 = result[result["coded_customer"] == "TFM_FL_087"].iloc[0]

    assert wf_101["reorders"] == 2
    assert wf_118["reorders"] == 2
    assert sp_214["reorders"] == 2
    assert sp_331["reorders"] == 2
    assert tfm_087["reorders"] == 2


def test_status_classification():
    df = load_test_data_status()
    df_features = add_features(df)

    result = (
        df_features.groupby("coded_customer", as_index=False)
        .agg(status=("status", "first"))
    )

    assert result[result["coded_customer"] == "NEW_001"]["status"].iloc[0] == "New"
    assert result[result["coded_customer"] == "INACTIVE_001"]["status"].iloc[0] == "Inactive"
    assert result[result["coded_customer"] == "STRUGGLE_001"]["status"].iloc[0] == "Struggling"
    assert result[result["coded_customer"] == "HEALTHY_001"]["status"].iloc[0] == "Healthy"
    assert result[result["coded_customer"] == "HEALTHY_002"]["status"].iloc[0] == "Healthy"
    assert result[result["coded_customer"] == "REVIVED_001"]["status"].iloc[0] == "Revived"


import pandas as pd
import pytest

def test_reorder_rate_growth_metrics():
    df = load_test_data_6m()
    df_features = add_features(df)

    result_reorder = active_store_rate(df_features)
    result_reorder = add_time_metrics_simple(
        result_reorder,
        reorder_metrics=["reorder_rate"]
    )

    oct_row = result_reorder[result_reorder["month_year"].astype(str) == "2025-10"].iloc[0]
    nov_row = result_reorder[result_reorder["month_year"].astype(str) == "2025-11"].iloc[0]
    dec_row = result_reorder[result_reorder["month_year"].astype(str) == "2025-12"].iloc[0]
    jan_row = result_reorder[result_reorder["month_year"].astype(str) == "2026-01"].iloc[0]
    feb_row = result_reorder[result_reorder["month_year"].astype(str) == "2026-02"].iloc[0]
    mar_row = result_reorder[result_reorder["month_year"].astype(str) == "2026-03"].iloc[0]

    # base reorder rate
    assert pd.isna(oct_row["reorder_rate"])
    assert nov_row["reorder_rate"] == pytest.approx(1)
    assert dec_row["reorder_rate"] == pytest.approx(1)
    assert jan_row["reorder_rate"] == pytest.approx(1)
    assert feb_row["reorder_rate"] == pytest.approx(1)
    assert mar_row["reorder_rate"] == pytest.approx(1)

    # l1m
    assert pd.isna(oct_row["reorder_rate_l1m"])
    assert pd.isna(nov_row["reorder_rate_l1m"])
    assert dec_row["reorder_rate_l1m"] == pytest.approx(1)
    assert jan_row["reorder_rate_l1m"] == pytest.approx(1)
    assert feb_row["reorder_rate_l1m"] == pytest.approx(1)
    assert mar_row["reorder_rate_l1m"] == pytest.approx(1)

    # l1m absolute change
    assert pd.isna(oct_row["reorder_rate_l1m_abs"])
    assert pd.isna(nov_row["reorder_rate_l1m_abs"])
    assert dec_row["reorder_rate_l1m_abs"] == pytest.approx(0)
    assert jan_row["reorder_rate_l1m_abs"] == pytest.approx(0)
    assert feb_row["reorder_rate_l1m_abs"] == pytest.approx(0)
    assert mar_row["reorder_rate_l1m_abs"] == pytest.approx(0)

    # 3m
    assert pd.isna(oct_row["reorder_rate_3m"])
    assert pd.isna(nov_row["reorder_rate_3m"])
    assert dec_row["reorder_rate_3m"] == pytest.approx(1)
    assert jan_row["reorder_rate_3m"] == pytest.approx(1)
    assert feb_row["reorder_rate_3m"] == pytest.approx(1)
    assert mar_row["reorder_rate_3m"] == pytest.approx(1)

    # l3m
    assert pd.isna(oct_row["reorder_rate_l3m"])
    assert pd.isna(nov_row["reorder_rate_l3m"])
    assert pd.isna(dec_row["reorder_rate_l3m"])
    assert pd.isna(jan_row["reorder_rate_l3m"])
    assert pd.isna(feb_row["reorder_rate_l3m"])
    assert mar_row["reorder_rate_l3m"] == pytest.approx(1)

    # l3m absolute change
    assert pd.isna(oct_row["reorder_rate_l3m_abs"])
    assert pd.isna(nov_row["reorder_rate_l3m_abs"])
    assert pd.isna(dec_row["reorder_rate_l3m_abs"])
    assert pd.isna(jan_row["reorder_rate_l3m_abs"])
    assert pd.isna(feb_row["reorder_rate_l3m_abs"])
    assert mar_row["reorder_rate_l3m_abs"] == pytest.approx(0)



def test_reorder_rate_sku_level_with_growth():
    df = load_test_data_6m()

    # mimic endpoint logic: filter first, then add features
    df = filter_table(df, sku=["Spicy Beef Ramen"])
    df = add_features(df)

    result_reorder = active_store_rate(df)
    result_reorder = add_time_metrics_simple(
        result_reorder,
        reorder_metrics=["reorder_rate"]
    )

    result_reorder = result_reorder.sort_values("month_year").reset_index(drop=True)

    oct_row = result_reorder[result_reorder["month_year"].astype(str) == "2025-10"].iloc[0]
    nov_row = result_reorder[result_reorder["month_year"].astype(str) == "2025-11"].iloc[0]
    dec_row = result_reorder[result_reorder["month_year"].astype(str) == "2025-12"].iloc[0]
    jan_row = result_reorder[result_reorder["month_year"].astype(str) == "2026-01"].iloc[0]
    feb_row = result_reorder[result_reorder["month_year"].astype(str) == "2026-02"].iloc[0]
    mar_row = result_reorder[result_reorder["month_year"].astype(str) == "2026-03"].iloc[0]

    # base reorder rate
    # denominator = possible reorder events = buying stores - new buyers
    assert pd.isna(oct_row["reorder_rate"])
    assert nov_row["reorder_rate"] == pytest.approx(1)
    assert dec_row["reorder_rate"] == pytest.approx(1)
    assert jan_row["reorder_rate"] == pytest.approx(1)
    assert feb_row["reorder_rate"] == pytest.approx(1)
    assert mar_row["reorder_rate"] == pytest.approx(1)

    # l1m
    assert pd.isna(oct_row["reorder_rate_l1m"])
    assert pd.isna(nov_row["reorder_rate_l1m"])
    assert dec_row["reorder_rate_l1m"] == pytest.approx(1)
    assert jan_row["reorder_rate_l1m"] == pytest.approx(1)
    assert feb_row["reorder_rate_l1m"] == pytest.approx(1)
    assert mar_row["reorder_rate_l1m"] == pytest.approx(1)

    # l1m abs
    assert pd.isna(oct_row["reorder_rate_l1m_abs"])
    assert pd.isna(nov_row["reorder_rate_l1m_abs"])
    assert dec_row["reorder_rate_l1m_abs"] == pytest.approx(0)
    assert jan_row["reorder_rate_l1m_abs"] == pytest.approx(0)
    assert feb_row["reorder_rate_l1m_abs"] == pytest.approx(0)
    assert mar_row["reorder_rate_l1m_abs"] == pytest.approx(0)

    # 3m
    assert pd.isna(oct_row["reorder_rate_3m"])
    assert pd.isna(nov_row["reorder_rate_3m"])
    assert dec_row["reorder_rate_3m"] == pytest.approx(1)
    assert jan_row["reorder_rate_3m"] == pytest.approx(1)
    assert feb_row["reorder_rate_3m"] == pytest.approx(1)
    assert mar_row["reorder_rate_3m"] == pytest.approx(1)

    # l3m
    assert pd.isna(oct_row["reorder_rate_l3m"])
    assert pd.isna(nov_row["reorder_rate_l3m"])
    assert pd.isna(dec_row["reorder_rate_l3m"])
    assert pd.isna(jan_row["reorder_rate_l3m"])
    assert pd.isna(feb_row["reorder_rate_l3m"])
    assert mar_row["reorder_rate_l3m"] == pytest.approx(1)

    # l3m abs
    assert pd.isna(oct_row["reorder_rate_l3m_abs"])
    assert pd.isna(nov_row["reorder_rate_l3m_abs"])
    assert pd.isna(dec_row["reorder_rate_l3m_abs"])
    assert pd.isna(jan_row["reorder_rate_l3m_abs"])
    assert pd.isna(feb_row["reorder_rate_l3m_abs"])
    assert mar_row["reorder_rate_l3m_abs"] == pytest.approx(0)

# EDGE CASES


def test_single_month_store_has_no_reorder():
    df = load_edge_case_test_data()
    df_features = add_features(df)

    single = df_features[df_features["coded_customer"] == "SINGLE_001"]

    assert single["first_store_flag"].sum() == 1
    assert single["reorder_flag"].sum() == 0
    assert str(single["first_month_purchased"].iloc[0]) == "2026-03"
    assert str(single["last_month_purchased"].iloc[0]) == "2026-03"


def test_gap_store_purchase_months_are_correct():
    df = load_edge_case_test_data()
    df_features = add_features(df)

    gap = df_features[df_features["coded_customer"] == "GAP_001"]

    assert str(gap["first_month_purchased"].iloc[0]) == "2026-01"
    assert str(gap["second_to_last_month_purchased"].iloc[0]) == "2026-01"
    assert str(gap["last_month_purchased"].iloc[0]) == "2026-03"
    assert gap["reorder_flag"].sum() == 1


def test_multi_sku_first_store_flag_survives_sku_dropoff():
    df = load_edge_case_test_data()
    df_features = add_features(df)

    multi = df_features[df_features["coded_customer"] == "MULTI_001"]

    # both Jan rows flagged as first-store rows
    assert multi["first_store_flag"].sum() == 2

    # each pod gets one first-pod flag
    assert multi["first_pod_flag"].sum() == 2

    # if filtered to one SKU, store-level first month should still be Jan
    spicy = multi[multi["sku"] == "Spicy Beef Ramen"]
    assert str(spicy["first_month_purchased"].iloc[0]) == "2026-01"
    assert set(spicy.loc[spicy["first_store_flag"], "month_year"].astype(str)) == {"2026-01"}


def test_out_of_order_rows_still_compute_correctly():
    df = load_edge_case_test_data()
    df_features = add_features(df)

    ordered = df_features[df_features["coded_customer"] == "ORDER_001"].sort_values("month_year")

    assert ordered["month_year"].astype(str).tolist() == ["2026-01", "2026-02", "2026-03"]
    assert str(ordered["first_month_purchased"].iloc[0]) == "2026-01"
    assert str(ordered["last_month_purchased"].iloc[0]) == "2026-03"
    assert ordered["reorder_flag"].sum() == 2


def test_zero_unit_row_does_not_break_features():
    df = load_edge_case_test_data()
    df_features = add_features(df)

    zero = df_features[df_features["coded_customer"] == "ZERO_001"].sort_values("month_year")

    assert zero["units"].tolist() == [9, 0, 11]
    assert str(zero["first_month_purchased"].iloc[0]) == "2026-01"
    assert str(zero["last_month_purchased"].iloc[0]) == "2026-03"

#TOTAL REORDER RATE
#L1M REORDER RATE + CHANGE
#L3M REORDER RATE + CHANGE
#STORE HEALTH ASSIGNMENT
#SKU PIE
#CHANNEL MIX
#L1M UNIT GROWTH / L3M UNIT GROWTH BY CHAIN
#VPO BY CHAIN
#AVERAGE SKUS PER STORE
#KPIS
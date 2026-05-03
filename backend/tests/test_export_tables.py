import pandas as pd
import pytest

from backend.exports.ai_ready.export_tables import (
    export_monthly_summary,
    export_summary_by_grain,
    export_store_level_table,
)


def reporting_end():
    return pd.Period(pd.Timestamp.today(), freq="M") - 1


def month_offset(n: int):
    return reporting_end() + n


def month_str(n: int):
    return str(month_offset(n))


def p(month: str):
    return pd.Period(month, freq="M")


def make_export_df(rows):
    df = pd.DataFrame(
        rows,
        columns=[
            "month_year",
            "chain",
            "coded_customer",
            "sku",
            "units",
            "revenue",
        ],
    )

    df["month_year"] = df["month_year"].map(p)
    df["pod_helper"] = df["coded_customer"] + "_" + df["sku"]

    df["city"] = "Miami"
    df["state"] = "FL"
    df["zip"] = "33101"
    df["channel"] = "Natural"
    df["distributor"] = "UNFI"
    df["dc"] = "ATL"
    df["status"] = "Active"

    df["first_month_purchased"] = df.groupby("coded_customer")["month_year"].transform("min")
    df["last_month_purchased"] = df.groupby("coded_customer")["month_year"].transform("max")
    df["first_month_purchased_sku"] = df.groupby("pod_helper")["month_year"].transform("min")

    df["first_store_flag"] = df["month_year"].eq(df["first_month_purchased"])
    df["first_pod_flag"] = df["month_year"].eq(df["first_month_purchased_sku"])
    df["reorder_flag"] = ~df["first_store_flag"]
    df["reorder_flag_pod"] = ~df["first_pod_flag"]

    return df


def assert_close(actual, expected):
    if expected is None or pd.isna(expected):
        assert pd.isna(actual), f"expected NaN, got {actual}"
    else:
        assert actual == pytest.approx(expected)


def row_for(df, **filters):
    result = df.copy()
    for col, val in filters.items():
        result = result[result[col] == val]
    assert len(result) == 1
    return result.iloc[0]


def test_summary_by_chain_uses_full_missing_month_spine_and_shifted_l3m_pct():
    df = make_export_df(
        [
            (month_str(-6), "A", "S1", "SKU1", 10, 100),
            (month_str(-4), "A", "S1", "SKU1", 30, 300),
            (month_str(-3), "A", "S1", "SKU1", 40, 400),
            (month_str(0), "A", "S1", "SKU1", 70, 700),
            (month_str(1), "A", "S1", "SKU1", 80, 800),
        ]
    )

    result = export_summary_by_grain(df, "chain")
    a = row_for(result, chain="A")

    assert a["units"] == 230
    assert a["revenue"] == 2300

    assert a["units_3m"] == 70
    assert a["revenue_3m"] == 700

    assert_close(a["units_l3m_pct"], 0)
    assert_close(a["revenue_l3m_pct"], 0)


def test_summary_by_chain_l3m_pct_is_nan_when_group_has_fewer_than_6_spine_rows():
    df = make_export_df(
        [
            (month_str(-3), "B", "S2", "SKU1", 10, 100),
            (month_str(-1), "B", "S2", "SKU1", 20, 200),
            (month_str(0), "B", "S2", "SKU1", 30, 300),
        ]
    )

    result = export_summary_by_grain(df, "chain")
    b = row_for(result, chain="B")

    assert b["units_3m"] == 50
    assert b["revenue_3m"] == 500

    assert pd.isna(b["units_l3m_pct"])
    assert pd.isna(b["revenue_l3m_pct"])


def test_summary_by_chain_handles_18_month_history_and_missing_middle_months():
    rows = []

    missing_offsets = {-13, -7, -3}

    for i, offset in enumerate(range(-17, 1), start=1):
        if offset in missing_offsets:
            continue

        rows.append(
            (
                month_str(offset),
                "Long",
                "S3",
                "SKU1",
                i,
                i * 10,
            )
        )

    df = make_export_df(rows)
    result = export_summary_by_grain(df, "chain")
    r = row_for(result, chain="Long")

    # Last 3 row-months at reporting end: -2, -1, 0.
    # Offset -3 is missing, but it is not in the current 3m window.
    current_3m_units = 16 + 17 + 18

    # Shifted l3m comes from 3 rows above: -5, -4, -3.
    # Offset -3 is missing, so contributes 0.
    prior_3m_units = 13 + 14 + 0

    assert r["units_3m"] == current_3m_units
    assert r["revenue_3m"] == current_3m_units * 10

    assert_close(
        r["units_l3m_pct"],
        (current_3m_units - prior_3m_units) / prior_3m_units,
    )


def test_store_level_table_excludes_current_month_from_3m_metrics_but_totals_include_it():
    df = make_export_df(
        [
            (month_str(-6), "A", "Store 1", "SKU1", 10, 100),
            (month_str(-4), "A", "Store 1", "SKU1", 30, 300),
            (month_str(-3), "A", "Store 1", "SKU1", 40, 400),
            (month_str(0), "A", "Store 1", "SKU1", 70, 700),
            (month_str(1), "A", "Store 1", "SKU1", 80, 800),
        ]
    )

    result = export_store_level_table(df, "coded_customer")
    store = row_for(result, coded_customer="Store 1")

    assert store["units"] == 230
    assert store["revenue"] == 2300

    assert store["units_3m"] == 70
    assert store["revenue_3m"] == 700

    assert_close(store["units_l3m_pct"], 0)
    assert_close(store["revenue_l3m_pct"], 0)


def test_monthly_summary_keeps_missing_months_in_spine_for_additive_3m():
    df = make_export_df(
        [
            (month_str(-6), "A", "S1", "SKU1", 10, 100),
            (month_str(-4), "A", "S1", "SKU1", 30, 300),
            (month_str(-3), "A", "S1", "SKU1", 40, 400),
            (month_str(0), "A", "S1", "SKU1", 70, 700),
            (month_str(1), "A", "S1", "SKU1", 80, 800),
        ]
    )

    result = export_monthly_summary(df)

    latest = row_for(result, month_year=reporting_end())

    assert latest["units_3m"] == 70
    assert latest["revenue_3m"] == 700

    assert_close(latest["units_l3m_pct"], 0)
    assert_close(latest["revenue_l3m_pct"], 0)


def test_monthly_summary_zero_sales_with_active_pods_has_zero_vpo_not_nan():
    df = make_export_df(
        [
            (month_str(-6), "A", "S1", "SKU1", 10, 100),
            (month_str(-5), "A", "S1", "SKU1", 10, 100),
            (month_str(-4), "A", "S1", "SKU1", 10, 100),
            (month_str(0), "A", "S1", "SKU1", 0, 0),
        ]
    )

    result = export_monthly_summary(df)
    latest = row_for(result, month_year=reporting_end())

    assert latest["units"] == 0
    assert latest["units_3m"] == 0
    assert latest["vpo_3m"] == 0


def test_active_pods_is_last_6_months_not_all_time_in_summary_by_grain():
    df = make_export_df(
        [
            (month_str(-7), "A", "Old Store", "SKU1", 10, 100),
            (month_str(-4), "A", "Fresh Store", "SKU1", 20, 200),
            (month_str(0), "A", "Fresh Store", "SKU1", 30, 300),
        ]
    )

    result = export_summary_by_grain(df, "chain")
    a = row_for(result, chain="A")

    assert a["all_time_pods"] == 2
    assert a["active_pods"] == 1


def test_reorder_rate_is_nan_when_there_are_no_reorder_opportunities():
    df = make_export_df(
        [
            (month_str(-2), "A", "New Store 1", "SKU1", 10, 100),
            (month_str(-1), "A", "New Store 2", "SKU1", 20, 200),
            (month_str(0), "A", "New Store 3", "SKU1", 30, 300),
        ]
    )

    result = export_summary_by_grain(df, "chain")
    a = row_for(result, chain="A")

    assert pd.isna(a["reorder_rate"])
    assert pd.isna(a["reorder_rate_3m"]) or a["reorder_rate_3m"] == 0

def test_single_order_store_export_handles_sparse_history():
    df = make_export_df(
        [
            (month_str(-2), "A", "Single Store", "SKU1", 20, 200),
        ]
    )

    result = export_summary_by_grain(df, "chain")
    row = row_for(result, chain="A")

    assert row["revenue"] == 200
    assert row["units"] == 20
    assert row["all_time_pods"] == 1
    assert row["active_pods"] == 1
    assert row["buying_stores"] == 1

    # Latest 3m window = -2, -1, 0
    assert row["revenue_3m"] == 200
    assert row["units_3m"] == 20
    assert row["new_pods_3m"] == 1
    assert row["buying_stores_3m"] == 1

    # Fewer than 6 spine rows, so l3m pct should be NaN
    assert pd.isna(row["revenue_l3m_pct"])
    assert pd.isna(row["units_l3m_pct"])
    assert pd.isna(row["vpo_l3m_pct"])


def test_dropoff_store_export_keeps_zero_latest_3m_but_negative_l3m_pct():
    df = make_export_df(
        [
            # Store orders early, then goes silent for latest 3 months
            (month_str(-6), "A", "Dropoff Store", "SKU1", 10, 100),
            (month_str(-5), "A", "Dropoff Store", "SKU1", 15, 150),
            (month_str(-4), "A", "Dropoff Store", "SKU1", 20, 200),

            # Healthy store continues ordering
            (month_str(-6), "A", "Healthy Store", "SKU1", 10, 100),
            (month_str(-5), "A", "Healthy Store", "SKU1", 10, 100),
            (month_str(-4), "A", "Healthy Store", "SKU1", 10, 100),
            (month_str(-3), "A", "Healthy Store", "SKU1", 10, 100),
            (month_str(-2), "A", "Healthy Store", "SKU1", 10, 100),
            (month_str(-1), "A", "Healthy Store", "SKU1", 10, 100),
            (month_str(0), "A", "Healthy Store", "SKU1", 10, 100),
        ]
    )

    store_result = export_store_level_table(df, "coded_customer")

    dropoff = row_for(store_result, coded_customer="Dropoff Store")
    healthy = row_for(store_result, coded_customer="Healthy Store")

    assert dropoff["revenue"] == 450
    assert dropoff["units"] == 45

    # Latest 3m = -2, -1, 0 where dropoff store has no orders
    assert dropoff["revenue_3m"] == 0
    assert dropoff["units_3m"] == 0
    assert pd.isna(dropoff["vpo_3m"])

    # Prior shifted 3m = -5, -4, -3 = 150 + 200 + 0 = 350
    assert_close(dropoff["revenue_l3m_pct"], (0 - 350) / 350)
    assert_close(dropoff["units_l3m_pct"], (0 - 35) / 35)

    assert healthy["revenue_3m"] == 300
    assert healthy["units_3m"] == 30
    assert healthy["vpo_3m"] > 0


def test_export_summary_by_multi_grain_chain_channel():
    df = make_export_df(
        [
            # A / Natural has enough history for l3m
            (month_str(-6), "A", "S1", "SKU1", 10, 100),
            (month_str(-5), "A", "S1", "SKU1", 10, 100),
            (month_str(-4), "A", "S1", "SKU1", 10, 100),
            (month_str(-3), "A", "S1", "SKU1", 10, 100),
            (month_str(-2), "A", "S1", "SKU1", 10, 100),
            (month_str(-1), "A", "S1", "SKU1", 10, 100),
            (month_str(0), "A", "S1", "SKU1", 10, 100),

            # B / Mass starts later, fewer than 6 spine rows
            (month_str(-3), "B", "S2", "SKU1", 20, 200),
            (month_str(-2), "B", "S2", "SKU1", 20, 200),
            (month_str(-1), "B", "S2", "SKU1", 20, 200),
            (month_str(0), "B", "S2", "SKU1", 20, 200),
        ]
    )

    df.loc[df["chain"] == "A", "channel"] = "Natural"
    df.loc[df["chain"] == "B", "channel"] = "Mass"

    result = export_summary_by_grain(df, ["chain", "channel"])

    a = row_for(result, chain="A", channel="Natural")
    b = row_for(result, chain="B", channel="Mass")

    assert a["revenue"] == 700
    assert a["units"] == 70
    assert a["revenue_3m"] == 300
    assert a["units_3m"] == 30
    assert_close(a["revenue_l3m_pct"], (300 - 300) / 300)
    assert_close(a["units_l3m_pct"], (30 - 30) / 30)

    assert b["revenue"] == 800
    assert b["units"] == 80
    assert b["revenue_3m"] == 600
    assert b["units_3m"] == 60

    # B only has 4 spine rows, so no l3m pct
    assert pd.isna(b["revenue_l3m_pct"])
    assert pd.isna(b["units_l3m_pct"])

def test_new_store_started_in_latest_month_has_nan_3m_and_l3m():
    df = make_export_df(
        [
            (month_str(0), "A", "Brand New Store", "SKU1", 50, 500),
        ]
    )

    store_result = export_store_level_table(df, "coded_customer")
    grain_result = export_summary_by_grain(df, "chain")

    store = row_for(store_result, coded_customer="Brand New Store")
    chain = row_for(grain_result, chain="A")

    assert store["revenue"] == 500
    assert store["units"] == 50
    assert store["reorders"] == 0

    assert pd.isna(store["revenue_3m"])
    assert pd.isna(store["units_3m"])
    assert pd.isna(store["vpo_3m"])

    assert pd.isna(store["revenue_l3m_pct"])
    assert pd.isna(store["units_l3m_pct"])
    assert pd.isna(store["vpo_l3m_pct"])

    assert chain["revenue"] == 500
    assert chain["units"] == 50
    assert pd.isna(chain["revenue_3m"])
    assert pd.isna(chain["units_3m"])
    assert pd.isna(chain["revenue_l3m_pct"])
    assert pd.isna(chain["units_l3m_pct"])

def test_store_level_reorders_do_not_double_count_multiple_skus_same_month():
    df = make_export_df(
        [
            (month_str(-2), "A", "Store 1", "SKU1", 10, 100),
            (month_str(-1), "A", "Store 1", "SKU1", 10, 100),
            (month_str(-1), "A", "Store 1", "SKU2", 5, 50),
            (month_str(0), "A", "Store 1", "SKU1", 10, 100),
            (month_str(0), "A", "Store 1", "SKU2", 5, 50),
        ]
    )

    result = export_store_level_table(df, "coded_customer")
    store = row_for(result, coded_customer="Store 1")

    assert store["skus_carrying"] == 2

    # Reorders should count store-months, not SKU rows.
    # First month is not reorder. Months -1 and 0 are reorder months.
    assert store["reorders"] == 2

    assert store["revenue"] == 400
    assert store["units"] == 40

def test_store_level_respects_additional_grain():
    df = make_export_df(
        [
            (month_str(-2), "A", "Store 1", "SKU1", 10, 100),
            (month_str(-1), "A", "Store 1", "SKU1", 10, 100),
            (month_str(0), "A", "Store 1", "SKU1", 10, 100),

            # same store but different chain (edge case)
            (month_str(-2), "B", "Store 1", "SKU1", 5, 50),
            (month_str(-1), "B", "Store 1", "SKU1", 5, 50),
            (month_str(0), "B", "Store 1", "SKU1", 5, 50),
        ]
    )

    result = export_store_level_table(df, ["chain"])

    # should split into two rows
    assert len(result) == 2

    a = row_for(result, coded_customer="Store 1", chain="A")
    b = row_for(result, coded_customer="Store 1", chain="B")

    assert a["revenue"] == 300
    assert b["revenue"] == 150

def test_store_level_additional_grain_does_not_duplicate_normal_rows():
    df = make_export_df(
        [
            (month_str(-2), "A", "Store 1", "SKU1", 10, 100),
            (month_str(-1), "A", "Store 1", "SKU1", 20, 200),
            (month_str(0), "A", "Store 1", "SKU1", 30, 300),

            (month_str(-2), "A", "Store 2", "SKU1", 40, 400),
            (month_str(-1), "A", "Store 2", "SKU1", 50, 500),
            (month_str(0), "A", "Store 2", "SKU1", 60, 600),
        ]
    )

    result = export_store_level_table(df, ["chain"])

    assert len(result) == 2

    s1 = row_for(result, coded_customer="Store 1", chain="A")
    s2 = row_for(result, coded_customer="Store 2", chain="A")

    assert s1["revenue"] == 600
    assert s1["units"] == 60
    assert s1["revenue_3m"] == 600
    assert s1["units_3m"] == 60

    assert s2["revenue"] == 1500
    assert s2["units"] == 150
    assert s2["revenue_3m"] == 1500
    assert s2["units_3m"] == 150
import pandas as pd
import pandas.testing as pdt

from backend.metrics.metric_calculators import (
    calculate_vpo, 
    calculate_reorder_rate,
    calculate_units,
    calculate_buying_stores,
    calculate_new_pods
)


# -----------------------------------------
# COMPLEX FIXTURE
# -----------------------------------------
def build_complex_df():
    data = [
        # -------------------
        # GROUP A (chain A)
        # -------------------
        # Store A1 (pre-window activation)
        ("A", "A1", "P1", "2025-11", 10, 1, 1, 0),
        ("A", "A1", "P1", "2026-01", 5, 0, 0, 1),
        ("A", "A1", "P1", "2026-03", 5, 0, 0, 1),

        # Store A2 (activates in window)
        ("A", "A2", "P2", "2026-01", 10, 1, 1, 0),
        ("A", "A2", "P2", "2026-02", 5, 0, 0, 1),

        # -------------------
        # GROUP B (chain B)
        # -------------------
        # Store B1 (missing middle month)
        ("B", "B1", "P3", "2026-01", 10, 1, 1, 0),
        ("B", "B1", "P3", "2026-03", 10, 0, 0, 1),

        # Store B2 (never orders in window but exists before)
        ("B", "B2", "P4", "2025-12", 10, 1, 1, 0),

        # -------------------
        # GROUP C (chain C)
        # -------------------
        # Only activates AFTER window → should NOT be included
        ("C", "C1", "P5", "2026-05", 10, 1, 1, 0),
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


# -----------------------------------------
# VPO TEST
# -----------------------------------------
def test_calculate_vpo_complex():
    df_full = build_complex_df()

    start = pd.Period("2026-01", freq="M")
    end = pd.Period("2026-03", freq="M")

    df_filtered = df_full[
        (df_full["month_year"] >= start) &
        (df_full["month_year"] <= end)
    ]

    result = calculate_vpo(
        df_filtered=df_filtered,
        df_full=df_full,
        group_cols=["chain"],
        selected_years=[2026],
        selected_months=[
            pd.Period("2026-01", freq="M"),
            pd.Period("2026-02", freq="M"),
            pd.Period("2026-03", freq="M"),
        ],
    ).sort_values("chain").reset_index(drop=True)

    expected = pd.DataFrame(
        {
            "chain": ["A", "B"],
            "vpo": [25 / 6 / 4, 20 / 6 / 4],
        }
    )

    pdt.assert_frame_equal(result, expected, check_exact=False, rtol=1e-9)


# -----------------------------------------
# REORDER RATE TEST
# -----------------------------------------
def test_calculate_reorder_rate_complex():
    df_full = build_complex_df()

    start = pd.Period("2026-01", freq="M")
    end = pd.Period("2026-03", freq="M")

    df_filtered = df_full[
        (df_full["month_year"] >= start) &
        (df_full["month_year"] <= end)
    ]

    result = calculate_reorder_rate(
        df_filtered=df_filtered,
        df_full=df_full,
        group_cols=["chain"],
        selected_years=[2026],
        selected_months=[
            pd.Period("2026-01", freq="M"),
            pd.Period("2026-02", freq="M"),
            pd.Period("2026-03", freq="M"),
        ],
    ).sort_values("chain").reset_index(drop=True)

    expected = pd.DataFrame(
        {
            "chain": ["A", "B"],
            "reorder_rate": [3 / 5, 1 / 5],
        }
    )

    pdt.assert_frame_equal(result, expected, check_exact=False, rtol=1e-9)


# ─────────────────────────────────────────────
# 1. All stores activate in the window
# ─────────────────────────────────────────────
def build_all_in_window_df():
    data = [
        ("A", "A1", "2026-01", 0),
        ("A", "A1", "2026-02", 1),
        ("A", "A2", "2026-02", 0),
        ("A", "A2", "2026-03", 1),
    ]
    df = pd.DataFrame(data, columns=["chain", "coded_customer", "month_year", "reorder_flag"])
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    return df

def test_all_stores_activate_in_window():
    df_full = build_all_in_window_df()
    df_filtered = df_full[(df_full["month_year"] >= pd.Period("2026-01", freq="M")) & (df_full["month_year"] <= pd.Period("2026-03", freq="M"))]

    result = calculate_reorder_rate(
        df_filtered,
        df_full,
        ["chain"],
        selected_years=[2026],
        selected_months=[
            pd.Period("2026-01", freq="M"),
            pd.Period("2026-02", freq="M"),
            pd.Period("2026-03", freq="M"),
        ],
    )

    # A1: first_month=Jan, opportunities=Feb,Mar=2, reorders=Feb=1
    # A2: first_month=Feb, opportunities=Mar=1, reorders=Mar=1
    # total: 2 reorders / 3 opportunities
    expected = pd.DataFrame({"chain": ["A"], "reorder_rate": [2 / 3]})
    pdt.assert_frame_equal(result.reset_index(drop=True), expected, check_exact=False, rtol=1e-9)


# ─────────────────────────────────────────────
# 2. Single month window
# ─────────────────────────────────────────────
def build_single_month_df():
    data = [
        ("A", "A1", "2025-12", 0),
        ("A", "A2", "2026-01", 0),
    ]
    df = pd.DataFrame(data, columns=["chain", "coded_customer", "month_year", "reorder_flag"])
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    return df

def test_single_month_window():
    df_full = build_single_month_df()
    df_filtered = df_full[df_full["month_year"] == pd.Period("2026-01", freq="M")]

    result = calculate_reorder_rate(
        df_filtered,
        df_full,
        ["chain"],
        selected_years=[2026],
        selected_months=[pd.Period("2026-01", freq="M")],
    )

    # A1: first_month=Dec, opportunity=Jan=1, reorder_flag=0 → 0 reorders
    # A2: first_month=Jan, 0 opportunities
    # rate = 0 / 1
    expected = pd.DataFrame({"chain": ["A"], "reorder_rate": [0.0]})
    pdt.assert_frame_equal(result.reset_index(drop=True), expected, check_exact=False, rtol=1e-9)


# ─────────────────────────────────────────────
# 3. 100% reorder rate
# ─────────────────────────────────────────────
def build_perfect_reorder_df():
    data = [
        ("A", "A1", "2025-12", 0),
        ("A", "A1", "2026-01", 1),
        ("A", "A1", "2026-02", 1),
        ("A", "A2", "2025-12", 0),
        ("A", "A2", "2026-01", 1),
        ("A", "A2", "2026-02", 1),
    ]
    df = pd.DataFrame(data, columns=["chain", "coded_customer", "month_year", "reorder_flag"])
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    return df

def test_perfect_reorder_rate():
    df_full = build_perfect_reorder_df()
    df_filtered = df_full[(df_full["month_year"] >= pd.Period("2026-01", freq="M")) & (df_full["month_year"] <= pd.Period("2026-02", freq="M"))]

    result = calculate_reorder_rate(
        df_filtered,
        df_full,
        ["chain"],
        selected_years=[2026],
        selected_months=[
            pd.Period("2026-01", freq="M"),
            pd.Period("2026-02", freq="M"),
        ],
    )

    # each store: first_month=Dec, opportunities=Jan,Feb=2, reorders=2
    # total: 4 / 4
    expected = pd.DataFrame({"chain": ["A"], "reorder_rate": [1.0]})
    pdt.assert_frame_equal(result.reset_index(drop=True), expected, check_exact=False, rtol=1e-9)


# ─────────────────────────────────────────────
# 4. No reorders in window, opportunities exist
# ─────────────────────────────────────────────
def build_no_reorders_df():
    data = [
        ("A", "A1", "2025-12", 0),
        ("A", "A1", "2026-01", 0),
        ("A", "A1", "2026-02", 0),
    ]
    df = pd.DataFrame(data, columns=["chain", "coded_customer", "month_year", "reorder_flag"])
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    return df

def test_no_reorders_in_window():
    df_full = build_no_reorders_df()
    df_filtered = df_full[(df_full["month_year"] >= pd.Period("2026-01", freq="M")) & (df_full["month_year"] <= pd.Period("2026-02", freq="M"))]

    result = calculate_reorder_rate(
        df_filtered,
        df_full,
        ["chain"],
        selected_years=[2026],
        selected_months=[
            pd.Period("2026-01", freq="M"),
            pd.Period("2026-02", freq="M"),
        ],
    )

    # A1: first_month=Dec, opportunities=Jan,Feb=2, reorders=0
    # rate = 0 / 2
    expected = pd.DataFrame({"chain": ["A"], "reorder_rate": [0.0]})
    pdt.assert_frame_equal(result.reset_index(drop=True), expected, check_exact=False, rtol=1e-9)


# ─────────────────────────────────────────────
# 5. Store in filtered window but reorder_flag always 0
# ─────────────────────────────────────────────
def build_no_flag_df():
    data = [
        ("A", "A1", "2025-12", 0),
        ("A", "A1", "2026-01", 0),
        ("A", "A1", "2026-02", 0),
    ]
    df = pd.DataFrame(data, columns=["chain", "coded_customer", "month_year", "reorder_flag"])
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    return df

def test_store_in_window_no_reorder_flag():
    df_full = build_no_flag_df()
    df_filtered = df_full[(df_full["month_year"] >= pd.Period("2026-01", freq="M")) & (df_full["month_year"] <= pd.Period("2026-02", freq="M"))]

    result = calculate_reorder_rate(
        df_filtered,
        df_full,
        ["chain"],
        selected_years=[2026],
        selected_months=[
            pd.Period("2026-01", freq="M"),
            pd.Period("2026-02", freq="M"),
        ],
    )

    expected = pd.DataFrame({"chain": ["A"], "reorder_rate": [0.0]})
    pdt.assert_frame_equal(result.reset_index(drop=True), expected, check_exact=False, rtol=1e-9)


# ─────────────────────────────────────────────
# 6. No group_cols
# ─────────────────────────────────────────────
def build_no_group_cols_df():
    data = [
        ("A1", "2025-12", 0),
        ("A1", "2026-01", 1),
        ("A1", "2026-02", 1),
        ("B1", "2026-01", 0),
        ("B1", "2026-02", 1),
    ]
    df = pd.DataFrame(data, columns=["coded_customer", "month_year", "reorder_flag"])
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    return df

def test_no_group_cols():
    df_full = build_no_group_cols_df()
    df_filtered = df_full[(df_full["month_year"] >= pd.Period("2026-01", freq="M")) & (df_full["month_year"] <= pd.Period("2026-02", freq="M"))]

    result = calculate_reorder_rate(
        df_filtered,
        df_full,
        [],
        selected_years=[2026],
        selected_months=[
            pd.Period("2026-01", freq="M"),
            pd.Period("2026-02", freq="M"),
        ],
    )

    # A1: first=Dec, opps=Jan,Feb=2, reorders=2
    # B1: first=Jan, opps=Feb=1, reorders=1
    # total: 3 / 3
    expected = pd.DataFrame({"reorder_rate": [1.0]})
    pdt.assert_frame_equal(result.reset_index(drop=True), expected, check_exact=False, rtol=1e-9)


# ─────────────────────────────────────────────
# 7. Entire chain has no rows in df_filtered
# ─────────────────────────────────────────────
def build_chain_absent_from_window_df():
    data = [
        ("A", "A1", "2025-11", 0),
        ("B", "B1", "2025-12", 0),
        ("B", "B1", "2026-01", 1),
        ("B", "B1", "2026-02", 1),
    ]
    df = pd.DataFrame(data, columns=["chain", "coded_customer", "month_year", "reorder_flag"])
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    return df

def test_chain_absent_from_filtered_window():
    df_full = build_chain_absent_from_window_df()
    df_filtered = df_full[(df_full["month_year"] >= pd.Period("2026-01", freq="M")) & (df_full["month_year"] <= pd.Period("2026-02", freq="M"))]

    result = calculate_reorder_rate(
        df_filtered,
        df_full,
        ["chain"],
        selected_years=[2026],
        selected_months=[
            pd.Period("2026-01", freq="M"),
            pd.Period("2026-02", freq="M"),
        ],
    )

    # Chain A: first=Nov, opps=Jan,Feb=2, reorders=0 → rate=0/2
    # Chain B: first=Dec, opps=Jan,Feb=2, reorders=2 → rate=2/2
    expected = pd.DataFrame({
        "chain": ["A", "B"],
        "reorder_rate": [0.0, 1.0],
    })
    pdt.assert_frame_equal(
        result.sort_values("chain").reset_index(drop=True),
        expected,
        check_exact=False,
        rtol=1e-9,
    )


# ─────────────────────────────────────────────
# 8. Multiple SKUs per store per month
# ─────────────────────────────────────────────
def build_multi_sku_df():
    data = [
        ("A", "A1", "P1", "2025-12", 0),
        ("A", "A1", "P1", "2026-01", 1),
        ("A", "A1", "P2", "2026-01", 0),
    ]
    df = pd.DataFrame(data, columns=["chain", "coded_customer", "pod_helper", "month_year", "reorder_flag"])
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    return df

def test_multi_sku_counts_as_one_repeat_buyer():
    df_full = build_multi_sku_df()
    df_filtered = df_full[df_full["month_year"] == pd.Period("2026-01", freq="M")]

    result = calculate_reorder_rate(
        df_filtered,
        df_full,
        ["chain"],
        selected_years=[2026],
        selected_months=[pd.Period("2026-01", freq="M")],
    )

    # A1: first=Dec, opp=Jan=1, repeat_buyer=max(1,0)=1
    # rate = 1 / 1
    expected = pd.DataFrame({"chain": ["A"], "reorder_rate": [1.0]})
    pdt.assert_frame_equal(result.reset_index(drop=True), expected, check_exact=False, rtol=1e-9)


# ─────────────────────────────────────────────
# 9. Store activates exactly on end_month
# ─────────────────────────────────────────────
def build_activate_on_end_month_df():
    data = [
        ("A", "A1", "2025-12", 0),
        ("A", "A1", "2026-01", 1),
        ("A", "A2", "2026-03", 0),
    ]
    df = pd.DataFrame(data, columns=["chain", "coded_customer", "month_year", "reorder_flag"])
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    return df

def test_store_activates_on_end_month():
    df_full = build_activate_on_end_month_df()
    df_filtered = df_full[(df_full["month_year"] >= pd.Period("2026-01", freq="M")) & (df_full["month_year"] <= pd.Period("2026-03", freq="M"))]

    result = calculate_reorder_rate(
        df_filtered,
        df_full,
        ["chain"],
        selected_years=[2026],
        selected_months=[
            pd.Period("2026-01", freq="M"),
            pd.Period("2026-02", freq="M"),
            pd.Period("2026-03", freq="M"),
        ],
    )

    # A1: first=Dec, opps=Jan,Feb,Mar=3, reorders=Jan=1
    # A2: first=Mar, opps=0 (no month > Mar in window)
    # rate = 1 / 3
    expected = pd.DataFrame({"chain": ["A"], "reorder_rate": [1 / 3]})
    pdt.assert_frame_equal(result.reset_index(drop=True), expected, check_exact=False, rtol=1e-9)

# -----------------------------------------
# SIMPLE METRIC TESTS
# -----------------------------------------

def test_calculate_units():
    df = build_complex_df()

    result = (
        calculate_units(df, ["chain"])
        .sort_values("chain")
        .reset_index(drop=True)
    )

    expected = pd.DataFrame({
        "chain": ["A", "B", "C"],
        "units": [35, 30, 10],
    })

    pdt.assert_frame_equal(result, expected)


def test_calculate_buying_stores():
    df = build_complex_df()

    result = (
        calculate_buying_stores(df, ["chain"])
        .sort_values("chain")
        .reset_index(drop=True)
    )

    expected = pd.DataFrame({
        "chain": ["A", "B", "C"],
        "buying_stores": [2, 2, 1],
    })

    pdt.assert_frame_equal(result, expected)


def test_calculate_new_pods():
    df = build_complex_df()

    result = (
        calculate_new_pods(df, ["chain"])
        .sort_values("chain")
        .reset_index(drop=True)
    )

    expected = pd.DataFrame({
        "chain": ["A", "B", "C"],
        "new_pods": [2, 2, 1],
    })

    pdt.assert_frame_equal(result, expected)
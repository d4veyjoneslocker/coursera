import pandas as pd

from backend.insights.build_what_changed import (
    build_what_changed,
    detect_top_sku_change,
    detect_top_chain_change,
    detect_new_store_expansion,
    detect_sku_new_states,
)


def make_df(rows):
    df = pd.DataFrame(rows)
    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    return df


def test_top_sku_change_detects_new_number_one():
    df = make_df([
        {"month_year": "2026-04", "sku": "SKU A", "chain": "Chain 1", "coded_customer": "S1", "state": "FL", "units": 100},
        {"month_year": "2026-04", "sku": "SKU B", "chain": "Chain 1", "coded_customer": "S2", "state": "FL", "units": 50},
        {"month_year": "2026-05", "sku": "SKU A", "chain": "Chain 1", "coded_customer": "S1", "state": "FL", "units": 80},
        {"month_year": "2026-05", "sku": "SKU B", "chain": "Chain 1", "coded_customer": "S2", "state": "FL", "units": 150},
    ])

    result = detect_top_sku_change(df, pd.Period("2026-05", freq="M"), pd.Period("2026-04", freq="M"))

    assert result is not None
    assert result["type"] == "state_change"
    assert result["parts"][0]["value"] == "SKU B"
    assert result["drilldown"]["href"] == "/insights/sku_rankings"


def test_top_sku_change_returns_none_when_same_top_sku():
    df = make_df([
        {"month_year": "2026-04", "sku": "SKU A", "chain": "Chain 1", "coded_customer": "S1", "state": "FL", "units": 100},
        {"month_year": "2026-04", "sku": "SKU B", "chain": "Chain 1", "coded_customer": "S2", "state": "FL", "units": 50},
        {"month_year": "2026-05", "sku": "SKU A", "chain": "Chain 1", "coded_customer": "S1", "state": "FL", "units": 120},
        {"month_year": "2026-05", "sku": "SKU B", "chain": "Chain 1", "coded_customer": "S2", "state": "FL", "units": 60},
    ])

    result = detect_top_sku_change(df, pd.Period("2026-05", freq="M"), pd.Period("2026-04", freq="M"))

    assert result is None


def test_top_chain_change_detects_new_number_one():
    df = make_df([
        {"month_year": "2026-04", "sku": "SKU A", "chain": "Whole Foods", "coded_customer": "S1", "state": "FL", "units": 100},
        {"month_year": "2026-04", "sku": "SKU A", "chain": "Sprouts", "coded_customer": "S2", "state": "FL", "units": 50},
        {"month_year": "2026-05", "sku": "SKU A", "chain": "Whole Foods", "coded_customer": "S1", "state": "FL", "units": 80},
        {"month_year": "2026-05", "sku": "SKU A", "chain": "Sprouts", "coded_customer": "S2", "state": "FL", "units": 150},
    ])

    result = detect_top_chain_change(df, pd.Period("2026-05", freq="M"), pd.Period("2026-04", freq="M"))

    assert result is not None
    assert result["parts"][0]["value"] == "Sprouts"


def test_new_store_expansion_detects_first_time_sku_buyers():
    df = make_df([
        {"month_year": "2026-04", "sku": "SKU A", "chain": "Chain 1", "coded_customer": "S1", "state": "FL", "units": 10},
        {"month_year": "2026-05", "sku": "SKU A", "chain": "Chain 1", "coded_customer": "S1", "state": "FL", "units": 10},
        {"month_year": "2026-05", "sku": "SKU A", "chain": "Chain 1", "coded_customer": "S2", "state": "FL", "units": 10},
        {"month_year": "2026-05", "sku": "SKU A", "chain": "Chain 1", "coded_customer": "S3", "state": "FL", "units": 10},
        {"month_year": "2026-05", "sku": "SKU A", "chain": "Chain 1", "coded_customer": "S4", "state": "FL", "units": 10},
    ])

    result = detect_new_store_expansion(df, pd.Period("2026-05", freq="M"), pd.Period("2026-04", freq="M"))

    assert result is not None
    assert result["parts"][0]["value"] == "SKU A"
    assert "3 new buying stores" in result["parts"][1]["value"]
    assert result["drilldown"]["href"] == "/insights/new_store_distribution?sku=SKU A"


def test_new_store_expansion_returns_none_under_threshold():
    df = make_df([
        {"month_year": "2026-04", "sku": "SKU A", "chain": "Chain 1", "coded_customer": "S1", "state": "FL", "units": 10},
        {"month_year": "2026-05", "sku": "SKU A", "chain": "Chain 1", "coded_customer": "S1", "state": "FL", "units": 10},
        {"month_year": "2026-05", "sku": "SKU A", "chain": "Chain 1", "coded_customer": "S2", "state": "FL", "units": 10},
    ])

    result = detect_new_store_expansion(df, pd.Period("2026-05", freq="M"), pd.Period("2026-04", freq="M"))

    assert result is None


def test_sku_new_states_detects_true_new_states_not_prior_month_gap():
    df = make_df([
        {"month_year": "2026-03", "sku": "SKU A", "chain": "Chain 1", "coded_customer": "S1", "state": "FL", "units": 10},
        {"month_year": "2026-04", "sku": "SKU A", "chain": "Chain 1", "coded_customer": "S2", "state": "GA", "units": 10},
        {"month_year": "2026-05", "sku": "SKU A", "chain": "Chain 1", "coded_customer": "S3", "state": "FL", "units": 10},
        {"month_year": "2026-05", "sku": "SKU A", "chain": "Chain 1", "coded_customer": "S4", "state": "TX", "units": 10},
    ])

    result = detect_sku_new_states(df, pd.Period("2026-05", freq="M"), pd.Period("2026-04", freq="M"))

    assert result is not None
    assert result["parts"][0]["value"] == "SKU A"
    assert "1 new state" in result["parts"][1]["value"]
    assert "TX" not in result["parts"][1]["value"]
    assert result["drilldown"]["href"] == "/insights/sku_state_expansion?sku=SKU A"


def test_build_what_changed_returns_list_without_crashing():
    df = make_df([
        {"month_year": "2026-04", "sku": "SKU A", "chain": "Whole Foods", "coded_customer": "S1", "state": "FL", "units": 100},
        {"month_year": "2026-04", "sku": "SKU B", "chain": "Sprouts", "coded_customer": "S2", "state": "GA", "units": 50},
        {"month_year": "2026-05", "sku": "SKU A", "chain": "Whole Foods", "coded_customer": "S1", "state": "FL", "units": 80},
        {"month_year": "2026-05", "sku": "SKU B", "chain": "Sprouts", "coded_customer": "S2", "state": "GA", "units": 150},
        {"month_year": "2026-05", "sku": "SKU B", "chain": "Sprouts", "coded_customer": "S3", "state": "TX", "units": 20},
        {"month_year": "2026-06", "sku": "SKU C", "chain": "Target", "coded_customer": "S4", "state": "CA", "units": 999},
    ])

    results = build_what_changed(df, max_items=4)

    assert isinstance(results, list)
    assert len(results) > 0
    assert all(item["type"] == "state_change" for item in results)
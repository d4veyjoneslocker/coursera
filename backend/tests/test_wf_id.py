import pandas as pd
import pytest

from backend.transforms.whole_foods_id import add_whole_foods_flags


def test_add_whole_foods_flags_stress_12_months_multi_store_multi_sku(tmp_path):
    months = pd.period_range("2025-01", "2025-12", freq="M").astype(str)
    skus = ["SKU A", "SKU B", "SKU C"]

    # WF zip map:
    # CA has 5 WF zips. Sales appear in 3 → 60% → WF area
    # TX has 5 WF zips. Sales appear in 1 → 20% → NOT WF area
    wf_map = pd.DataFrame({
        "zip": [
            "90001", "90002", "90003", "90004", "90005",
            "73301", "73302", "73303", "73304", "73305",
        ],
        "wf_Chain": ["Whole Foods"] * 10,
        "wf_State": ["CA"] * 5 + ["TX"] * 5,
    })

    wf_map_path = tmp_path / "wf_map.csv"
    wf_map.to_csv(wf_map_path, index=False)

    rows = []

    # -----------------------------
    # CA WF-area confidential stores
    # -----------------------------

    # 90001: one confidential store per zip/month/SKU → definite WF
    for m in months:
        for sku in skus:
            rows.append({
                "Zip": "90001",
                "chain": "CONFIDENTIAL",
                "state": "CA",
                "month_year": m,
                "sku": sku,
                "store_number": "C-90001-1",
                "units": 10,
            })

    # 90002: two confidential stores per zip/month/SKU → possible WF
    for m in months:
        for sku in skus:
            rows.append({
                "Zip": "90002",
                "chain": "CONFIDENTIAL",
                "state": "CA",
                "month_year": m,
                "sku": sku,
                "store_number": "C-90002-1",
                "units": 10,
            })
            rows.append({
                "Zip": "90002",
                "chain": "CONFIDENTIAL",
                "state": "CA",
                "month_year": m,
                "sku": sku,
                "store_number": "C-90002-2",
                "units": 5,
            })

    # 90003: one confidential store per zip/month/SKU → definite WF
    for m in months:
        for sku in skus:
            rows.append({
                "Zip": "90003",
                "chain": "CONFIDENTIAL",
                "state": "CA",
                "month_year": m,
                "sku": sku,
                "store_number": "C-90003-1",
                "units": 10,
            })

    # Non-confidential store in WF zip → should NOT be flagged
    for m in months:
        for sku in skus:
            rows.append({
                "Zip": "90004",
                "chain": "Kroger",
                "state": "CA",
                "month_year": m,
                "sku": sku,
                "store_number": "K-90004-1",
                "units": 7,
            })

    # -----------------------------
    # TX (low WF coverage)
    # -----------------------------
    # Only 1/5 zips has sales → below 40% threshold
    for m in months:
        for sku in skus:
            rows.append({
                "Zip": "73301",
                "chain": "CONFIDENTIAL",
                "state": "TX",
                "month_year": m,
                "sku": sku,
                "store_number": "C-73301-1",
                "units": 10,
            })

    # -----------------------------
    # Non-WF zip (FL)
    # -----------------------------
    for m in months:
        for sku in skus:
            rows.append({
                "Zip": "33101",
                "chain": "CONFIDENTIAL",
                "state": "FL",
                "month_year": m,
                "sku": sku,
                "store_number": "C-33101-1",
                "units": 10,
            })

    df = pd.DataFrame(rows)

    result = add_whole_foods_flags(df, str(wf_map_path))

    # -----------------------------
    # Basic checks
    # -----------------------------
    assert len(result) == len(df)
    assert "is_whole_foods" in result.columns
    assert "possible_whole_foods" in result.columns
    assert "zip" in result.columns

    # ZIP normalization
    assert result["zip"].str.len().eq(5).all()

    # -----------------------------
    # Assertions by scenario
    # -----------------------------

    # 90001 → definite WF
    r_90001 = result[result["zip"] == "90001"]
    assert r_90001["is_whole_foods"].all()
    assert not r_90001["possible_whole_foods"].any()

    # 90002 → possible WF (multiple stores)
    r_90002 = result[result["zip"] == "90002"]
    assert not r_90002["is_whole_foods"].any()
    assert r_90002["possible_whole_foods"].all()

    # 90003 → definite WF
    r_90003 = result[result["zip"] == "90003"]
    assert r_90003["is_whole_foods"].all()
    assert not r_90003["possible_whole_foods"].any()

    # 90004 → not confidential
    r_90004 = result[result["zip"] == "90004"]
    assert not r_90004["is_whole_foods"].any()
    assert not r_90004["possible_whole_foods"].any()

    # TX → below coverage threshold
    r_tx = result[result["state"] == "TX"]
    assert not r_tx["is_whole_foods"].any()
    assert not r_tx["possible_whole_foods"].any()

    # FL → not in WF map
    r_fl = result[result["state"] == "FL"]
    assert not r_fl["is_whole_foods"].any()
    assert not r_fl["possible_whole_foods"].any()
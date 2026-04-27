import pandas as pd
import numpy as np

def add_whole_foods_flags(df: pd.DataFrame, wf_map_path: str) -> pd.DataFrame:
    df = df.copy()

    # 1. zip normalization
    df["zip"] = df["Zip"].astype(str).str.zfill(5)

    # 2. Confidential store ID
    df["is_confidential"] = df["chain"] == "CONFIDENTIAL"

    # 3. merge wf zip map
    wf_map = pd.read_csv(wf_map_path, dtype={"zip": str})
    df = df.merge(wf_map, on="zip", how="left")
    df["is_wf_zip"] = df["wf_Chain"] == "Whole Foods"

    # 4. state coverage logic
    wf_candidates = df[df["is_confidential"] & df["is_wf_zip"]]

    state_coverage = (
        wf_candidates.groupby("state")["zip"]
        .nunique()
        .rename("wf_zips_with_sales")
    )

    wf_state_totals = (
        wf_map.groupby("wf_State")["zip"]
        .nunique()
        .rename("wf_total_zips")
    )

    state_stats = (
        pd.concat([state_coverage, wf_state_totals], axis=1)
        .fillna(0)
    )

    state_stats["wf_area_coverage"] = (
        state_stats["wf_zips_with_sales"] / state_stats["wf_total_zips"]
    ).replace([np.inf, -np.inf], 0).fillna(0)

    state_stats["is_wf_area"] = (state_stats["wf_area_coverage"] >= 0.4)


    df = df.merge(
        state_stats[["is_wf_area"]],
        left_on="state",
        right_index=True,
        how="left",
    )

    df["is_wf_area"] = df["is_wf_area"].fillna(False)


    # 5. only confidential store in zip flag
    sku_zip_month_counts = (
        df[df["is_confidential"] & df["is_wf_zip"]]
        .groupby(["zip", "month_year", "sku"])
        .size()
        .rename("stores_selling_in_zip")  # your name
        .reset_index()
    )

    sku_zip_month_counts["one_store_probable"] = (sku_zip_month_counts["stores_selling_in_zip"] == 1)

    one_store_zip_month = (
        sku_zip_month_counts
        .groupby(["zip", "month_year"])["one_store_probable"]
        .all()
        .rename("one_store_zip_month")
        .reset_index()
    )

    df = df.merge(
        one_store_zip_month,
        on=["zip", "month_year"],
        how="left"
    )

    df["one_store_zip_month"] = df["one_store_zip_month"].fillna(False)

    # final flag
    df["is_whole_foods"] = (
        df["is_confidential"].fillna(False)
        & df["is_wf_zip"].fillna(False)
        & df["is_wf_area"].fillna(False)
        #& df["one_store_zip_month"].fillna(False)
    )

    df["possible_whole_foods"] = (
        df["is_confidential"].fillna(False)
        & df["is_wf_zip"].fillna(False)
        & df["is_wf_area"].fillna(False)
        & ~df["is_whole_foods"]
    )

    # drop helper columns

    helper_cols = [
        "is_wf_zip",
        "is_wf_area",
        "one_store_zip_month",
        "wf_area_coverage",
        "wf_zips_with_sales",
    ]

    df = df.drop(columns=[c for c in helper_cols if c in df.columns])

    return df
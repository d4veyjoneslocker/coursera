from pathlib import Path

import pandas as pd

from backend.data_pipeline.kehe_pipeline import normalize_kehe_upload
from backend.transforms.kehe import transform_kehe_full_pod_vendor
from backend.transforms.fill_rate.kehe import transform_kehe_fill_rate

from backend.metrics.fill_rate.features import build_fill_rate_features
from backend.metrics.fill_rate.metrics import fill_rate_metrics


ORG_ID = "default_org"

BASE_PATH = Path(
    f"backend/data/{ORG_ID}"
)

FULL_POD_PATH = (
    BASE_PATH
    / "raw"
    / "kehe"
    / "raw_master.csv"
)

FILL_RATE_PATH = (
    BASE_PATH
    / "processed"
    / "fill_rate"
)

OUTPUT_PATH = (
    BASE_PATH
    / "processed"
    / "fill_rate_smoke_test.xlsx"
)


def main():

    # =========================================================
    # LOAD + TRANSFORM FULL POD
    #
    # Mirrors the normal KeHE pipeline:
    # raw -> normalize -> transform
    # =========================================================

    full_pod_raw = pd.read_csv(
        FULL_POD_PATH
    )

    full_pod_normalized = normalize_kehe_upload(
        full_pod_raw
    )

    features_df = transform_kehe_full_pod_vendor(
        full_pod_normalized,
        org_id=ORG_ID,
    )

    print("\nFull POD:")
    print(f"Raw rows:         {len(full_pod_raw):,}")
    print(f"Transformed rows: {len(features_df):,}")


    # =========================================================
    # LOAD + TRANSFORM FILL RATE
    # =========================================================

    fill_rate_raw = pd.read_parquet(
        FILL_RATE_PATH
    )

    kehe_fill_rate_df = transform_kehe_fill_rate(
        fill_rate_raw,
        org_id=ORG_ID,
    )

    print("\nFill rate:")
    print(f"Raw rows:         {len(fill_rate_raw):,}")
    print(f"Transformed rows: {len(kehe_fill_rate_df):,}")


    # =========================================================
    # BUILD FILL-RATE FEATURES
    # =========================================================

    fill_features = build_fill_rate_features(
        kehe_fill_rate_df=kehe_fill_rate_df,
        features_df=features_df,
    )

    print(
        f"\nBuilt fill-rate features: "
        f"{len(fill_features):,} rows"
    )


    # =========================================================
    # DC MAPPING DIAGNOSTICS
    # =========================================================

    mapped_dc = (
        fill_features["dc"]
        .notna()
        .sum()
    )

    missing_dc = (
        fill_features["dc"]
        .isna()
        .sum()
    )

    total = len(fill_features)

    mapping_rate = (
        mapped_dc / total
        if total > 0
        else 0
    )

    print("\nDC mapping:")
    print(f"Mapped:       {mapped_dc:,}")
    print(f"Missing:      {missing_dc:,}")
    print(f"Mapping rate: {mapping_rate:.1%}")

    missing_dc_df = (
        fill_features.loc[
            fill_features["dc"].isna()
        ]
        .copy()
    )


    # =========================================================
    # METRICS
    # =========================================================

    overall = fill_rate_metrics(
        fill_features
    )

    by_dc = (
        fill_rate_metrics(
            fill_features,
            grain="dc",
        )
        .sort_values(
            "cases_ordered",
            ascending=False,
        )
    )

    by_chain = (
        fill_rate_metrics(
            fill_features,
            grain="chain",
        )
        .sort_values(
            "cases_ordered",
            ascending=False,
        )
    )

    chain_dc = (
        fill_rate_metrics(
            fill_features,
            grain=[
                "chain",
                "dc",
            ],
        )
        .sort_values(
            "cases_ordered",
            ascending=False,
        )
    )

    by_sku = (
        fill_rate_metrics(
            fill_features,
            grain="sku",
        )
        .sort_values(
            "cases_ordered",
            ascending=False,
        )
    )

    chain_sku = (
        fill_rate_metrics(
            fill_features,
            grain=[
                "chain",
                "sku",
            ],
        )
        .sort_values(
            "cases_ordered",
            ascending=False,
        )
    )

    dc_sku = (
        fill_rate_metrics(
            fill_features,
            grain=[
                "dc",
                "sku",
            ],
        )
        .sort_values(
            "cases_ordered",
            ascending=False,
        )
    )

    chain_dc_sku = (
        fill_rate_metrics(
            fill_features,
            grain=[
                "chain",
                "dc",
                "sku",
            ],
        )
        .sort_values(
            "cases_ordered",
            ascending=False,
        )
    )


    # =========================================================
    # WRITE EXCEL WORKBOOK
    # =========================================================

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with pd.ExcelWriter(
        OUTPUT_PATH,
        engine="openpyxl",
    ) as writer:

        # Raw feature-level output
        fill_features.to_excel(
            writer,
            sheet_name="features",
            index=False,
        )

        # DC mapping diagnostics
        missing_dc_df.to_excel(
            writer,
            sheet_name="missing_dc",
            index=False,
        )

        # Metrics
        overall.to_excel(
            writer,
            sheet_name="overall",
            index=False,
        )

        by_dc.to_excel(
            writer,
            sheet_name="by_dc",
            index=False,
        )

        by_chain.to_excel(
            writer,
            sheet_name="by_chain",
            index=False,
        )

        chain_dc.to_excel(
            writer,
            sheet_name="chain_x_dc",
            index=False,
        )

        by_sku.to_excel(
            writer,
            sheet_name="by_sku",
            index=False,
        )

        chain_sku.to_excel(
            writer,
            sheet_name="chain_x_sku",
            index=False,
        )

        dc_sku.to_excel(
            writer,
            sheet_name="dc_x_sku",
            index=False,
        )

        chain_dc_sku.to_excel(
            writer,
            sheet_name="chain_x_dc_x_sku",
            index=False,
        )


    print("\nSmoke test complete.")
    print(
        f"Workbook written to:\n"
        f"{OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
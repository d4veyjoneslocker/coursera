from pathlib import Path
import pandas as pd

# Change these imports to wherever your transforms actually live
from backend.transforms.kehe import transform_kehe_full_pod_vendor
from backend.transforms.fill_rate.kehe import transform_kehe_fill_rate
from backend.data_pipeline.kehe_pipeline import normalize_kehe_upload

ORG_ID = "default_org"

BASE_PATH = Path(f"backend/data/{ORG_ID}")

FULL_POD_PATH = BASE_PATH / "raw" / "kehe" / "raw_master.csv"
FILL_RATE_PATH = BASE_PATH / "processed" / "fill_rate"


# ============================================================
# LOAD + NORMALIZE + TRANSFORM FULL POD
# ============================================================

print("\n" + "=" * 70)
print("FULL POD")
print("=" * 70)

full_pod_raw = pd.read_csv(FULL_POD_PATH)

full_pod_normalized = normalize_kehe_upload(full_pod_raw)

full_pod_df = transform_kehe_full_pod_vendor(
    full_pod_normalized,
    org_id=ORG_ID,
)

print(f"Raw rows:        {len(full_pod_raw):,}")
print(f"Normalized rows: {len(full_pod_normalized):,}")
print(f"Processed rows:  {len(full_pod_df):,}")


# ============================================================
# LOAD + TRANSFORM FILL RATE
# ============================================================

print("\n" + "=" * 70)
print("FILL RATE")
print("=" * 70)

fill_rate_raw = pd.read_parquet(FILL_RATE_PATH)

fill_rate_df = transform_kehe_fill_rate(
    fill_rate_raw,
    org_id=ORG_ID,
)

print(f"Raw rows:       {len(fill_rate_raw):,}")
print(f"Processed rows: {len(fill_rate_df):,}")

alb_safeway_debug = (
    full_pod_df[
        full_pod_df["customer_name"]
        .astype("string")
        .str.contains(
            "SAFEWAY|ALBERTSON",
            case=False,
            na=False,
        )
    ][
        [
            "chain",
            "customer_name",
            "chain_store_number",
            "chain_store_key",
        ]
    ]
    .drop_duplicates()
    .sort_values(["chain", "chain_store_number"])
)

alb_safeway_debug.to_csv(
    f"backend/data/{ORG_ID}/processed/albertsons_safeway_full_pod_debug.csv",
    index=False,
)

print("\nFill-rate chain_store_number coverage:")
print(
    fill_rate_df["chain_store_number"]
    .notna()
    .value_counts()
)

print("\nSample:")
print(
    fill_rate_df[
        [
            "chain",
            "customer_name",
            "chain_store_number",
            "chain_store_key",
        ]
    ]
    .drop_duplicates()
    .head(20)
    .to_string(index=False)
)


# ============================================================
# UNIQUE KEYS
# ============================================================

full_pod_keys = set(
    full_pod_df["chain_store_key"]
    .dropna()
    .unique()
)

fill_rate_keys = set(
    fill_rate_df["chain_store_key"]
    .dropna()
    .unique()
)

matched_keys = full_pod_keys & fill_rate_keys
fill_rate_only = fill_rate_keys - full_pod_keys
full_pod_only = full_pod_keys - fill_rate_keys


# ============================================================
# MATCH RESULTS
# ============================================================

print("\n" + "=" * 70)
print("MATCH RESULTS")
print("=" * 70)

print(f"Full POD unique keys:      {len(full_pod_keys):,}")
print(f"Fill-rate unique keys:     {len(fill_rate_keys):,}")
print(f"Matched keys:              {len(matched_keys):,}")
print(f"Fill-rate unmatched keys:  {len(fill_rate_only):,}")
print(f"Full POD unmatched keys:   {len(full_pod_only):,}")

if fill_rate_keys:
    print(
        f"Fill-rate key match rate:  "
        f"{len(matched_keys) / len(fill_rate_keys):.1%}"
    )


# ============================================================
# FILL-RATE STORES THAT HAVE A KEY BUT DON'T MATCH FULL POD
# ============================================================

unmatched_fill_rate = (
    fill_rate_df[
        fill_rate_df["chain_store_key"].notna()
        & ~fill_rate_df["chain_store_key"].isin(full_pod_keys)
    ][
        [
            "chain",
            "customer_name",
            "chain_store_number",
            "chain_store_key",
        ]
    ]
    .drop_duplicates()
    .sort_values(
        ["chain", "chain_store_number"],
        na_position="last",
    )
)

print("\n" + "=" * 70)
print("FILL-RATE KEYS NOT FOUND IN FULL POD")
print("=" * 70)

if unmatched_fill_rate.empty:
    print("None")
else:
    print(unmatched_fill_rate.to_string(index=False))


# ============================================================
# FILL-RATE STORES WHERE WE COULDN'T EXTRACT A NUMBER
# ============================================================

no_fill_rate_number = (
    fill_rate_df[
        fill_rate_df["chain_store_number"].isna()
    ][
        [
            "chain",
            "customer_name",
        ]
    ]
    .drop_duplicates()
    .sort_values(
        ["chain", "customer_name"],
        na_position="last",
    )
)

# ============================================================
# EXPORT MATCH DIAGNOSTICS
# ============================================================

diagnostics_output_path = (
    f"backend/data/{ORG_ID}/processed/"
    "fill_rate_store_match_test.csv"
)

diagnostics = pd.concat(
    [
        unmatched_fill_rate.assign(
            match_issue="key_not_found_in_full_pod"
        ),
        no_fill_rate_number.assign(
            chain_store_number=pd.NA,
            chain_store_key=pd.NA,
            match_issue="no_store_number_extracted",
        ),
    ],
    ignore_index=True,
)

diagnostics.to_csv(
    f"backend/data/{ORG_ID}/processed/fill_rate_store_match_test.csv",
    index=False,
)

print(
    f"Saved diagnostics to "
    f"backend/data/{ORG_ID}/processed/fill_rate_store_match_test.csv"
)

print(f"Saved diagnostics to {diagnostics_output_path}")

print("\n" + "=" * 70)
print("FILL-RATE STORES WITH NO CHAIN STORE NUMBER")
print("=" * 70)

if no_fill_rate_number.empty:
    print("None")
else:
    print(no_fill_rate_number.to_string(index=False))


# ============================================================
# FULL POD STORES WHERE WE COULDN'T EXTRACT A NUMBER
# ============================================================

no_full_pod_number = (
    full_pod_df[
        full_pod_df["chain_store_number"].isna()
    ][
        [
            "chain",
            "customer_name",
        ]
    ]
    .drop_duplicates()
    .sort_values(
        ["chain", "customer_name"],
        na_position="last",
    )
)

print("\n" + "=" * 70)
print("FULL POD STORES WITH NO CHAIN STORE NUMBER")
print("=" * 70)

if no_full_pod_number.empty:
    print("None")
else:
    print(no_full_pod_number.to_string(index=False))


# ============================================================
# CHECK FOR AMBIGUOUS FULL POD KEYS
#
# Same chain_store_key resolving to multiple customer_name
# values isn't automatically wrong, but we want to inspect it.
# ============================================================

full_pod_key_names = (
    full_pod_df[
        full_pod_df["chain_store_key"].notna()
    ]
    .groupby("chain_store_key")["customer_name"]
    .nunique()
)

ambiguous_keys = full_pod_key_names[
    full_pod_key_names > 1
].index

ambiguous_full_pod = (
    full_pod_df[
        full_pod_df["chain_store_key"].isin(ambiguous_keys)
    ][
        [
            "chain_store_key",
            "chain",
            "chain_store_number",
            "customer_name",
        ]
    ]
    .drop_duplicates()
    .sort_values(
        ["chain_store_key", "customer_name"]
    )
)

print("\n" + "=" * 70)
print("AMBIGUOUS FULL POD KEYS")
print("=" * 70)

if ambiguous_full_pod.empty:
    print("None")
else:
    print(ambiguous_full_pod.to_string(index=False))
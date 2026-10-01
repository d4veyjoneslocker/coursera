from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd

from backend.metrics.metric_tables import (
    chain_table_og,
    chain_table_new,
)


ORG_ID = "67a96381-5014-4a9b-bfe8-a14e6da5affe"

FEATURES_PATH = Path(
    f"backend/data/{ORG_ID}/features_df.parquet"
)

ACTIVE_PODS_PATH = Path(
    f"backend/data/{ORG_ID}/active_pods_df.parquet"
)


# =================================================
# LOAD DATA
# =================================================

features_df = pd.read_parquet(FEATURES_PATH)
active_pods_df = pd.read_parquet(ACTIVE_PODS_PATH)

features_df["month_year"] = pd.PeriodIndex(
    features_df["month_year"],
    freq="M",
)

active_pods_df["month_year"] = pd.PeriodIndex(
    active_pods_df["month_year"],
    freq="M",
)


print("\n" + "=" * 70)
print("CHAIN TABLE OG VS NEW")
print("=" * 70)

print(f"Features rows: {len(features_df):,}")
print(f"Active POD rows: {len(active_pods_df):,}")


# =================================================
# RUN OLD OLD
# =================================================

start = perf_counter()

old = chain_table_og(
    features_df
)

old_time = perf_counter() - start

print(f"\nOG TIME:  {old_time:.4f}s")


# =================================================
# RUN NEW NEW
# =================================================

start = perf_counter()

new = chain_table_new(
    features_df,
    active_pods_df,
)

new_time = perf_counter() - start

print(f"NEW TIME: {new_time:.4f}s")

if new_time > 0:
    print(
        f"SPEEDUP:  {old_time / new_time:.2f}x"
    )


# =================================================
# ALIGN RESULTS
# =================================================

old = (
    old
    .sort_values("chain")
    .reset_index(drop=True)
)

new = (
    new
    .sort_values("chain")
    .reset_index(drop=True)
)


# =================================================
# BASIC STRUCTURE CHECK
# =================================================

print("\n" + "-" * 70)
print("STRUCTURE")
print("-" * 70)

print(f"OG rows:  {len(old):,}")
print(f"NEW rows: {len(new):,}")

print(f"OG columns:  {old.columns.tolist()}")
print(f"NEW columns: {new.columns.tolist()}")

assert set(old.columns) == set(new.columns), (
    "Column mismatch between OG and NEW"
)


# =================================================
# MERGE RESULTS
# =================================================

comparison = old.merge(
    new,
    on="chain",
    how="outer",
    suffixes=("_og", "_new"),
    indicator=True,
)

missing_chains = comparison[
    comparison["_merge"] != "both"
]

if not missing_chains.empty:

    print("\nCHAIN MISMATCHES:")

    print(
        missing_chains[
            ["chain", "_merge"]
        ].to_string(index=False)
    )


# =================================================
# COMPARE EVERY OUTPUT METRIC
# =================================================

metric_cols = [
    col
    for col in old.columns
    if col != "chain"
]

all_mismatches = []


print("\n" + "-" * 70)
print("METRIC COMPARISON")
print("-" * 70)


for col in metric_cols:

    og_col = f"{col}_og"
    new_col = f"{col}_new"

    og_values = pd.to_numeric(
        comparison[og_col],
        errors="coerce",
    )

    new_values = pd.to_numeric(
        comparison[new_col],
        errors="coerce",
    )

    matches = np.isclose(
        og_values,
        new_values,
        equal_nan=True,
    )

    mismatches = comparison.loc[
        ~matches,
        [
            "chain",
            og_col,
            new_col,
        ],
    ].copy()

    print(
        f"{col:<25} "
        f"matches={matches.sum():>4} "
        f"mismatches={len(mismatches):>4}"
    )

    if not mismatches.empty:

        mismatches["metric"] = col

        mismatches = mismatches.rename(
            columns={
                og_col: "og_value",
                new_col: "new_value",
            }
        )

        all_mismatches.append(
            mismatches[
                [
                    "chain",
                    "metric",
                    "og_value",
                    "new_value",
                ]
            ]
        )


# =================================================
# PRINT MISMATCH SUMMARY
# =================================================

print("\n" + "=" * 70)

if all_mismatches:

    mismatch_df = pd.concat(
        all_mismatches,
        ignore_index=True,
    )

    print(
        f"FAILED — {len(mismatch_df):,} "
        f"metric mismatches"
    )

    print("\nMISMATCH DETAILS:")

    print(
        mismatch_df.to_string(index=False)
    )

else:

    mismatch_df = pd.DataFrame()

    print(
        "PASSED — OG AND NEW MATCH EXACTLY"
    )

print("=" * 70)


# =================================================
# BUYING STORES L1M DEBUG
#
# Compare:
#
#   1. Chains OG says should be 0
#   2. Chains previously identified as legitimately NaN
#
# Goal:
# Understand what historical condition makes OG create
# a zero-filled L1M row.
# =================================================

debug_chains = [
    # OG = 0, NEW = NaN
    "GENERIC EDI",
    "HORTON'S MARKET LLC",
    "PALACE MARKET",

    # Previously identified OG = NaN cases
    "AMERICA'S FOOD BASKET",
    "DECICCO FAMILY",
    "PARK SLOPE COOP",
    "SHERRY'S PLACE",
]


current_month = (
    pd.Timestamp.today()
    .to_period("M")
)

l1m = current_month - 1


print("\n\n" + "=" * 70)
print("BUYING STORES L1M — ZERO VS NAN DEBUG")
print("=" * 70)

print(f"Current month: {current_month}")
print(f"L1M:          {l1m}")


for chain in debug_chains:

    print("\n" + "-" * 70)
    print(chain)
    print("-" * 70)

    # ---------------------------------------------
    # FINAL OUTPUT
    # ---------------------------------------------

    old_row = old[
        old["chain"] == chain
    ]

    new_row = new[
        new["chain"] == chain
    ]

    if not old_row.empty:

        print(
            "OG buying_stores_l1m:",
            old_row[
                "buying_stores_l1m"
            ].iloc[0],
        )

    else:

        print(
            "OG buying_stores_l1m: "
            "CHAIN NOT PRESENT"
        )

    if not new_row.empty:

        print(
            "NEW buying_stores_l1m:",
            new_row[
                "buying_stores_l1m"
            ].iloc[0],
        )

    else:

        print(
            "NEW buying_stores_l1m: "
            "CHAIN NOT PRESENT"
        )


    # ---------------------------------------------
    # FEATURES HISTORY
    # ---------------------------------------------

    chain_features = features_df[
        features_df["chain"] == chain
    ].copy()

    if chain_features.empty:

        print("\nFEATURES:")
        print("  No feature rows")

    else:

        feature_min = (
            chain_features[
                "month_year"
            ].min()
        )

        feature_max = (
            chain_features[
                "month_year"
            ].max()
        )

        feature_months = sorted(
            chain_features[
                "month_year"
            ]
            .dropna()
            .unique()
            .tolist()
        )

        l1m_feature_rows = chain_features[
            chain_features[
                "month_year"
            ] == l1m
        ]

        print("\nFEATURES:")

        print(
            f"  First purchase month: "
            f"{feature_min}"
        )

        print(
            f"  Last purchase month:  "
            f"{feature_max}"
        )

        print(
            f"  Purchase months:      "
            f"{feature_months}"
        )

        print(
            f"  L1M feature rows:     "
            f"{len(l1m_feature_rows):,}"
        )

        if "pod_helper" in chain_features.columns:

            print(
                f"  L1M buying stores:    "
                f"{l1m_feature_rows['pod_helper'].nunique():,}"
            )


    # ---------------------------------------------
    # ACTIVE POD HISTORY
    # ---------------------------------------------

    chain_active = active_pods_df[
        active_pods_df["chain"] == chain
    ].copy()

    if chain_active.empty:

        print("\nACTIVE PODS:")
        print("  No active POD rows")

    else:

        active_min = (
            chain_active[
                "month_year"
            ].min()
        )

        active_max = (
            chain_active[
                "month_year"
            ].max()
        )

        active_l1m = chain_active[
            chain_active[
                "month_year"
            ] == l1m
        ]

        print("\nACTIVE PODS:")

        print(
            f"  First active month:   "
            f"{active_min}"
        )

        print(
            f"  Last active month:    "
            f"{active_max}"
        )

        print(
            f"  Active PODs in L1M:  "
            f"{active_l1m['pod_helper'].nunique():,}"
        )


    # ---------------------------------------------
    # MONTH-BY-MONTH HISTORY
    #
    # Show recent purchase rows vs active membership.
    # This should make the OG zero-fill rule obvious.
    # ---------------------------------------------

    history_start = l1m - 12

    recent_features = chain_features[
        (
            chain_features["month_year"]
            >= history_start
        )
        & (
            chain_features["month_year"]
            <= l1m
        )
    ]

    recent_active = chain_active[
        (
            chain_active["month_year"]
            >= history_start
        )
        & (
            chain_active["month_year"]
            <= l1m
        )
    ]


    purchase_history = (
        recent_features
        .groupby(
            "month_year"
        )["pod_helper"]
        .nunique()
        .rename(
            "buying_stores"
        )
    )


    active_history = (
        recent_active
        .groupby(
            "month_year"
        )["pod_helper"]
        .nunique()
        .rename(
            "active_pods"
        )
    )


    month_spine = pd.DataFrame(
        {
            "month_year": pd.period_range(
                start=history_start,
                end=l1m,
                freq="M",
            )
        }
    )


    history = (
        month_spine
        .merge(
            purchase_history,
            on="month_year",
            how="left",
        )
        .merge(
            active_history,
            on="month_year",
            how="left",
        )
    )


    print("\nRECENT HISTORY:")

    print(
        history.to_string(
            index=False
        )
    )


# =================================================
# ASSERTIONS
#
# Keep these at the END so all debug information
# prints before pytest fails.
# =================================================

assert missing_chains.empty, (
    "OG and NEW contain different chains"
)

assert not all_mismatches, (
    "OG and NEW metric values do not match"
)
import numpy as np
import pandas as pd

NEW_STATUSES = {"New"}
RAMPING_STATUSES = {"Ramping"}
MATURE_STATUSES = {"Mature"}

ATOM = ["coded_customer", "sku"]


# ---------------------------------------------------------
# Contribution table
# ---------------------------------------------------------

def build_units_contribution_table(
    df: pd.DataFrame,
    current_start,
    current_end,
    prior_start,
    prior_end,
    dimensions: list[str] | None = None,
) -> pd.DataFrame:
    """
    Builds an additive store × SKU contribution table for a current
    period vs. prior period.

    Lifecycle is computed upstream and must already exist on df
    as the sku_lifecycle column.

    Attribution:
        New      -> new
        Ramping  -> ramping
        Mature   -> mature

    Every row assigns its full unit change to exactly one bucket:

        new_impact
        + ramping_impact
        + mature_impact
        == total_change

    Because attribution happens at the atomic placement level,
    impacts remain additive at any higher aggregation grain.
    """

    out_cols = ATOM + [
        "units_current",
        "units_prior",
        "total_change",
        "sku_lifecycle",
        "new_impact",
        "ramping_impact",
        "mature_impact",
    ]

    if df is None or df.empty:
        return pd.DataFrame(columns=out_cols)

    df = df.copy()

    if "sku_lifecycle" not in df.columns:
        raise ValueError(
            "df must contain sku_lifecycle before building contributions."
        )
    # -----------------------------------------------------
    # Dimensions
    # -----------------------------------------------------

    if dimensions is None:
        dimensions = [
            col
            for col in ["chain", "state", "dc", "distributor", "channel"]
            if col in df.columns
        ]

    group_cols = ATOM + dimensions + ["sku_lifecycle"]

    # -----------------------------------------------------
    # Current / prior windows
    # -----------------------------------------------------

    current_df = df[
        (df["month_year"] >= current_start)
        & (df["month_year"] <= current_end)
    ].copy()

    prior_df = df[
        (df["month_year"] >= prior_start)
        & (df["month_year"] <= prior_end)
    ].copy()

    current = (
        current_df
        .groupby(group_cols, dropna=False)["units"]
        .sum()
        .reset_index(name="units_current")
    )

    prior = (
        prior_df
        .groupby(group_cols, dropna=False)["units"]
        .sum()
        .reset_index(name="units_prior")
    )

    # -----------------------------------------------------
    # Outer join so new / lost / quiet placements survive
    # -----------------------------------------------------

    result = current.merge(prior, on=group_cols, how="outer")

    result["units_current"] = result["units_current"].fillna(0)
    result["units_prior"] = result["units_prior"].fillna(0)
    result["total_change"] = result["units_current"] - result["units_prior"]

    # -----------------------------------------------------
    # Validate analysis endpoint
    # -----------------------------------------------------

    latest_month = df["month_year"].max()

    if current_end != latest_month:
        raise ValueError(
            "Current contribution analysis only supports "
            "current_end equal to the latest month in the dataset."
        )

    # -----------------------------------------------------
    # Every moving placement must have a status
    # -----------------------------------------------------

    movers = result[result["total_change"] != 0]

    missing = movers[
        movers["sku_lifecycle"].isna()
        | (movers["sku_lifecycle"] == "-")
    ]

    if not missing.empty:
        raise ValueError(
            f"{len(missing)} moving store×SKU rows have no lifecycle status "
            f"at {current_end}. Possible join/grain mismatch. "
            f"Sample:\n{missing[ATOM + ['total_change']].head()}"
        )

    # -----------------------------------------------------
    # Status -> impact bucket
    # -----------------------------------------------------

    # -----------------------------------------------------
    # Lifecycle -> impact bucket
    # -----------------------------------------------------

    is_new = result["sku_lifecycle"].isin(NEW_STATUSES)
    is_ramping = result["sku_lifecycle"].isin(RAMPING_STATUSES)
    is_mature = result["sku_lifecycle"].isin(MATURE_STATUSES)

    result["new_impact"] = np.where(
        is_new,
        result["total_change"],
        0.0,
    )

    result["ramping_impact"] = np.where(
        is_ramping,
        result["total_change"],
        0.0,
    )

    result["mature_impact"] = np.where(
        is_mature,
        result["total_change"],
        0.0,
    )

    # -----------------------------------------------------
    # Reconciliation invariant
    # -----------------------------------------------------

    recon_gap = (
        result["new_impact"]
        + result["ramping_impact"]
        + result["mature_impact"]
        - result["total_change"]
    ).abs()

    bad_mask = recon_gap > 1e-6

    if bad_mask.any():
        bad = result[bad_mask]

        raise ValueError(
            f"Attribution failed to reconcile for {len(bad)} rows. "
            f"Likely a sku_lifecycle not mapped to New, Ramping, or Mature. "
            f"Sample:\n"
            f"{bad[ATOM + ['sku_lifecycle', 'total_change']].head()}"
        )
    # -----------------------------------------------------
    # Drop rows with no unit movement
    # -----------------------------------------------------

    result = result[result["total_change"] != 0].copy()

    return result.reset_index(drop=True)


# ---------------------------------------------------------
# Aggregate contribution table
# ---------------------------------------------------------

def aggregate_units_contributions(
    contributions: pd.DataFrame,
    group_cols=None,
) -> pd.DataFrame:
    """
    Aggregates the already-assigned contribution ledger to any grain.

    No attribution is recalculated here.
    """

    if group_cols is None:
        group_cols = []
    elif isinstance(group_cols, str):
        group_cols = [group_cols]
    else:
        group_cols = [c for c in group_cols if c]

    if contributions is None or contributions.empty:
        return pd.DataFrame()

    metrics = [
        "units_prior",
        "units_current",
        "total_change",
        "new_impact",
        "ramping_impact",
        "mature_impact",
    ]

    if group_cols:
        result = (
            contributions
            .groupby(group_cols, dropna=False)[metrics]
            .sum()
            .reset_index()
        )

    else:
        result = pd.DataFrame([
            contributions[metrics].sum()
        ])

    # -----------------------------------------------------
    # Shares / primary driver
    # -----------------------------------------------------

    nonzero_change = result["total_change"] != 0

    # Net shares — useful descriptively, but can exceed 100%
    # when lifecycle buckets offset one another.
    result["new_share"] = np.where(
        nonzero_change,
        result["new_impact"] / result["total_change"],
        np.nan,
    )

    result["ramping_share"] = np.where(
        nonzero_change,
        result["ramping_impact"] / result["total_change"],
        np.nan,
    )

    result["mature_share"] = np.where(
        nonzero_change,
        result["mature_impact"] / result["total_change"],
        np.nan,
    )

    # Primary driver is based on share of GROSS movement, not net change.
    # This prevents near-cancelling forces from creating absurd dominance scores.
    impact_cols = [
        "new_impact",
        "ramping_impact",
        "mature_impact",
    ]

    abs_impacts = result[impact_cols].abs()

    gross_impact = abs_impacts.sum(axis=1)

    dominant_share = (
        abs_impacts.max(axis=1)
        / gross_impact.replace(0, np.nan)
    )

    LED_THRESHOLD = 0.65

    dominant_col = abs_impacts.idxmax(axis=1)

    result["primary_driver"] = np.select(
        [
            gross_impact == 0,
            dominant_share < LED_THRESHOLD,
            dominant_col == "new_impact",
            dominant_col == "ramping_impact",
        ],
        [
            "none",
            "balanced",
            "new",
            "ramping",
        ],
        default="mature",
    )

    return result


# ---------------------------------------------------------
# Full additive decomposition
# ---------------------------------------------------------

def calculate_units_growth_decomposition_additive(
    df: pd.DataFrame,
    current_start,
    current_end,
    prior_start,
    prior_end,
    group_cols=None,
    dimensions: list[str] | None = None,
) -> pd.DataFrame:
    """
    Convenience wrapper:

        raw data
        -> atomic contribution table
        -> aggregate to requested grain

    This is the additive replacement for the older aggregate
    POD × VPO decomposition when building the explanation tree.
    """

    contributions = build_units_contribution_table(
        df=df,
        current_start=current_start,
        current_end=current_end,
        prior_start=prior_start,
        prior_end=prior_end,
        dimensions=dimensions,
    )

    if contributions.empty:
        return pd.DataFrame()

    return aggregate_units_contributions(
        contributions=contributions,
        group_cols=group_cols,
    )


# ---------------------------------------------------------
# Reconciliation helper
# ---------------------------------------------------------

def validate_contribution_reconciliation(
    contributions: pd.DataFrame,
) -> dict:
    """
    Returns a simple reconciliation summary for debugging.
    """

    if contributions is None or contributions.empty:
        return {
            "total_change": 0,
            "new_impact": 0,
            "ramping_impact": 0,
            "mature_impact": 0,
            "reconciliation_gap": 0,
        }

    total_change = contributions["total_change"].sum()
    new_impact = contributions["new_impact"].sum()
    ramping_impact = contributions["ramping_impact"].sum()
    mature_impact = contributions["mature_impact"].sum()

    reconciliation_gap = (
        new_impact
        + ramping_impact
        + mature_impact
        - total_change
    )

    return {
        "total_change": total_change,
        "new_impact": new_impact,
        "ramping_impact": ramping_impact,
        "mature_impact": mature_impact,
        "reconciliation_gap": reconciliation_gap,
    }
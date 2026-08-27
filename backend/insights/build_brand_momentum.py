import pandas as pd

from backend.metrics.metric_helpers import get_current_period
from backend.metrics.monthly_metric_calculators import (
    calculate_monthly_revenue,
    calculate_monthly_units,
)
from backend.metrics.metric_growth_rates import (
    add_additive_metric_3m,
    calculate_buying_stores_3m,
    calculate_vpo_3m,
    add_prior_month_columns,
    add_pct_change_columns,
)


# ---------------------------------------------------------
# Core metric builder
# ---------------------------------------------------------

def _build_3m_metrics(
    df_filtered: pd.DataFrame,
    df_full: pd.DataFrame,
    grain: list[str],
) -> pd.DataFrame:
    """
    Uses SKUba's existing metric functions to build
    L3M performance and growth at any requested grain.
    """

    if df_filtered is None or df_filtered.empty:
        return pd.DataFrame()

    result = calculate_monthly_revenue(
        df_filtered,
        grain,
    )

    result = result.merge(
        calculate_monthly_units(
            df_filtered,
            grain,
        ),
        on=grain + ["month_year"],
        how="left",
    )

    result = add_additive_metric_3m(
        result,
        grain,
        "revenue",
    )

    result = add_additive_metric_3m(
        result,
        grain,
        "units",
    )

    result = result.merge(
        calculate_buying_stores_3m(
            df_filtered,
            grain,
        ),
        on=grain + ["month_year"],
        how="left",
    )

    result = result.merge(
        calculate_vpo_3m(
            df_filtered,
            df_full,
            grain,
        ),
        on=grain + ["month_year"],
        how="left",
    )

    result = add_prior_month_columns(
        result,
        grain,
        "revenue",
        l3m=True,
    )

    result = add_prior_month_columns(
        result,
        grain,
        "units",
        l3m=True,
    )

    result = add_prior_month_columns(
        result,
        grain,
        "buying_stores",
        l3m=True,
    )

    result = add_prior_month_columns(
        result,
        grain,
        "vpo",
        l3m=True,
    )

    result = add_pct_change_columns(
        result,
        "revenue",
        l3m=True,
    )

    result = add_pct_change_columns(
        result,
        "units",
        l3m=True,
    )

    result = add_pct_change_columns(
        result,
        "buying_stores",
        l3m=True,
    )

    result = add_pct_change_columns(
        result,
        "vpo",
        l3m=True,
    )

    current_month = get_current_period(
        include_current_month=True
    )

    result = result[
        result["month_year"] != current_month
    ].copy()

    if result.empty:
        return result

    latest_month = result["month_year"].max()

    return result[
        result["month_year"] == latest_month
    ].copy()


# ---------------------------------------------------------
# Brand momentum evidence
# ---------------------------------------------------------

def build_brand_momentum(
    df: pd.DataFrame,
    skus: list[str] | None = None,
) -> dict:
    """
    Builds raw evidence describing the current health,
    scale, and momentum of the brand.

    This function does NOT decide which findings are good
    or worth surfacing. It only generates the evidence.

    The analytical layer can later evaluate:
        - overall growth
        - distribution growth
        - velocity growth
        - SKU momentum
        - retailer momentum
        - geographic momentum
        - channel momentum
        - breadth / consistency of growth
    """

    if df is None or df.empty:
        return {}

    df_analysis = df.copy()

    # -----------------------------------------------------
    # Optional pitch-level SKU restriction
    # -----------------------------------------------------

    if skus:
        df_analysis = df_analysis[
            df_analysis["sku"].isin(skus)
        ].copy()

    if df_analysis.empty:
        return {}

    # -----------------------------------------------------
    # Overall brand
    # -----------------------------------------------------

    overall = _build_3m_metrics(
        df_filtered=df_analysis,
        df_full=df_analysis,
        grain=[],
    )

    # -----------------------------------------------------
    # SKU
    # -----------------------------------------------------

    by_sku = _build_3m_metrics(
        df_filtered=df_analysis,
        df_full=df_analysis,
        grain=["sku"],
    )

    # -----------------------------------------------------
    # Retailer / chain
    # -----------------------------------------------------

    by_chain = _build_3m_metrics(
        df_filtered=df_analysis,
        df_full=df_analysis,
        grain=["chain"],
    )

    # -----------------------------------------------------
    # Geography
    # -----------------------------------------------------

    by_state = _build_3m_metrics(
        df_filtered=df_analysis,
        df_full=df_analysis,
        grain=["state"],
    )

    # -----------------------------------------------------
    # Channel
    # -----------------------------------------------------

    by_channel = _build_3m_metrics(
        df_filtered=df_analysis,
        df_full=df_analysis,
        grain=["channel"],
    )

    # -----------------------------------------------------
    # Useful intersections
    # -----------------------------------------------------

    by_chain_sku = _build_3m_metrics(
        df_filtered=df_analysis,
        df_full=df_analysis,
        grain=["chain", "sku"],
    )

    by_state_sku = _build_3m_metrics(
        df_filtered=df_analysis,
        df_full=df_analysis,
        grain=["state", "sku"],
    )

    by_channel_sku = _build_3m_metrics(
        df_filtered=df_analysis,
        df_full=df_analysis,
        grain=["channel", "sku"],
    )

    return {
        "skus": skus or [],

        "overall": overall,

        "breakdowns": {
            "sku": by_sku,
            "chain": by_chain,
            "state": by_state,
            "channel": by_channel,
        },

        "intersections": {
            "chain_sku": by_chain_sku,
            "state_sku": by_state_sku,
            "channel_sku": by_channel_sku,
        },
    }


# ---------------------------------------------------------
# Test
# ---------------------------------------------------------

if __name__ == "__main__":
    from pathlib import Path

    ORG_ID = "67a96381-5014-4a9b-bfe8-a14e6da5affe"

    df = pd.read_parquet(
        Path("backend/data")
        / ORG_ID
        / "features_df.parquet"
    )

    result = build_brand_momentum(
        df=df,
    )

    output_dir = (
        Path("backend/data")
        / ORG_ID
        / "brand_momentum"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    result["overall"].to_csv(
        output_dir / "overall.csv",
        index=False,
    )

    result["breakdowns"]["sku"].to_csv(
        output_dir / "by_sku.csv",
        index=False,
    )

    result["breakdowns"]["chain"].to_csv(
        output_dir / "by_chain.csv",
        index=False,
    )

    result["breakdowns"]["state"].to_csv(
        output_dir / "by_state.csv",
        index=False,
    )

    result["breakdowns"]["channel"].to_csv(
        output_dir / "by_channel.csv",
        index=False,
    )

    result["intersections"]["chain_sku"].to_csv(
        output_dir / "by_chain_sku.csv",
        index=False,
    )

    result["intersections"]["state_sku"].to_csv(
        output_dir / "by_state_sku.csv",
        index=False,
    )

    result["intersections"]["channel_sku"].to_csv(
        output_dir / "by_channel_sku.csv",
        index=False,
    )

    print(f"Brand momentum exported to: {output_dir}")
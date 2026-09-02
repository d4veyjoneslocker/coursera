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

def add_sku_count(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    df = df.copy()

    months = sorted(df["month_year"].dropna().unique())

    rows = []

    pods = (
        df[
            [
                "coded_customer",
                "sku",
                "first_month_purchased",
            ]
        ]
        .drop_duplicates()
    )

    for month in months:
        active = pods[
            pods["first_month_purchased"] <= month
        ]

        counts = (
            active
            .groupby("coded_customer", as_index=False)
            .agg(sku_count=("sku", "nunique"))
        )

        counts["month_year"] = month
        rows.append(counts)

    sku_counts = pd.concat(
        rows,
        ignore_index=True,
    )

    return df.merge(
        sku_counts,
        on=["coded_customer", "month_year"],
        how="left",
    )

# ---------------------------------------------------------
# Core metric builder
# ---------------------------------------------------------

def _build_3m_metrics(
    df_filtered: pd.DataFrame,
    df_full: pd.DataFrame,
    grain: list[str],
) -> pd.DataFrame:

    if df_filtered is None or df_filtered.empty:
        return pd.DataFrame()

    df_filtered = df_filtered.copy()
    df_full = df_full.copy()

    df_filtered["month_year"] = pd.PeriodIndex(
        df_filtered["month_year"],
        freq="M",
    )

    df_full["month_year"] = pd.PeriodIndex(
        df_full["month_year"],
        freq="M",
    )

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
# Generic scope analysis
# ---------------------------------------------------------

def build_scope_analysis(
    df: pd.DataFrame,
    states: list[str] | None = None,
    retailers: list[str] | None = None,
    skus: list[str] | None = None,
    breakdown: list[str] | None = None,
) -> pd.DataFrame:
    """
    Calculates performance for any selected pitch scope.

    Examples:

    Michigan:
        states=["MI"]

    Fresh Thyme:
        retailers=["FRESH THYME"]

    Fresh Thyme in Michigan:
        states=["MI"],
        retailers=["FRESH THYME"]

    Fresh Thyme in Michigan by SKU:
        states=["MI"],
        retailers=["FRESH THYME"],
        breakdown=["sku"]
    """

    if df is None or df.empty:
        return pd.DataFrame()

    df_scope = df.copy()

    if states:
        df_scope = df_scope[
            df_scope["state"].isin(states)
        ].copy()

    if retailers:
        df_scope = df_scope[
            df_scope["chain"].isin(retailers)
        ].copy()

    if skus:
        df_scope = df_scope[
            df_scope["sku"].isin(skus)
        ].copy()

    if df_scope.empty:
        return pd.DataFrame()

    grain = breakdown or []

    return _build_3m_metrics(
        df_filtered=df_scope,
        df_full=df_scope,
        grain=grain,
    )


# ---------------------------------------------------------
# Pitch evidence builder
# ---------------------------------------------------------

def build_retailer_pitch(
    df: pd.DataFrame,
    target_retailer: str,
    comparison_retailers: list[str],
    states: list[str],
    skus: list[str] | None = None,
) -> dict:
    """
    Builds raw evidence for a new-retailer pitch.

    For each comparison retailer, returns:
        - retailer overall
        - retailer inside selected geography
        - retailer outside selected geography

    Also returns:
        - selected geography overall
        - outside geography
        - total business

    All scopes are also returned by SKU.

    The analytical layer later determines which comparisons
    are useful enough to surface.
    """

    if df is None or df.empty:
        return {}

    # -----------------------------------------------------
    # Optional SKU restriction
    # -----------------------------------------------------

    df_analysis = df.copy()

    if skus:
        df_analysis = df_analysis[
            df_analysis["sku"].isin(skus)
        ].copy()

    df_analysis = add_sku_count(df_analysis)

    # -----------------------------------------------------
    # Overall business
    # -----------------------------------------------------

    overall = _build_3m_metrics(
        df_filtered=df_analysis,
        df_full=df_analysis,
        grain=[],
    )

    overall_by_sku = _build_3m_metrics(
        df_filtered=df_analysis,
        df_full=df_analysis,
        grain=["sku"],
    )

    # -----------------------------------------------------
    # Geography overall
    # -----------------------------------------------------

    df_geography = df_analysis[
        df_analysis["state"].isin(states)
    ].copy()

    geography = _build_3m_metrics(
        df_filtered=df_geography,
        df_full=df_geography,
        grain=[],
    )

    geography_by_sku = _build_3m_metrics(
        df_filtered=df_geography,
        df_full=df_geography,
        grain=["sku"],
    )

    # -----------------------------------------------------
    # Outside geography
    # -----------------------------------------------------

    df_outside_geography = df_analysis[
        ~df_analysis["state"].isin(states)
    ].copy()

    outside_geography = _build_3m_metrics(
        df_filtered=df_outside_geography,
        df_full=df_outside_geography,
        grain=[],
    )

    outside_geography_by_sku = _build_3m_metrics(
        df_filtered=df_outside_geography,
        df_full=df_outside_geography,
        grain=["sku"],
    )

    # -----------------------------------------------------
    # Related retailers — collective
    # -----------------------------------------------------

    df_related_retailers = df_analysis[
        df_analysis["chain"].isin(comparison_retailers)
    ].copy()

    related_retailers_overall = _build_3m_metrics(
        df_filtered=df_related_retailers,
        df_full=df_related_retailers,
        grain=[],
    )

    related_retailers_overall_by_sku = _build_3m_metrics(
        df_filtered=df_related_retailers,
        df_full=df_related_retailers,
        grain=["sku"],
    )

    assortment_by_sku_count = _build_3m_metrics(
        df_filtered=df_analysis,
        df_full=df_analysis,
        grain=["sku_count"],
    )

    assortment_by_sku_and_count = _build_3m_metrics(
        df_filtered=df_analysis,
        df_full=df_analysis,
        grain=["sku", "sku_count"],
    )

    # -----------------------------------------------------
    # Related retailers × selected geography
    # -----------------------------------------------------

    df_related_retailers_geography = df_related_retailers[
        df_related_retailers["state"].isin(states)
    ].copy()

    related_retailers_geography = _build_3m_metrics(
        df_filtered=df_related_retailers_geography,
        df_full=df_related_retailers_geography,
        grain=[],
    )

    related_retailers_geography_by_sku = _build_3m_metrics(
        df_filtered=df_related_retailers_geography,
        df_full=df_related_retailers_geography,
        grain=["sku"],
    )


    # -----------------------------------------------------
    # Related retailers outside selected geography
    # -----------------------------------------------------

    df_related_retailers_outside_geography = df_related_retailers[
        ~df_related_retailers["state"].isin(states)
    ].copy()

    related_retailers_outside_geography = _build_3m_metrics(
        df_filtered=df_related_retailers_outside_geography,
        df_full=df_related_retailers_outside_geography,
        grain=[],
    )

    related_retailers_outside_geography_by_sku = _build_3m_metrics(
        df_filtered=df_related_retailers_outside_geography,
        df_full=df_related_retailers_outside_geography,
        grain=["sku"],
    )

    # -----------------------------------------------------
    # Comparison retailer scopes
    # -----------------------------------------------------

    retailer_results = {}

    for retailer in comparison_retailers:

        # ---------------------------------------------
        # Retailer overall
        # ---------------------------------------------

        df_retailer = df_analysis[
            df_analysis["chain"] == retailer
        ].copy()

        retailer_overall = _build_3m_metrics(
            df_filtered=df_retailer,
            df_full=df_retailer,
            grain=[],
        )

        retailer_overall_by_sku = _build_3m_metrics(
            df_filtered=df_retailer,
            df_full=df_retailer,
            grain=["sku"],
        )

        # ---------------------------------------------
        # Retailer × selected geography
        # ---------------------------------------------

        df_retailer_geography = df_analysis[
            (df_analysis["chain"] == retailer)
            & (df_analysis["state"].isin(states))
        ].copy()

        retailer_geography = _build_3m_metrics(
            df_filtered=df_retailer_geography,
            df_full=df_retailer_geography,
            grain=[],
        )

        retailer_geography_by_sku = _build_3m_metrics(
            df_filtered=df_retailer_geography,
            df_full=df_retailer_geography,
            grain=["sku"],
        )

        # ---------------------------------------------
        # Retailer outside selected geography
        # ---------------------------------------------

        df_retailer_outside_geography = df_analysis[
            (df_analysis["chain"] == retailer)
            & (~df_analysis["state"].isin(states))
        ].copy()

        retailer_outside_geography = _build_3m_metrics(
            df_filtered=df_retailer_outside_geography,
            df_full=df_retailer_outside_geography,
            grain=[],
        )

        retailer_outside_geography_by_sku = _build_3m_metrics(
            df_filtered=df_retailer_outside_geography,
            df_full=df_retailer_outside_geography,
            grain=["sku"],
        )

        retailer_results[retailer] = {
            "overall": retailer_overall,

            "geography":
                retailer_geography,

            "outside_geography":
                retailer_outside_geography,

            "sku_breakdown": {
                "overall":
                    retailer_overall_by_sku,

                "geography":
                    retailer_geography_by_sku,

                "outside_geography":
                    retailer_outside_geography_by_sku,
            },
        }

    # -----------------------------------------------------
    # Return evidence tree
    # -----------------------------------------------------

    return {
        "target_retailer": target_retailer,
        "comparison_retailers": comparison_retailers,
        "states": states,
        "skus": skus or [],

        "overall": overall,

        "geography": geography,

        "outside_geography":
            outside_geography,

        "sku_breakdown": {
            "overall":
                overall_by_sku,

            "geography":
                geography_by_sku,

            "outside_geography":
                outside_geography_by_sku,
        },

        "related_retailers": {
            "overall": related_retailers_overall,

            "geography": related_retailers_geography,

            "outside_geography":
                related_retailers_outside_geography,

            "sku_breakdown": {
                "overall":
                    related_retailers_overall_by_sku,

                "geography":
                    related_retailers_geography_by_sku,

                "outside_geography":
                    related_retailers_outside_geography_by_sku,
            },
        },

        "assortment": {
            "by_sku_count": assortment_by_sku_count,
            "by_sku_and_count": assortment_by_sku_and_count,
        },

        "retailers": retailer_results,
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

    result = build_retailer_pitch(
        df=df,
        target_retailer="PUBLIX",
        comparison_retailers=[
            "SPROUTS",
            "THE FRESH MARKET",
        ],
        states=[
            "FL",
            "GA",
            "AL",
            "SC",
            "NC",
            "TN",
            "VA",
            "KY",
        ],
    )

    cols = [
        "revenue_3m",
        "units_3m",
        "buying_stores_3m",
        "vpo_3m",
        "revenue_l3m_pct",
        "units_l3m_pct",
        "buying_stores_l3m_pct",
        "vpo_l3m_pct",
    ]

    sku_cols = ["sku"] + cols

    def print_section(title, data, columns):
        print("\n")
        print("=" * 90)
        print(title)
        print("=" * 90)

        if data is None or data.empty:
            print("No data")
            return

        print(
            data[columns]
            .round(3)
            .to_string(index=False)
        )


    # -----------------------------------------------------
    # Overall geography
    # -----------------------------------------------------

    print_section(
        "PUBLIX GEOGRAPHY — ALL SELECTED STATES",
        result["geography"],
        cols,
    )

    print_section(
        "OUTSIDE PUBLIX GEOGRAPHY",
        result["outside_geography"],
        cols,
    )

    print_section(
        "PUBLIX GEOGRAPHY — BY SKU",
        result["sku_breakdown"]["geography"],
        sku_cols,
    )


    # -----------------------------------------------------
    # Related retailers — collective
    # -----------------------------------------------------

    print_section(
        "RELATED RETAILERS — OVERALL",
        result["related_retailers"]["overall"],
        cols,
    )

    print_section(
        "RELATED RETAILERS — PUBLIX GEOGRAPHY",
        result["related_retailers"]["geography"],
        cols,
    )

    print_section(
        "RELATED RETAILERS — OUTSIDE PUBLIX GEOGRAPHY",
        result["related_retailers"]["outside_geography"],
        cols,
    )

    print_section(
        "RELATED RETAILERS — OVERALL BY SKU",
        result["related_retailers"]["sku_breakdown"]["overall"],
        sku_cols,
    )

    print_section(
        "RELATED RETAILERS — PUBLIX GEOGRAPHY BY SKU",
        result["related_retailers"]["sku_breakdown"]["geography"],
        sku_cols,
    )

    print_section(
        "RELATED RETAILERS — OUTSIDE PUBLIX GEOGRAPHY BY SKU",
        result["related_retailers"]["sku_breakdown"]["outside_geography"],
        sku_cols,
    )

    print_section(
        "ASSORTMENT — VELOCITY BY SKU COUNT",
        result["assortment"]["by_sku_count"],
        ["sku_count"] + cols,
    )

    print_section(
        "ASSORTMENT — VELOCITY BY SKU + SKU COUNT",
        result["assortment"]["by_sku_and_count"],
        ["sku", "sku_count"] + cols,
    )


    # -----------------------------------------------------
    # Related retailers — individually
    # -----------------------------------------------------

    for retailer, retailer_data in result["retailers"].items():

        print_section(
            f"{retailer} — OVERALL",
            retailer_data["overall"],
            cols,
        )

        print_section(
            f"{retailer} — PUBLIX GEOGRAPHY",
            retailer_data["geography"],
            cols,
        )

        print_section(
            f"{retailer} — OUTSIDE PUBLIX GEOGRAPHY",
            retailer_data["outside_geography"],
            cols,
        )

        print_section(
            f"{retailer} — OVERALL BY SKU",
            retailer_data["sku_breakdown"]["overall"],
            sku_cols,
        )

        print_section(
            f"{retailer} — PUBLIX GEOGRAPHY BY SKU",
            retailer_data["sku_breakdown"]["geography"],
            sku_cols,
        )

        print_section(
            f"{retailer} — OUTSIDE PUBLIX GEOGRAPHY BY SKU",
            retailer_data["sku_breakdown"]["outside_geography"],
            sku_cols,
        )
import pandas as pd
from backend.metrics.metric_helpers import get_current_period
from backend.metrics.metric_callers import (
    calculate_metric,
    compare_metric,
)


def _filter_pitch_scope(
    df,
    states=None,
    retailers=None,
    skus=None,
):
    if df is None or df.empty:
        return pd.DataFrame()

    result = df.copy()

    if states:
        result = result[
            result["state"].isin(states)
        ].copy()

    if retailers:
        result = result[
            result["chain"].isin(retailers)
        ].copy()

    if skus:
        result = result[
            result["sku"].isin(skus)
        ].copy()

    return result


def _build_pitch_metrics(
    df_full,
    active_pods_full,
    grain=None,
    end_month=None,
):
    """
    Builds the retailer-pitch metric bundle using only the
    canonical comparison layer.

    This helper does NOT calculate periods or metric math.
    It only calls compare_metric() and shapes the results
    into the columns expected by the pitch evidence tree.
    """

    grain = grain or []

    if df_full is None or df_full.empty:
        return pd.DataFrame()

    metric_columns = {
        "units": {
            "current": "units_3m",
            "comparison": "units_l3m",
            "pct": "units_l3m_pct",
        },
        "buying_stores": {
            "current": "buying_stores_3m",
            "comparison": "buying_stores_l3m",
            "pct": "buying_stores_l3m_pct",
        },
        "velocity": {
            "current": "vpo_3m",
            "comparison": "vpo_l3m",
            "pct": "vpo_l3m_pct",
        },
    }

    result = None

    for metric_name, columns in metric_columns.items():

        metric_result = compare_metric(
            df=df_full,
            df_full=df_full,
            active_pods_df=active_pods_full,
            metric_name=metric_name,
            period="L3M",
            comparison="PP",
            group_cols=grain,
            end_month=end_month,
        )

        metric_result = metric_result.rename(
            columns={
                "value_current": columns["current"],
                "value_comparison": columns["comparison"],
                "pct_change": columns["pct"],
            }
        )

        metric_result = metric_result[
            grain
            + [
                columns["current"],
                columns["comparison"],
                columns["pct"],
            ]
        ]

        if result is None:
            result = metric_result
            continue

        if grain:
            result = result.merge(
                metric_result,
                on=grain,
                how="outer",
            )
        else:
            result = pd.concat(
                [
                    result.reset_index(drop=True),
                    metric_result.reset_index(drop=True),
                ],
                axis=1,
            )

    return result


def _build_pitch_scope(
    df_full,
    active_pods_full,
    grain=None,
    states=None,
    retailers=None,
    skus=None,
    end_month=None,
):
    """
    Applies the same business scope to transactions and active PODs,
    then asks the canonical metric layer for the comparison metrics.
    """

    df_scope = _filter_pitch_scope(
        df_full,
        states=states,
        retailers=retailers,
        skus=skus,
    )

    active_pods_scope = _filter_pitch_scope(
        active_pods_full,
        states=states,
        retailers=retailers,
        skus=skus,
    )

    return _build_pitch_metrics(
        df_full=df_scope,
        active_pods_full=active_pods_scope,
        grain=grain or [],
        end_month=end_month,
    )


def build_scope_analysis(
    df_full: pd.DataFrame,
    active_pods_full: pd.DataFrame,
    states: list[str] | None = None,
    retailers: list[str] | None = None,
    skus: list[str] | None = None,
    breakdown: list[str] | None = None,
    end_month=None,
) -> pd.DataFrame:
    """
    Calculates performance for any selected pitch scope using the
    canonical metric architecture.
    """
    if df_full is None or df_full.empty:
        return pd.DataFrame()
    return _build_pitch_scope(
        df_full=df_full,
        active_pods_full=active_pods_full,
        grain=breakdown or [],
        states=states,
        retailers=retailers,
        skus=skus,
        end_month=end_month,
    )


def _add_active_skus_snapshot(
    df,
    active_pods_full,
    end_month=None,
):
    """
    Adds each store's active assortment size at the requested snapshot.

    No end_month:
        current month

    end_month supplied:
        that month

    This uses active assortment at the current/requested snapshot.
    """

    if df is None or df.empty:
        return df

    snapshot_month = (
        pd.Period(end_month, freq="M")
        if end_month is not None
        else get_current_period(include_current_month=True)
    )

    snapshot_active_pods = active_pods_full[
        active_pods_full["month_year"] == snapshot_month
    ].copy()

    active_skus = calculate_metric(
        metric_name="active_skus",
        df_filtered=df,
        active_pods_df=snapshot_active_pods,
        group_cols=["coded_customer"],
    )

    active_skus = active_skus.rename(
        columns={
            "value": "active_skus",
        }
    )

    return df.merge(
        active_skus[
            [
                "coded_customer",
                "active_skus",
            ]
        ],
        on="coded_customer",
        how="left",
    )


def build_retailer_pitch(
    df_full: pd.DataFrame,
    active_pods_full: pd.DataFrame,
    target_retailer: str,
    comparison_retailers: list[str],
    states: list[str],
    skus: list[str] | None = None,
    end_month=None,
) -> dict:
    """
    Builds retailer-pitch evidence using the canonical metric architecture.

    Metric math and period comparisons are owned by compare_metric().

    This function owns only:
        - pitch scope construction
        - evidence-tree construction
        - current/as-of assortment classification
    """

    if df_full is None or df_full.empty:
        return {}

    # -----------------------------------------------------
    # Optional SKU restriction
    # -----------------------------------------------------

    df_analysis = _filter_pitch_scope(
        df_full,
        skus=skus,
    )

    active_pods_analysis = _filter_pitch_scope(
        active_pods_full,
        skus=skus,
    )

    # -----------------------------------------------------
    # Overall business
    # -----------------------------------------------------

    overall = _build_pitch_scope(
        df_full=df_analysis,
        active_pods_full=active_pods_analysis,
        end_month=end_month,
    )

    overall_by_sku = _build_pitch_scope(
        df_full=df_analysis,
        active_pods_full=active_pods_analysis,
        grain=["sku"],
        end_month=end_month,
    )

    # -----------------------------------------------------
    # Geography
    # -----------------------------------------------------

    geography = _build_pitch_scope(
        df_full=df_analysis,
        active_pods_full=active_pods_analysis,
        states=states,
        end_month=end_month,
    )

    geography_by_sku = _build_pitch_scope(
        df_full=df_analysis,
        active_pods_full=active_pods_analysis,
        grain=["sku"],
        states=states,
        end_month=end_month,
    )

    # -----------------------------------------------------
    # Outside geography
    # -----------------------------------------------------

    df_outside_geography = df_analysis[
        ~df_analysis["state"].isin(states)
    ].copy()

    active_pods_outside_geography = active_pods_analysis[
        ~active_pods_analysis["state"].isin(states)
    ].copy()

    outside_geography = _build_pitch_metrics(
        df_full=df_outside_geography,
        active_pods_full=active_pods_outside_geography,
        end_month=end_month,
    )

    outside_geography_by_sku = _build_pitch_metrics(
        df_full=df_outside_geography,
        active_pods_full=active_pods_outside_geography,
        grain=["sku"],
        end_month=end_month,
    )

    # -----------------------------------------------------
    # Related retailers — collective
    # -----------------------------------------------------

    related_retailers_overall = _build_pitch_scope(
        df_full=df_analysis,
        active_pods_full=active_pods_analysis,
        retailers=comparison_retailers,
        end_month=end_month,
    )

    related_retailers_overall_by_sku = _build_pitch_scope(
        df_full=df_analysis,
        active_pods_full=active_pods_analysis,
        grain=["sku"],
        retailers=comparison_retailers,
        end_month=end_month,
    )

    related_retailers_geography = _build_pitch_scope(
        df_full=df_analysis,
        active_pods_full=active_pods_analysis,
        states=states,
        retailers=comparison_retailers,
        end_month=end_month,
    )

    related_retailers_geography_by_sku = _build_pitch_scope(
        df_full=df_analysis,
        active_pods_full=active_pods_analysis,
        grain=["sku"],
        states=states,
        retailers=comparison_retailers,
        end_month=end_month,
    )

    df_related_outside = df_analysis[
        df_analysis["chain"].isin(comparison_retailers)
        & ~df_analysis["state"].isin(states)
    ].copy()

    active_pods_related_outside = active_pods_analysis[
        active_pods_analysis["chain"].isin(comparison_retailers)
        & ~active_pods_analysis["state"].isin(states)
    ].copy()

    related_retailers_outside_geography = _build_pitch_metrics(
        df_full=df_related_outside,
        active_pods_full=active_pods_related_outside,
        end_month=end_month,
    )

    related_retailers_outside_geography_by_sku = _build_pitch_metrics(
        df_full=df_related_outside,
        active_pods_full=active_pods_related_outside,
        grain=["sku"],
        end_month=end_month,
    )

    # -----------------------------------------------------
    # Assortment
    #
    # Assortment semantics:
    # stores are classified by active SKU count at the
    # current/requested snapshot.
    # -----------------------------------------------------

    df_assortment = _add_active_skus_snapshot(
        df=df_analysis,
        active_pods_full=active_pods_analysis,
        end_month=end_month,
    )

    active_pods_assortment = _add_active_skus_snapshot(
        df=active_pods_analysis,
        active_pods_full=active_pods_analysis,
        end_month=end_month,
    )

    assortment_by_active_skus = _build_pitch_metrics(
        df_full=df_assortment,
        active_pods_full=active_pods_assortment,
        grain=["active_skus"],
        end_month=end_month,
    )

    assortment_by_sku_and_active_skus = _build_pitch_metrics(
        df_full=df_assortment,
        active_pods_full=active_pods_assortment,
        grain=["sku", "active_skus"],
        end_month=end_month,
    )

    # -----------------------------------------------------
    # Individual comparison retailers
    # -----------------------------------------------------

    retailer_results = {}

    for retailer in comparison_retailers:

        retailer_overall = _build_pitch_scope(
            df_full=df_analysis,
            active_pods_full=active_pods_analysis,
            retailers=[retailer],
            end_month=end_month,
        )

        retailer_overall_by_sku = _build_pitch_scope(
            df_full=df_analysis,
            active_pods_full=active_pods_analysis,
            grain=["sku"],
            retailers=[retailer],
            end_month=end_month,
        )

        retailer_geography = _build_pitch_scope(
            df_full=df_analysis,
            active_pods_full=active_pods_analysis,
            retailers=[retailer],
            states=states,
            end_month=end_month,
        )

        retailer_geography_by_sku = _build_pitch_scope(
            df_full=df_analysis,
            active_pods_full=active_pods_analysis,
            grain=["sku"],
            retailers=[retailer],
            states=states,
            end_month=end_month,
        )

        df_retailer_outside = df_analysis[
            (df_analysis["chain"] == retailer)
            & (~df_analysis["state"].isin(states))
        ].copy()

        active_pods_retailer_outside = active_pods_analysis[
            (active_pods_analysis["chain"] == retailer)
            & (~active_pods_analysis["state"].isin(states))
        ].copy()

        retailer_outside_geography = _build_pitch_metrics(
            df_full=df_retailer_outside,
            active_pods_full=active_pods_retailer_outside,
            end_month=end_month,
        )

        retailer_outside_geography_by_sku = _build_pitch_metrics(
            df_full=df_retailer_outside,
            active_pods_full=active_pods_retailer_outside,
            grain=["sku"],
            end_month=end_month,
        )

        retailer_results[retailer] = {
            "overall": retailer_overall,
            "geography": retailer_geography,
            "outside_geography": retailer_outside_geography,
            "sku_breakdown": {
                "overall": retailer_overall_by_sku,
                "geography": retailer_geography_by_sku,
                "outside_geography": retailer_outside_geography_by_sku,
            },
        }

    # -----------------------------------------------------
    # Evidence tree
    # -----------------------------------------------------

    return {
        "target_retailer": target_retailer,
        "comparison_retailers": comparison_retailers,
        "states": states,
        "skus": skus or [],

        "overall": overall,

        "geography": geography,

        "outside_geography": outside_geography,

        "sku_breakdown": {
            "overall": overall_by_sku,
            "geography": geography_by_sku,
            "outside_geography": outside_geography_by_sku,
        },

        "related_retailers": {
            "overall": related_retailers_overall,
            "geography": related_retailers_geography,
            "outside_geography": related_retailers_outside_geography,

            "sku_breakdown": {
                "overall": related_retailers_overall_by_sku,
                "geography": related_retailers_geography_by_sku,
                "outside_geography": related_retailers_outside_geography_by_sku,
            },
        },

        "assortment": {
            "by_active_skus": assortment_by_active_skus,
            "by_sku_and_active_skus": assortment_by_sku_and_active_skus,
        },

        "retailers": retailer_results,
    }

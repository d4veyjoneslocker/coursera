import pandas as pd

from backend.metrics.metric_callers import compare_metric


def _build_metrics(
    df: pd.DataFrame,
    active_pods_df: pd.DataFrame,
    grain: list[str],
    period: str = "L3M",
    comparison: str = "PP",
) -> pd.DataFrame:
    """
    NEW architecture.

    Metric math is owned by canonical metric calculators.
    Period filtering and comparisons are owned by compare_metric().
    """

    if df is None or df.empty:
        return pd.DataFrame()

    metrics = {
        "units": "units",
        "buying_stores": "buying_stores",
        "velocity": "vpo",
    }

    result = None

    for metric_name, output_name in metrics.items():
        metric_result = compare_metric(
            df=df,
            df_full=df,
            active_pods_df=active_pods_df,
            metric_name=metric_name,
            period=period,
            comparison=comparison,
            group_cols=grain,
        )

        metric_result = metric_result.rename(
            columns={
                "value_current": output_name,
                "value_comparison": f"{output_name}_comparison",
                "abs_change": f"{output_name}_abs_change",
                "pct_change": f"{output_name}_pct_change",
            }
        )

        keep_cols = grain + [
            output_name,
            f"{output_name}_comparison",
            f"{output_name}_abs_change",
            f"{output_name}_pct_change",
        ]

        metric_result = metric_result[keep_cols]

        if result is None:
            result = metric_result

        elif grain:
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

    return result if result is not None else pd.DataFrame()


def build_brand_momentum(
    df: pd.DataFrame,
    active_pods_df: pd.DataFrame,
    skus: list[str] | None = None,
    period: str = "L3M",
    comparison: str = "PP",
) -> dict:
    """
    NEW architecture version of build_brand_momentum().
    """

    if df is None or df.empty:
        return {}

    df_analysis = df.copy()
    active_pods_analysis = active_pods_df.copy()

    if skus:
        df_analysis = df_analysis[
            df_analysis["sku"].isin(skus)
        ].copy()

        active_pods_analysis = active_pods_analysis[
            active_pods_analysis["sku"].isin(skus)
        ].copy()

    if df_analysis.empty:
        return {}

    overall = _build_metrics(
        df_analysis,
        active_pods_analysis,
        [],
        period,
        comparison,
    )

    by_sku = _build_metrics(
        df_analysis,
        active_pods_analysis,
        ["sku"],
        period,
        comparison,
    )

    by_chain = _build_metrics(
        df_analysis,
        active_pods_analysis,
        ["chain"],
        period,
        comparison,
    )

    by_state = _build_metrics(
        df_analysis,
        active_pods_analysis,
        ["state"],
        period,
        comparison,
    )

    by_channel = _build_metrics(
        df_analysis,
        active_pods_analysis,
        ["channel"],
        period,
        comparison,
    )

    by_chain_sku = _build_metrics(
        df_analysis,
        active_pods_analysis,
        ["chain", "sku"],
        period,
        comparison,
    )

    by_state_sku = _build_metrics(
        df_analysis,
        active_pods_analysis,
        ["state", "sku"],
        period,
        comparison,
    )

    by_channel_sku = _build_metrics(
        df_analysis,
        active_pods_analysis,
        ["channel", "sku"],
        period,
        comparison,
    )

    return {
        "skus": skus or [],
        "period": period,
        "comparison": comparison,

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
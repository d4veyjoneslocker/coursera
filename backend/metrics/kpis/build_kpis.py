from backend.metrics.metric_callers import calculate_metric, compare_metric
from backend.metrics.metric_helpers import safe_float, safe_int, get_metric_value, get_current_period, resolve_period


def build_kpis(df, df_full, active_pods_df, active_pods_full, end_month=None):
    # Selected-period totals
    total_units = get_metric_value(
        calculate_metric(
            metric_name="units",
            df_filtered=df,
            active_pods_df=active_pods_df,
            group_cols=[],
        )
    )

    total_buyers = get_metric_value(
        calculate_metric(
            metric_name="buying_stores",
            df_filtered=df,
            active_pods_df=active_pods_df,
            group_cols=[],
        )
    )

    # Total PODs is a current-state KPI, so use the current month
    # from the full active-POD spine.
    snapshot_month = (
        end_month
        if end_month is not None
        else get_current_period(include_current_month=True)
    )

    snapshot_active_pods_df = active_pods_full[
        active_pods_full["month_year"] == snapshot_month
    ].copy()

    total_pods = get_metric_value(
        calculate_metric(
            metric_name="active_pods",
            df_filtered=df,
            active_pods_df=snapshot_active_pods_df,
            group_cols=[],
        )
    )

    total_velocity = get_metric_value(
        calculate_metric(
            metric_name="velocity",
            df_filtered=df,
            active_pods_df=active_pods_df,
            group_cols=[],
        )
    )

    avg_skus = get_metric_value(
        calculate_metric(
            metric_name="average_skus_per_store",
            df_filtered=df,
            active_pods_df=active_pods_df,
            group_cols=[],
        )
    )

    total_reorder_rate = get_metric_value(
        calculate_metric(
            metric_name="reorder_rate",
            df_filtered=df,
            active_pods_df=active_pods_df,
            group_cols=[],
        )
    )

    # L1M comparisons
    l1m_units = compare_metric(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_full,
        metric_name="units",
        period="L1M",
        comparison="PP",
        group_cols=[],
        end_month=end_month,
    )

    l1m_buyers = compare_metric(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_full,
        metric_name="buying_stores",
        period="L1M",
        comparison="PP",
        group_cols=[],
        end_month=end_month,
    )

    l1m_new_pods = compare_metric(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_full,
        metric_name="new_pods",
        period="L1M",
        comparison="PP",
        group_cols=[],
        end_month=end_month,
    )

    l1m_velocity = compare_metric(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_full,
        metric_name="velocity",
        period="L1M",
        comparison="PP",
        group_cols=[],
        end_month=end_month,
    )

    l1m_reorder_rate = compare_metric(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_full,
        metric_name="reorder_rate",
        period="L1M",
        comparison="PP",
        group_cols=[],
        end_month=end_month,
    )

    # L3M comparisons
    l3m_units = compare_metric(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_full,
        metric_name="units",
        period="L3M",
        comparison="PP",
        group_cols=[],
        end_month=end_month,
    )

    l3m_buyers = compare_metric(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_full,
        metric_name="buying_stores",
        period="L3M",
        comparison="PP",
        group_cols=[],
        end_month=end_month,
    )

    l3m_new_pods = compare_metric(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_full,
        metric_name="new_pods",
        period="L3M",
        comparison="PP",
        group_cols=[],
        end_month=end_month,
    )

    l3m_velocity = compare_metric(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_full,
        metric_name="velocity",
        period="L3M",
        comparison="PP",
        group_cols=[],
        end_month=end_month,
    )

    l3m_reorder_rate = compare_metric(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_full,
        metric_name="reorder_rate",
        period="L3M",
        comparison="PP",
        group_cols=[],
        end_month=end_month,
    )

    return {
        "units_kpis": [
            {
                "key": "total_units",
                "title": "Total Units",
                "value": total_units,
            },
            {
                "key": "l1m_units",
                "title": "L1M Units",
                "value": get_metric_value(l1m_units, "value_current"),
                "sideValue": get_metric_value(l1m_units, "pct_change"),
            },
            {
                "key": "l3m_units",
                "title": "L3M Units",
                "value": get_metric_value(l3m_units, "value_current"),
                "sideValue": get_metric_value(l3m_units, "pct_change"),
            },
        ],
        "buyers_kpis": [
            {
                "key": "total_buyers",
                "title": "Total Buyers",
                "value": total_buyers,
            },
            {
                "key": "l1m_buyers",
                "title": "L1M Buyers",
                "value": get_metric_value(l1m_buyers, "value_current"),
                "sideValue": get_metric_value(l1m_buyers, "pct_change"),
            },
            {
                "key": "l3m_buyers",
                "title": "L3M Buyers",
                "value": get_metric_value(l3m_buyers, "value_current"),
                "sideValue": get_metric_value(l3m_buyers, "pct_change"),
            },
        ],
        "pod_kpis": [
            {
                "key": "total_pods",
                "title": "Total PODs",
                "value": total_pods,
            },
            {
                "key": "l1m_new_pods",
                "title": "L1M New PODs",
                "value": get_metric_value(l1m_new_pods, "value_current"),
                "sideValue": get_metric_value(l1m_new_pods, "pct_change"),
            },
            {
                "key": "l3m_new_pods",
                "title": "L3M New PODs",
                "value": get_metric_value(l3m_new_pods, "value_current"),
                "sideValue": get_metric_value(l3m_new_pods, "pct_change"),
            },
        ],
        "velocity_kpis": [
            {
                "key": "total_velocity",
                "title": "Velocity",
                "value": total_velocity,
            },
            {
                "key": "l1m_velocity",
                "title": "L1M Velocity",
                "value": get_metric_value(l1m_velocity, "value_current"),
                "sideValue": get_metric_value(l1m_velocity, "pct_change"),
            },
            {
                "key": "l3m_velocity",
                "title": "L3M Velocity",
                "value": get_metric_value(l3m_velocity, "value_current"),
                "sideValue": get_metric_value(l3m_velocity, "pct_change"),
            },
        ],
        "avg_skus_per_store": {
            "skus_per_store": {
                "key": "skus_per_store",
                "title": "Avg. SKUs per Store",
                "value": avg_skus,
            }
        },
        "count_channel": {
            "channel_count": {
                "key": "channel_count",
                "title": "Channel Count",
                "value": df["channel"].nunique(),
            }
        },
        "reorder_kpis": [
            {
                "key": "total_reorder_rate",
                "title": "Ttl reorder rate",
                "value": safe_float(total_reorder_rate),
            },
            {
                "key": "l1m_reorder_rate",
                "title": "L1M reorder rate",
                "value": safe_float(get_metric_value(l1m_reorder_rate, "value_current")),
                "sideValue": safe_float(get_metric_value(l1m_reorder_rate, "abs_change")),
                "sideLabel": "vs L1M",
                "sideType": "absolute",
            },
            {
                "key": "l3m_reorder_rate",
                "title": "L3M reorder rate",
                "value": safe_float(get_metric_value(l3m_reorder_rate, "value_current")),
                "sideValue": safe_float(get_metric_value(l3m_reorder_rate, "abs_change")),
                "sideLabel": "vs L3M",
                "sideType": "absolute",
            },
        ],
    }
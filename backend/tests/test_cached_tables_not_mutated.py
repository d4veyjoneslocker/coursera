import pandas as pd
from pandas.util import hash_pandas_object
from backend.data_pipeline.table_loader import load_org_tables
from backend.filters.filter_table import filter_table
from backend.metrics.monthly_metric_calculators import calculate_monthly_units
from backend.serving.api_helpers import prep_monthly_graph, clean_for_json
from backend.filters.filter_table import filter_table
from backend.filters.filters import get_filters, generate_filter_api
from backend.data_pipeline.table_loader import load_org_tables
from backend.metrics.monthly_metric_calculators import calculate_monthly_buying_stores, calculate_monthly_reorder_rate
from backend.metrics.metric_tables import store_performance, kpi_monthly_table, status_counts_dict
from backend.metrics.metric_calculators import calculate_units
from backend.metrics.kpis.store_health_kpis import buying_kpis, reorder_kpis, count_channels
from backend.serving.api_helpers import clean_for_json, prep_monthly_graph, remove_time_filters, filter_and_recompute_features
from backend.filters.filter_table import filter_table
from backend.filters.filters import get_filters, generate_filter_api
from backend.metrics.metric_calculators import calculate_units
from backend.serving.api_helpers import clean_for_json, prep_monthly_graph, remove_time_filters
from backend.metrics.metric_tables import chain_table, kpi_monthly_table
from backend.metrics.kpis.overview_kpis import unit_kpis, buying_kpis, pod_kpis, vpo_kpis, count_channels, avg_skus_per_store
from backend.data_pipeline.table_loader import load_org_tables
from backend.metrics.monthly_metric_calculators import (
    calculate_monthly_units,
    calculate_monthly_active_pods,
    calculate_monthly_buying_stores,
    calculate_monthly_vpo
)



def df_signature(df: pd.DataFrame):
    return {
        "shape": df.shape,
        "columns": tuple(df.columns),
        "fingerprint": int(hash_pandas_object(df, index=True).sum()),
    }

def test_tables_not_mutated():
    features_df = load_org_tables("default_org")

    features_df_before = df_signature(features_df)

    filters = {}

    df = filter_table(features_df, **filters)

    non_time_filters=remove_time_filters(filters)
    df_all_time = filter_table(features_df, **non_time_filters)

    result = store_performance(df, df_all_time)

    result = clean_for_json(result)


    assert result is not None
    assert df_signature(features_df) == features_df_before
from backend.metrics.metric_tables import store_performance

def chain_struggling_store_detail_table(df, df_all_time, chain):
    table = store_performance(df, df_all_time)

    table = table[
        (table["chain"] == chain) &
        (table["status"] == "Struggling")
    ].copy()

    return table.sort_values("units", ascending=False)
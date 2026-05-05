from backend.metrics.metric_tables import store_performance

def chain_struggling_store_detail_table(df, df_all_time, chain):
    table = store_performance(df, df_all_time)

    print("1. Does chain exist?")
    print((table["chain"] == chain).sum())

    print("2. Are there struggling rows at all?")
    print((table["status"] == "Struggling").sum())

    print("3. Do they overlap?")
    print(
        ((table["chain"] == chain) &
        (table["status"] == "Struggling")).sum()
    )

    table = table[
        (table["chain"] == chain) &
        (table["status"] == "Struggling")
    ].copy()

    print("1. Does chain exist?")
    print((table["chain"] == chain).sum())

    print("2. Are there struggling rows at all?")
    print((table["status"] == "Struggling").sum())

    print("3. Do they overlap?")
    print(
        ((table["chain"] == chain) &
        (table["status"] == "Struggling")).sum()
    )


    return table.sort_values("units", ascending=False)
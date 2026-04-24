def validate_data(df):
    errors = []

    # duplicate store-sku-month
    dupes = (
        df.groupby(["coded_customer", "sku", "month_year"])
        .size()
        .reset_index(name="row_count")
    )
    dupes = dupes[dupes["row_count"] > 1]

    if not dupes.empty:
        # merge back to get full rows
        dupes_full = df.merge(
            dupes[["coded_customer", "sku", "month_year"]],
            on=["coded_customer", "sku", "month_year"],
            how="inner"
        )

        dupes_full.to_csv("duplicate_rows.csv", index=False)

        errors.append("Duplicate store-SKU-month rows found (saved to duplicate_rows.csv)")

    return errors
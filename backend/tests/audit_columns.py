def audit_data(df):
    print("\n🔍 DATA AUDIT\n")

    # Channel distribution
    print("Channel breakdown:")
    print(df["channel"].value_counts(dropna=False), "\n")

    # SKU count
    print("Unique SKUs:", df["sku"].nunique())

    # Stores
    print("Unique stores:", df["coded_customer"].nunique())

    # Missing values
    print("\nMissing values:")
    print(df.isna().sum(), "\n")

    # Weird strings (leading/trailing spaces)
    print("Unique channel values:")
    print(df["channel"].unique())
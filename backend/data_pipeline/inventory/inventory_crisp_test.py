from backend.data_pipeline.unfi_pipeline_crisp import pull_crisp_data


df = pull_crisp_data(
    account_id="82090",
    connector_id="9781",
    username="ZDKKoOZnAmOkdKAAexRu",
    password="1dZ6Z&X#1d9vYVC8Gb3*eygfzoP3W1",
    table="Direct_Unfi_Insights_Natural_Quantity_On_Hand_And_On_Order_By_Product_By_Dc",
)

print(df.columns.tolist())
print(df.head())

df.to_csv(
    "backend/data/default_org/raw/inventory/unfi_inventory_inspection.csv",
    index=False,
)
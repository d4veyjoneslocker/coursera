from crisp_data_pull import pull_crisp_data
from transforms.kehe import transform_kehe_full_pod_vendor
from transforms.unfi import transform_unfi_natural_vendor_sales
from transforms.combine_sources  import combine_distributors
from data_validation.phase_1 import flag_dupes
from metrics.core_metrics import monthly_summary
from metrics.features import add_features
from metrics.core_metrics import sku_mix
from metrics.core_metrics import chain_table
import os
from dotenv import load_dotenv


load_dotenv()

account_id_kehe = os.getenv("KEHE_ACCOUNT_ID")
connector_id_kehe = os.getenv("KEHE_CONNECTOR_ID")
username_kehe = os.getenv("KEHE_USERNAME")
password_kehe = os.getenv("KEHE_PASSWORD")

account_id_unfi = os.getenv("UNFI_ACCOUNT_ID")
connector_id_unfi = os.getenv("UNFI_CONNECTOR_ID")
username_unfi = os.getenv("UNFI_USERNAME")
password_unfi = os.getenv("UNFI_PASSWORD")


raw_kehe_df = pull_crisp_data(account_id_kehe, connector_id_kehe, username_kehe, password_kehe, table="Kehe_Full_Pod_Vendor")
raw_unfi_df = pull_crisp_data(account_id_unfi, connector_id_unfi, username_unfi, password_unfi, table="Direct_Unfi_Insights_Natural_Vendor_Sales_Customer_Details_Weekly")


clean_kehe_df = transform_kehe_full_pod_vendor(raw_kehe_df)
clean_unfi_df = transform_unfi_natural_vendor_sales(raw_unfi_df)
combined_df = combine_distributors(clean_kehe_df, clean_unfi_df)

combined_w_features = add_features(combined_df)

#print("reorder_flag" in combined_w_features.columns)


monthly_summary = monthly_summary(combined_w_features, combined_w_features)
#sku_mix = sku_mix(combined_w_features)
chain = chain_table(combined_w_features, combined_w_features)

monthly_summary.to_parquet("monthly_summary.parquet", index=False)
#sku_mix.to_parquet("sku_mix.parquet", index=False)
chain.to_parquet("chain.parquet", index=False)





#clean_kehe_df.to_csv("kehe_output.csv", index=False)
#clean_unfi_df.to_csv("unfi_output.csv", index=False)
#combined_df.to_csv("combined_output.csv", index=False)


#flag_dupes(combined_df)
print("files created")
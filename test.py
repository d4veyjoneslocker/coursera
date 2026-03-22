from crisp_data_pull_generic import pull_crisp_data
from transforms.kehe import transform_kehe_full_pod_vendor
from transforms.unfi import transform_unfi_natural_vendor_sales
from transforms.combine_sources  import combine_distributors
from data_validation.phase_1 import flag_dupes
from metrics.core_metrics import monthly_summary


account_id_kehe = 82090
connector_id_kehe = 9322
username_kehe = "sQfFtSIuRDy9tO4Ea4Cm"
password_kehe = "BPaz30r6LiWbi%XI#+l*Qn7OP^rmIh"

account_id_unfi = 82090
connector_id_unfi = 9332
username_unfi = "wORkw0MEBvwJl7lyU0Cu"
password_unfi = "zklW)Amo(YY3yGtG2o)t&jgdHB%&t_"


raw_kehe_df = pull_crisp_data(account_id_kehe, connector_id_kehe, username_kehe, password_kehe, table="Kehe_Full_Pod_Vendor")
raw_unfi_df = pull_crisp_data(account_id_unfi, connector_id_unfi, username_unfi, password_unfi, table="Direct_Unfi_Insights_Natural_Vendor_Sales_Customer_Details_Weekly")


clean_kehe_df = transform_kehe_full_pod_vendor(raw_kehe_df)
clean_unfi_df = transform_unfi_natural_vendor_sales(raw_unfi_df)
combined_df = combine_distributors(clean_kehe_df, clean_unfi_df)

summary_test = monthly_summary(combined_df, combined_df)

summary_test.to_csv("monthly_summary.csv", index=False)

#clean_kehe_df.to_csv("kehe_output.csv", index=False)
#clean_unfi_df.to_csv("unfi_output.csv", index=False)
#combined_df.to_csv("combined_output.csv", index=False)


#flag_dupes(combined_df)
print("files created")
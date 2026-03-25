import pandas as pd
from data_validation.phase_1 import validate_first_pod_flag


def add_features(df):

    df["first_month_purchased"] = (
        df.groupby("coded_customer")["month_year"].transform("min")
    )

    df["last_month_purchased"] = (
        df.groupby("coded_customer")["month_year"].transform("max")
    )

    df["second_to_last_month_purchased"] = (
    df.groupby("coded_customer")["month_year"]
      .transform(lambda x: x.nlargest(2).iloc[-1] if len(x) > 1 else pd.NaT)
    )

    df["first_store_flag"] = (
        df["month_year"] == df["first_month_purchased"]
    )

    df["first_month_purchased_sku"] = (
        df.groupby("pod_helper")["month_year"].transform("min")
    )

    df["first_pod_flag"] = (
        df["month_year"] == df["first_month_purchased_sku"]
    )

    # ADD THIS TEST BACK IN

    #validate_first_pod_flag(df)

    return df


    # ADD STATUS METRIC



# buying stores (distinct count)
# count (POD count)

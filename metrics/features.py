import pandas as pd
from data_validation.phase_1 import validate_first_pod_flag
import numpy as np


def add_features(df):

    df["first_month_purchased"] = (
        df.groupby("coded_customer")["month_year"].transform("min")
    )

    df["last_month_purchased"] = (
        df.groupby("coded_customer")["month_year"].transform("max")
    )

    df["second_to_last_month_purchased"] = (
        df.groupby("coded_customer")["month_year"]
        .transform(
            lambda x: (
                x.drop_duplicates().nlargest(2).iloc[-1]
                if len(x.drop_duplicates()) > 1
                else pd.NaT
            )
    )
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

    df["reorder_flag"] = ~df["first_store_flag"]

    df["reorder_flag_pod"] = ~df["first_pod_flag"]

    df["count"] = 1

    # ADD THIS TEST BACK IN

    #validate_first_pod_flag(df)

    return df

def add_month_features(df):

    df["first_month_purchased"] = (
        df.groupby("coded_customer")["month_year"].transform("min")
    )

    df["last_month_purchased"] = (
        df.groupby("coded_customer")["month_year"].transform("max")
    )

    df["second_to_last_month_purchased"] = (
        df.groupby("coded_customer")["month_year"]
        .transform(
            lambda x: (
                x.drop_duplicates().nlargest(2).iloc[-1]
                if len(x.drop_duplicates()) > 1
                else pd.NaT
            )
    )
    )

    df["first_store_flag"] = (
        df["month_year"] == df["first_month_purchased"]
    )


    df["reorder_flag"] = np.where(
        ~df["first_store_flag"],1,
        0
    )


    # ADD THIS TEST BACK IN

    #validate_first_pod_flag(df)

    return df


    # ADD STATUS METRIC



# buying stores (distinct count)
# count (POD count)

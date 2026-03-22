import pandas as pd


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

    # ADD STATUS METRIC



# buying stores (distinct count)
# count (POD count)


def calculate_monthly_active_pods(df):

    result = (
        df.groupby("month_year", as_index=False)
        .agg(new_pods=("first_pod_flag", "sum"))
        .sort_values("month_year")
    )

    result["value"] = result["new_pods"].cumsum()
    result["month_year"] = result["month_year"].astype(str)

    return result[["month_year", "value"]]

def calculate_vpo(df):

    result = (
        df.groupby("month_year", as_index=False)
        .agg(
            new_pods = ("first_pod_flag", "sum"),
            volume = ("units", "sum")
            )
        .sort_values("month_year")
    )

    result["active_pods"] = result["new_pods"].cumsum()

    result["value"] = result["volume"]/result["active_pods"]/4
    result["month_year"] = result["month_year"].astype(str)

    return result[["month_year", "value"]]
# PROB MOVE THESE TWO FUNCTIONS SOMEWHERE ELSE

from backend.metrics.metric_helpers import grouped_cumsum
    
def calculate_reorder_rate(df):
    denom = df["total_buyers"] - df["new_buyers"]

    result = df["repeat_buyers"] / denom

    return result.replace([float("inf"), -float("inf")], None)

# ------------------------------------------------------------------------

def calculate_monthly_revenue(df, group_cols):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    if "month_year" not in group_cols:
        group_cols = ["month_year"] + group_cols

    result = (
        df.groupby(group_cols, as_index=False)
        .agg(revenue=("revenue", "sum"))
    )

    return result

def calculate_monthly_units(df, group_cols):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    if "month_year" not in group_cols:
        group_cols = ["month_year"] + group_cols

    result = (
        df.groupby(group_cols, as_index=False)
        .agg(units=("units", "sum"))
    )

    return result

def calculate_monthly_buying_stores(df, group_cols):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    if "month_year" not in group_cols:
        group_cols = ["month_year"] + group_cols

    result = (
        df.groupby(group_cols, as_index=False)
        .agg(buying_stores=("coded_customer", "nunique"))
    )

    return result

def calculate_monthly_active_pods(df, group_cols):
    if isinstance(group_cols, str):
        group_cols = [group_cols]
    
    if "month_year" in group_cols:
        group_cols = [c for c in group_cols if c != "month_year"] + ["month_year"]
    else:
        group_cols = group_cols + ["month_year"]

    result = (
        df.groupby(group_cols, as_index=False)
        .agg(new_pods=("first_pod_flag", "sum"))
        .sort_values(group_cols)
    )

    result["active_pods"] = grouped_cumsum(result, "new_pods", group_cols)
    
    return result[group_cols + ["active_pods"]]


def calculate_monthly_vpo(df, group_cols):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    if "month_year" not in group_cols:
        group_cols = ["month_year"] + group_cols

    active_pods = calculate_monthly_active_pods(df, group_cols)
    units = calculate_monthly_units(df, group_cols)

    result = units.merge(active_pods,
        on = group_cols,
        how = "left"
    )

    result["vpo"] = result["units"] / result["active_pods"].replace(0, None)

    return result[group_cols + ["vpo"]]


def calculate_monthly_reorder_rate(df, group_cols):

    if isinstance(group_cols, str):
        group_cols = [group_cols]

    # Ensures that month_year is in the right order for the sorting before the cumsum

    if "month_year" in group_cols:
        group_cols = [c for c in group_cols if c != "month_year"] + ["month_year"]
    else:
        group_cols = group_cols + ["month_year"]

    store_universe = (
        df.groupby(["coded_customer"] + group_cols, as_index=False)
        .agg(
            repeat_buyer=("reorder_flag", "max"),
            new_buyer=("first_store_flag", "max"),
        )
    )

    result = (
        store_universe.groupby(group_cols, as_index=False)
        .agg(
            repeat_buyers=("repeat_buyer", "sum"),
            new_buyers=("new_buyer", "sum"),
            buying_stores=("coded_customer", "nunique"),
        )
        .sort_values(group_cols)
        .reset_index(drop=True)
    )

    result["total_buyers"] = grouped_cumsum(result, "new_buyers", group_cols)
    result["existing_buyers"] = result["total_buyers"] - result["new_buyers"]

    result["reorder_rate"] = calculate_reorder_rate(result)

    return result[group_cols + ["reorder_rate"]]

def calculate_monthly_new_pods(df, group_cols):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    if "month_year" not in group_cols:
        group_cols = ["month_year"] + group_cols

    result = (
        df.groupby(group_cols, as_index=False)
        .agg(new_pods=("first_pod_flag", "sum"))
    )

    return result

def calculate_monthly_average_skus_per_store(df, group_cols):
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    if "month_year" not in group_cols:
        group_cols = ["month_year"] + group_cols

    store_level = (
        df.groupby(["coded_customer"] + group_cols, as_index=False)
        .agg(skus=("sku", "nunique"))
    )

    result = (
        store_level.groupby(group_cols, as_index=False)
        .agg(average_skus_per_store=("skus", "mean"))
    )

    return result
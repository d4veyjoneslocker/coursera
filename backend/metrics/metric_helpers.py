import pandas as pd

def ensure_month_spine(df, group_cols, value_cols=None):
    """
    Ensures every group has a full continuous month_year spine.
    Missing months get filled with 0s for value_cols.
    """

    #print("before spine", df.shape, group_cols)


    if isinstance(group_cols, str):
        group_cols = [group_cols]

    # Separate time + non-time
    non_time_cols = [c for c in group_cols if c != "month_year"]

    # Get full month range

    current_month = pd.Timestamp.today().to_period("M")
    latest_full_month = current_month - 1

    min_month = df["month_year"].min()
    max_month = latest_full_month
    full_months = pd.period_range(min_month, max_month, freq="M")

    # Get all unique groups (excluding time)
    unique_groups = df[non_time_cols].drop_duplicates()

    # Create full grid
    full_index = (
        unique_groups.assign(key=1)
        .merge(pd.DataFrame({"month_year": full_months, "key": 1}), on="key")
        .drop("key", axis=1)
    )

    #print("full_index", full_index.shape)


    # Merge original data
    df = full_index.merge(df, on=group_cols + ["month_year"], how="left")

    # Fill missing values
    if value_cols:
        for col in value_cols:
            df[col] = df[col].fillna(0)

    #print("after spine", df.shape)

    sort_cols = group_cols + ["month_year"] if group_cols else ["month_year"]
    return df.sort_values(sort_cols).reset_index(drop=True)

def grouped_cumsum(df, metric, group_cols):
    non_time_cols = [c for c in group_cols if c != "month_year"]

    if non_time_cols:
        return df.groupby(non_time_cols)[metric].cumsum()
    else:
        return df[metric].cumsum()
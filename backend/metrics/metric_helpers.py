import pandas as pd
from datetime import datetime

def build_spine(df_filtered, group_cols=None, selected_years=None, selected_months=None):
    if group_cols is None:
        group_cols = []
    elif isinstance(group_cols, str):
        group_cols = [group_cols]

    # Set today to today's today and current_period to the month Period before today's date

    today = datetime.today()
    current_period = pd.Period(today, freq="M") - 1

    # If no specific year is passed by the filter, set the max year to the current_period's year
    # (not today's year so we can display the right data in January)

    if not selected_years:
        max_selected_year = current_period.year
    else:
        max_selected_year = max(selected_years)
    
    # If a specific filter was passed and the highest year wasn't the current year, set the max
    # period to the end of that year. Otherwise, it stays the same at last month

    if max_selected_year != current_period.year:
        current_period = pd.Period(year=max_selected_year, month=12, freq="M")

    # If group_cols was passed, group the filtered_df by group_cols and add two columns to each
    # group indicating the first and last month that they appeared in the filtered dataset

    if group_cols:
        group_ranges = (
            df_filtered
            .groupby(group_cols)
            .agg(
                first_month=("month_year", "min"),
                last_month=("month_year", "max"))
            .reset_index()
        )
    
        def adjust_max(period):
            if period.year == current_period.year:
                return current_period
            else:
                return pd.Period(year=period.year, month=12, freq='M')

    # Extend last month out for each group to the end of the period
    # This is because if a store stopped ordering in say January and it's April (it's April 2026 btw), 
    # we need to factor in that they didn't order in Feb and March

        group_ranges['last_month'] = group_ranges['last_month'].apply(adjust_max)

    # For each group, fill in the missing months and concatenate

        def expand_range(row):
            months = pd.period_range(row["first_month"], row["last_month"], freq='M')
            return pd.DataFrame({**{col: row[col] for col in group_cols}, 'month_year': months})

        spine = pd.concat([expand_range(row) for _, row in group_ranges.iterrows()], ignore_index=True)

    else:

    # First month is the first month of the filtered_df, last month is last month of the filtered_df

        first_month = df_filtered["month_year"].min()
        last_month = df_filtered["month_year"].max()
    
    # Extends last month to end of current period

        if last_month.year == current_period.year:
            last_month = current_period
        else:
            last_month = pd.Period(year=last_month.year, month=12, freq='M')

    # Fills in missing values        

        spine = pd.DataFrame({"month_year": pd.period_range(first_month, last_month, freq='M')})

    # If monthly filter is applied, filter spine only to those months

    if selected_months:
        spine = spine[spine["month_year"].isin(selected_months)]

    return spine[group_cols + ["month_year"]]

# Full universe spine is for things like the denominators of reorder rate / VPO, where a store could be inactive during the filtered
# window, but need to be counted

def build_full_universe_spine(df_filtered, df_full, group_cols=None, selected_years=None, selected_months=None):
    if group_cols is None:
        group_cols = []
    elif isinstance(group_cols, str):
        group_cols = [group_cols]

    today = datetime.today()
    current_period = pd.Period(today, freq="M") - 1

    if not selected_years:
        max_selected_year = current_period.year
    else:
        max_selected_year = max(selected_years)
    
    if max_selected_year != current_period.year:
        current_period = pd.Period(year=max_selected_year, month=12, freq="M")

    if group_cols:
        overall_first = min(selected_months) if selected_months else (pd.Period(year=min(selected_years), month=1, freq='M') if selected_years else df_full["month_year"].min())
        overall_last = current_period

        active_in_or_before_window = (
            df_full[df_full["month_year"] <= overall_last][group_cols]
            .drop_duplicates()
        )

        store_first = (
            df_full.groupby(group_cols)["month_year"]
            .min()
            .reset_index()
            .rename(columns={"month_year": "true_first_month"})
        )

        group_ranges = active_in_or_before_window.merge(store_first, on=group_cols, how="left")
        group_ranges["first_month"] = group_ranges["true_first_month"].clip(lower=overall_first)
        group_ranges["last_month"] = overall_last
        group_ranges = group_ranges.drop(columns=["true_first_month"])

        def expand_range(row):
            months = pd.period_range(row["first_month"], row["last_month"], freq='M')
            return pd.DataFrame({**{col: row[col] for col in group_cols}, 'month_year': months})

        spine = pd.concat([expand_range(row) for _, row in group_ranges.iterrows()], ignore_index=True)

    else:
        overall_first = min(selected_months) if selected_months else (pd.Period(year=min(selected_years), month=1, freq='M') if selected_years else df_full["month_year"].min())
        spine = pd.DataFrame({"month_year": pd.period_range(overall_first, current_period, freq='M')})

    if selected_months:
        spine = spine[spine["month_year"].isin(selected_months)]

    return spine

def build_comparison_spine(df_full, group_cols=None, lookback_months=3, selected_years=None, selected_months=None):
    if group_cols is None:
        group_cols = []
    elif isinstance(group_cols, str):
        group_cols = [group_cols]

    # ----------------------------------
    # 1. Determine comparison_end
    # ----------------------------------
    today = pd.Timestamp.today()
    current_period = pd.Period(today, freq="M") - 1

    if selected_months:
        comparison_end = max(selected_months)
        if comparison_end > current_period:
            comparison_end = current_period
    elif selected_years:
        max_selected_year = max(selected_years)
        if max_selected_year == current_period.year:
            comparison_end = current_period
        else:
            comparison_end = pd.Period(year=max_selected_year, month=12, freq="M")
    else:
        comparison_end = current_period

    # ----------------------------------
    # 2. Determine comparison_start
    # ----------------------------------
    comparison_start = comparison_end - lookback_months

    # ----------------------------------
    # 3. Build spine
    # ----------------------------------
    if group_cols:
        groups = (
            df_full[df_full["month_year"] <= comparison_end][group_cols]
            .drop_duplicates()
        )

        first_month = (
            df_full.groupby(group_cols)["month_year"]
            .min()
            .reset_index()
            .rename(columns={"month_year": "true_first_month"})
        )

        group_ranges = groups.merge(first_month, on=group_cols, how="left")
        group_ranges["start"] = group_ranges["true_first_month"].clip(lower=comparison_start)
        group_ranges["end"] = comparison_end

        def expand(row):
            months = pd.period_range(row["start"], row["end"], freq="M")
            return pd.DataFrame({
                **{col: row[col] for col in group_cols},
                "month_year": months
            })

        if group_ranges.empty:
            spine = pd.DataFrame(columns=group_cols + ["month_year"])
        else:
            spine = pd.concat(
                [expand(row) for _, row in group_ranges.iterrows()],
                ignore_index=True
            )
    else:
        spine = pd.DataFrame({
            "month_year": pd.period_range(comparison_start, comparison_end, freq="M")
        })

    return spine


def grouped_cumsum(df, metric, group_cols):
    non_time_cols = [c for c in group_cols if c != "month_year"]

    if non_time_cols:
        return df.groupby(non_time_cols)[metric].cumsum()
    else:
        return df[metric].cumsum()
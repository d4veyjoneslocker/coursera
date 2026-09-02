import pandas as pd
from datetime import datetime


def empty_spine(group_cols=None):
    if group_cols is None:
        group_cols = []
    elif isinstance(group_cols, str):
        group_cols = [group_cols]

    return pd.DataFrame(columns=group_cols + ["month_year"])


def build_spine(
    df_filtered,
    group_cols=None,
    selected_years=None,
    selected_months=None,
    include_current_month=False,
):
    if group_cols is None:
        group_cols = []
    elif isinstance(group_cols, str):
        group_cols = [group_cols]

    today = datetime.today()
    current_period = pd.Period(today, freq="M")

    if not include_current_month:
        current_period -= 1

    max_selected_year = current_period.year if not selected_years else max(selected_years)

    if max_selected_year != current_period.year:
        current_period = pd.Period(year=max_selected_year, month=12, freq="M")

    if group_cols:
        if df_filtered.empty or df_filtered["month_year"].isna().all():
            return empty_spine(group_cols)

        group_ranges = (
            df_filtered
            .groupby(group_cols)
            .agg(
                first_month=("month_year", "min"),
                last_month=("month_year", "max"),
            )
            .reset_index()
        )

        def adjust_max(period):
            if pd.isna(period):
                return pd.NaT

            if period.year == current_period.year:
                return current_period

            return pd.Period(year=period.year, month=12, freq="M")

        group_ranges["last_month"] = group_ranges["last_month"].apply(adjust_max)

        def expand_range(row):
            if pd.isna(row["first_month"]) or pd.isna(row["last_month"]):
                return empty_spine(group_cols)

            months = pd.period_range(row["first_month"], row["last_month"], freq="M")

            return pd.DataFrame({
                **{col: row[col] for col in group_cols},
                "month_year": months,
            })

        if group_ranges.empty:
            spine = empty_spine(group_cols)
        else:
            spine = pd.concat(
                [expand_range(row) for _, row in group_ranges.iterrows()],
                ignore_index=True,
            )

    else:
        if df_filtered.empty or df_filtered["month_year"].isna().all():
            return empty_spine(group_cols)

        first_month = df_filtered["month_year"].min()
        last_month = df_filtered["month_year"].max()

        if pd.isna(first_month) or pd.isna(last_month):
            return empty_spine(group_cols)

        if last_month.year == current_period.year:
            last_month = current_period
        else:
            last_month = pd.Period(year=last_month.year, month=12, freq="M")

        spine = pd.DataFrame({
            "month_year": pd.period_range(first_month, last_month, freq="M")
        })

    if selected_months:
        spine = spine[spine["month_year"].isin(selected_months)]

    return spine[group_cols + ["month_year"]]


def build_window_universe_spine(
    df_filtered,
    df_full,
    group_cols=None,
    selected_years=None,
    selected_months=None,
    include_current_month=False,
):
    if group_cols is None:
        group_cols = []
    elif isinstance(group_cols, str):
        group_cols = [group_cols]

    today = datetime.today()
    current_period = pd.Period(today, freq="M")

    if not include_current_month:
        current_period -= 1

    max_selected_year = current_period.year if not selected_years else max(selected_years)

    if max_selected_year != current_period.year:
        current_period = pd.Period(year=max_selected_year, month=12, freq="M")

    if group_cols:
        overall_first = (
            min(selected_months)
            if selected_months
            else (
                pd.Period(year=min(selected_years), month=1, freq="M")
                if selected_years
                else df_filtered["month_year"].min()
            )
        )

        if pd.isna(overall_first) or pd.isna(current_period):
            return empty_spine(group_cols)

        overall_last = current_period

        active_in_or_before_window = (
            df_full[df_full["month_year"] <= overall_last][group_cols]
            .drop_duplicates()
        )

        if active_in_or_before_window.empty:
            active_in_or_before_window = df_full[group_cols].drop_duplicates()

        group_first = (
            df_full.groupby(group_cols)["month_year"]
            .min()
            .reset_index()
            .rename(columns={"month_year": "true_first_month"})
        )

        group_ranges = active_in_or_before_window.merge(
            group_first,
            on=group_cols,
            how="left",
        )

        group_ranges["first_month"] = group_ranges["true_first_month"].clip(lower=overall_first)
        group_ranges["last_month"] = overall_last
        group_ranges = group_ranges.drop(columns=["true_first_month"])

        def expand_range(row):
            if pd.isna(row["first_month"]) or pd.isna(row["last_month"]):
                return empty_spine(group_cols)

            months = pd.period_range(row["first_month"], row["last_month"], freq="M")

            return pd.DataFrame({
                **{col: row[col] for col in group_cols},
                "month_year": months,
            })

        if group_ranges.empty:
            spine = empty_spine(group_cols)
        else:
            spine = pd.concat(
                [expand_range(row) for _, row in group_ranges.iterrows()],
                ignore_index=True,
            )

    else:
        if df_filtered.empty or df_filtered["month_year"].isna().all():
            return empty_spine(group_cols)

        first_month = df_filtered["month_year"].min()
        last_month = df_filtered["month_year"].max()

        if pd.isna(first_month) or pd.isna(last_month):
            return empty_spine(group_cols)

        if last_month.year == current_period.year:
            last_month = current_period
        else:
            last_month = pd.Period(year=last_month.year, month=12, freq="M")

        spine = pd.DataFrame({
            "month_year": pd.period_range(first_month, last_month, freq="M")
        })

    if selected_months:
        spine = spine[spine["month_year"].isin(selected_months)]

    return spine[group_cols + ["month_year"]]


def build_full_universe_spine(
    df_filtered,
    df_full,
    group_cols=None,
    selected_years=None,
    selected_months=None,
    include_current_month=False,
):
    if group_cols is None:
        group_cols = []
    elif isinstance(group_cols, str):
        group_cols = [group_cols]

    today = datetime.today()
    current_period = pd.Period(today, freq="M")

    if not include_current_month:
        current_period -= 1

    max_selected_year = current_period.year if not selected_years else max(selected_years)

    if max_selected_year != current_period.year:
        current_period = pd.Period(year=max_selected_year, month=12, freq="M")

    if group_cols:
        overall_first = (
            min(selected_months)
            if selected_months
            else (
                pd.Period(year=min(selected_years), month=1, freq="M")
                if selected_years
                else df_full["month_year"].min()
            )
        )

        if pd.isna(overall_first) or pd.isna(current_period):
            return empty_spine(group_cols)

        overall_last = current_period

        active_in_or_before_window = (
            df_full[df_full["month_year"] <= overall_last][group_cols]
            .drop_duplicates()
        )

        if active_in_or_before_window.empty:
            active_in_or_before_window = df_full[group_cols].drop_duplicates()

        store_first = (
            df_full.groupby(group_cols)["month_year"]
            .min()
            .reset_index()
            .rename(columns={"month_year": "true_first_month"})
        )

        group_ranges = active_in_or_before_window.merge(
            store_first,
            on=group_cols,
            how="left",
        )

        group_ranges["first_month"] = group_ranges["true_first_month"].clip(lower=overall_first)
        group_ranges["last_month"] = overall_last
        group_ranges = group_ranges.drop(columns=["true_first_month"])

        def expand_range(row):
            if pd.isna(row["first_month"]) or pd.isna(row["last_month"]):
                return empty_spine(group_cols)

            months = pd.period_range(row["first_month"], row["last_month"], freq="M")

            return pd.DataFrame({
                **{col: row[col] for col in group_cols},
                "month_year": months,
            })

        if group_ranges.empty:
            spine = empty_spine(group_cols)
        else:
            spine = pd.concat(
                [expand_range(row) for _, row in group_ranges.iterrows()],
                ignore_index=True,
            )

    else:
        overall_first = (
            min(selected_months)
            if selected_months
            else (
                pd.Period(year=min(selected_years), month=1, freq="M")
                if selected_years
                else df_full["month_year"].min()
            )
        )

        if pd.isna(overall_first) or pd.isna(current_period):
            return empty_spine(group_cols)

        spine = pd.DataFrame({
            "month_year": pd.period_range(overall_first, current_period, freq="M")
        })

    if selected_months:
        spine = spine[spine["month_year"].isin(selected_months)]

    return spine[group_cols + ["month_year"]]


def build_comparison_spine(
    df_full,
    group_cols=None,
    lookback_months=0,
    selected_years=None,
    selected_months=None,
    include_current_month=False,
):
    if group_cols is None:
        group_cols = []
    elif isinstance(group_cols, str):
        group_cols = [group_cols]

    today = pd.Timestamp.today()
    current_period = pd.Period(today, freq="M")

    if not include_current_month:
        current_period -= 1

    if selected_months:
        display_start = min(selected_months)
        display_end = min(max(selected_months), current_period)

    elif selected_years:
        min_selected_year = min(selected_years)
        max_selected_year = max(selected_years)

        display_start = pd.Period(year=min_selected_year, month=1, freq="M")

        if max_selected_year == current_period.year:
            display_end = current_period
        else:
            display_end = pd.Period(year=max_selected_year, month=12, freq="M")

    else:
        if df_full.empty or df_full["month_year"].isna().all():
            return empty_spine(group_cols)

        display_start = df_full["month_year"].min()
        display_end = current_period

    if pd.isna(display_start) or pd.isna(display_end):
        return empty_spine(group_cols)

    if display_start > display_end:
        return empty_spine(group_cols)

    spine_start = display_start - lookback_months
    spine_end = display_end

    if group_cols:
        groups = (
            df_full[df_full["month_year"] <= spine_end][group_cols]
            .drop_duplicates()
        )

        first_month = (
            df_full.groupby(group_cols)["month_year"]
            .min()
            .reset_index()
            .rename(columns={"month_year": "true_first_month"})
        )

        group_ranges = groups.merge(first_month, on=group_cols, how="left")
        group_ranges["start"] = group_ranges["true_first_month"].clip(lower=spine_start)
        group_ranges["end"] = spine_end

        def expand_range(row):
            if pd.isna(row["start"]) or pd.isna(row["end"]):
                return empty_spine(group_cols)

            months = pd.period_range(row["start"], row["end"], freq="M")

            return pd.DataFrame({
                **{col: row[col] for col in group_cols},
                "month_year": months,
            })

        if group_ranges.empty:
            spine = empty_spine(group_cols)
        else:
            spine = pd.concat(
                [expand_range(row) for _, row in group_ranges.iterrows()],
                ignore_index=True,
            )

    else:
        if pd.isna(spine_start) or pd.isna(spine_end):
            return empty_spine(group_cols)

        spine = pd.DataFrame({
            "month_year": pd.period_range(spine_start, spine_end, freq="M")
        })

    return spine[group_cols + ["month_year"]]
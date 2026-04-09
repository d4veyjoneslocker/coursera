import pandas as pd

def repeat_buyers_1m(df):
    months = sorted(df["month_year"].dropna().unique())
    results = []

    for m in months:
        df_month = df[df["month_year"] == m]
        df_before = df[df["month_year"] < m]

        before_customers = set(df_before["coded_customer"].unique())

        buyers = df_month["coded_customer"].unique()
        repeat = [c for c in buyers if c in before_customers]

        results.append({
            "month_year": m,
            "repeat_buyers_1m": len(set(repeat))
        })

    return pd.DataFrame(results)

def repeat_buyers_3m(df):
    months = sorted(df["month_year"].dropna().unique())
    results = []

    for i, end_month in enumerate(months):
        start_idx = max(0, i - 2)
        window_months = months[start_idx:i + 1]
        first_window_month = window_months[0]

        df_window = df[df["month_year"].isin(window_months)]
        df_before = df[df["month_year"] < first_window_month]

        window_counts = (
            df_window.groupby("coded_customer")["month_year"]
            .nunique()
            .reset_index(name="months_in_window")
        )

        before_customers = set(df_before["coded_customer"].unique())
        window_counts["had_before"] = window_counts["coded_customer"].isin(before_customers)

        qualified = window_counts[
            (window_counts["had_before"]) |
            (window_counts["months_in_window"] >= 2)
        ]

        results.append({
            "month_year": end_month,
            "repeat_buyers_3m": qualified["coded_customer"].nunique()
        })

    return pd.DataFrame(results)
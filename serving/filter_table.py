

def filter_table(df, **filters):
    for col, val in filters.items():
        if val is not None:
            df = df[df[col] == val]
    return df

def select_metric(df, metric):
    return df[["month_year", metric]]

def get_metric_timeseries(df, metric, **filters):
    df = filter_table(df, **filters)
    return df[["month_year", metric]].sort_values("month_year")
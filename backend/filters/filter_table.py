def resolve_entity_value(
    df,
    column,
    value,
):
    if value is None:
        return None

    values = (
        df[column]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    # exact case-insensitive match
    for candidate in values:
        if candidate.lower() == value.lower():
            return candidate

    raise ValueError(
        f"Could not resolve {column}: {value}"
    )

# UPDATE SO BLANK FILTERS DONT COUNT

def filter_table(df, **filters):
    for col, val in filters.items():
        if val is None:
            continue

        if isinstance(val, list):
            if len(val) == 0:
                continue

            df = df[df[col].astype(str).isin([str(v) for v in val])]
        else:
            df = df[df[col].astype(str) == str(val)]
    return df

def select_metric(df, metric):
    return df[["month_year", metric]]

def get_metric_timeseries(df, metric, **filters):
    df = filter_table(df, **filters)
    return df[["month_year", metric]].sort_values("month_year")
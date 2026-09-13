import pandas as pd
import numpy as np


def to_python_value(value):
    if pd.isna(value):
        return None

    if isinstance(value, np.generic):
        return value.item()

    return value


def metric_summary(df):
    if df.empty:
        return None

    row = df.iloc[0]

    return {
        "current": to_python_value(row["value_current"]),
        "comparison": to_python_value(row["value_comparison"]),
        "abs_change": to_python_value(row["abs_change"]),
        "pct_change": to_python_value(row["pct_change"]),
    }

import numpy as np
import pandas as pd


def to_python_value(value):
    if value is None:
        return None

    if isinstance(value, np.generic):
        value = value.item()

    if pd.isna(value):
        return None

    return value


def dataframe_to_records(df):
    return [
        {
            key: to_python_value(value)
            for key, value in row.items()
        }
        for row in df.to_dict(orient="records")
    ]
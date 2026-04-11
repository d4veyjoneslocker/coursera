import pandas as pd
import numpy as np

def clean_for_json(df: pd.DataFrame) -> pd.DataFrame:
    # convert periods/dates first
    for col in df.columns:
        if pd.api.types.is_period_dtype(df[col]) or pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].astype(str)

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.astype(object).where(pd.notnull(df), None)

    return df
import pandas as pd
import numpy as np

def pct_change(current, prior):
    return np.where(
        prior > 0,
        current / prior - 1,
        np.nan
    )

def add_time_metrics_simple(df, unit_metrics=None,buyer_metrics=None,vpo_metrics=None,pod_metrics=None):

    unit_metrics = unit_metrics or []
    vpo_metrics = vpo_metrics or []
    pod_metrics = pod_metrics or []

    current_month = pd.Timestamp.today().to_period("M")

    df = df.sort_values("month_year").copy()
    df_full_months = df[df["month_year"] != current_month].copy()

    for metric in unit_metrics:
        
        # Calculating prior values

        df_full_months[f"{metric}_3m"] = df_full_months[metric].rolling(3, min_periods=3).sum()
        df_full_months[f"{metric}_l1m"] = df_full_months[metric].shift(1)
        df_full_months[f"{metric}_l3m"] = df_full_months[metric].shift(3).rolling(3, min_periods=3).sum()
        df_full_months[f"{metric}_py"] = df_full_months[metric].shift(12)

        # Calculating percent change

        df_full_months[f"{metric}_l1m_pct"] = pct_change(df_full_months[f"{metric}"],df_full_months[f"{metric}_l1m"])
        df_full_months[f"{metric}_l3m_pct"] = pct_change(df_full_months[f"{metric}_3m"],df_full_months[f"{metric}_l3m"])
        df_full_months[f"{metric}_py_pct"] = pct_change(df_full_months[f"{metric}"],df_full_months[f"{metric}_py"])

    for metric in buyer_metrics:
        
        # Calculating prior values

        df_full_months[f"{metric}_l1m"] = df_full_months[metric].shift(1)
        df_full_months[f"{metric}_py"] = df_full_months[metric].shift(12)

        # Calculating percent change

        df_full_months[f"{metric}_l1m_pct"] = pct_change(df_full_months[f"{metric}"],df_full_months[f"{metric}_l1m"])
        df_full_months[f"{metric}_l3m_pct"] = pct_change(df_full_months[f"{metric}_3m"],df_full_months[f"{metric}_l3m"])
        df_full_months[f"{metric}_py_pct"] = pct_change(df_full_months[f"{metric}"],df_full_months[f"{metric}_py"])
    
    for metric in vpo_metrics:

        df_full_months[f"{metric}_lifetime_average"] = df_full_months["units"].cumsum()/df_full_months["active_pods"].cumsum()/4

        # calculating 3m velocity
        df_full_months[f"{metric}_3m"] = df_full_months["units"].rolling(3, min_periods=3).sum()/df_full_months["active_pods"].rolling(3, min_periods=3).sum()/4
        df_full_months[f"{metric}_l3m"] = df_full_months["units"].shift(3).rolling(3, min_periods=3).sum()/df_full_months["active_pods"].shift(3).rolling(3, min_periods=3).sum()/4
        
        # Calculating prior values

        df_full_months[f"{metric}_l1m"] = df_full_months[metric].shift(1)
        df_full_months[f"{metric}_py"] = df_full_months[metric].shift(12)

        # Calculating percent change

        df_full_months[f"{metric}_l1m_pct"] = pct_change(df_full_months[f"{metric}"],df_full_months[f"{metric}_l1m"])
        df_full_months[f"{metric}_l3m_pct"] = pct_change(df_full_months[f"{metric}_3m"],df_full_months[f"{metric}_l3m"])
        df_full_months[f"{metric}_py_pct"] = pct_change(df_full_months[f"{metric}"],df_full_months[f"{metric}_py"])
    
    for metric in pod_metrics:
        
        # Calculating prior values

        df_full_months[f"{metric}_3m"] = df_full_months[metric].rolling(3, min_periods=3).max()
        df_full_months[f"{metric}_l1m"] = df_full_months[metric].shift(1)
        df_full_months[f"{metric}_l3m"] = df_full_months[metric].shift(3)
        df_full_months[f"{metric}_py"] = df_full_months[metric].shift(12)

        # Calculating percent change

        df_full_months[f"{metric}_l1m_pct"] = pct_change(df_full_months[f"{metric}"],df_full_months[f"{metric}_l1m"])
        df_full_months[f"{metric}_l3m_pct"] = pct_change(df_full_months[f"{metric}"],df_full_months[f"{metric}_l3m"])
        df_full_months[f"{metric}_py_pct"] = pct_change(df_full_months[f"{metric}"],df_full_months[f"{metric}_py"])

    

    df_full_months.to_csv("df_full_months.csv", index=False)
    return df_full_months

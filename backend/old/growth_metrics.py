import pandas as pd
import numpy as np

def pct_change(current, prior):
    return np.where(
        prior > 0,
        current / prior - 1,
        np.nan
    )

def add_pct_change_columns(df, metric):
    df[f"{metric}_l1m_pct"] = pct_change(df[f"{metric}"], df[f"{metric}_l1m"])
    df[f"{metric}_l3m_pct"] = pct_change(df[f"{metric}"], df[f"{metric}_l3m"])
    df[f"{metric}_py_pct"] = pct_change(df[f"{metric}"], df[f"{metric}_py"])

    return df

def calculate_reorder_rate(df, metric):
    
    result = df[f"repeat_buyers_{metric}"] / df[f"existing_buyers_{metric}"]
    
    return result.replace([float("inf"), -float("inf")], None)


def add_prior_month_columns(df, attribute, metric, l1m = None, l3m = None, py = None):

    if l1m:
        df[f"{metric}_l1m"] = df[metric].shift(1)

    if l3m:
        df[f"{metric}_l3m"] = df[f"{metric}_3m"].shift(3)

    if py:
        df[f"{metric}_py"] = df[metric].shift(12)

    return df


def add_time_metrics_chain(df, attribute, unit_metrics=[],buyer_metrics=[],vpo_metrics=[],pod_metrics=[]):

    unit_metrics = unit_metrics or []
    vpo_metrics = vpo_metrics or []
    pod_metrics = pod_metrics or []

    current_month = pd.Timestamp.today().to_period("M")

    df = df.sort_values([attribute, "month_year"]).copy()
    df_full_months = df[df["month_year"] != current_month].copy()
    month_count = df["month_year"].nunique()

    # Error check for if there's no sales before the current month

    if df_full_months.empty:
        return {
            "units_kpis": [],
            "velocity_kpis": [],
            "buyers_kpis": [],
        }
    print("full-month rows:", len(df_full_months))


    for metric in unit_metrics:
        
        # Calculating prior values

        df_full_months[f"{metric}_3m"] = df_full_months.groupby(attribute)[metric].rolling(3, min_periods=3).sum().reset_index(level=0, drop=True)
        df_full_months[f"{metric}_l1m"] = df_full_months.groupby(attribute)[metric].shift(1)
        df_full_months[f"{metric}_l3m"] = df_full_months.groupby(attribute)[f"{metric}_3m"].shift(3)
        df_full_months[f"{metric}_py"] = df_full_months.groupby(attribute)[metric].shift(12)

        # Calculating percent change

        df_full_months[f"{metric}_l1m_pct"] = pct_change(df_full_months[f"{metric}"],df_full_months[f"{metric}_l1m"])
        df_full_months[f"{metric}_l3m_pct"] = pct_change(df_full_months[f"{metric}_3m"],df_full_months[f"{metric}_l3m"])
        df_full_months[f"{metric}_py_pct"] = pct_change(df_full_months[f"{metric}"],df_full_months[f"{metric}_py"])

    for metric in buyer_metrics:
        
        # Calculating prior values

        df_full_months[f"{metric}_l1m"] = df_full_months.groupby(attribute)[metric].shift(1)
        df_full_months[f"{metric}_py"] = df_full_months.groupby(attribute)[metric].shift(12)

        # Calculating percent change

        df_full_months[f"{metric}_l1m_pct"] = pct_change(df_full_months[f"{metric}"],df_full_months[f"{metric}_l1m"])
        df_full_months[f"{metric}_l3m_pct"] = pct_change(df_full_months[f"{metric}_3m"],df_full_months[f"{metric}_l3m"])
        df_full_months[f"{metric}_py_pct"] = pct_change(df_full_months[f"{metric}"],df_full_months[f"{metric}_py"])
    
    # NOT CURRENTLY USING VPO OR POD SO THESE MAY NEED TO BE CLEANED UP

    for metric in pod_metrics:
        
        # Calculating prior values

        df_full_months[f"{metric}_3m"] = df_full_months.groupby(attribute)[metric].rolling(3, min_periods=3).max().reset_index(level=0, drop=True)
        df_full_months[f"{metric}_l1m"] = df_full_months.groupby(attribute)[metric].shift(1)
        df_full_months[f"{metric}_l3m"] = df_full_months.groupby(attribute)[metric].shift(3)
        df_full_months[f"{metric}_py"] = df_full_months.groupby(attribute)[metric].shift(12)

        # Calculating percent change

        df_full_months[f"{metric}_l1m_pct"] = pct_change(df_full_months[f"{metric}"],df_full_months[f"{metric}_l1m"])
        df_full_months[f"{metric}_l3m_pct"] = pct_change(df_full_months[f"{metric}"],df_full_months[f"{metric}_l3m"])
        df_full_months[f"{metric}_py_pct"] = pct_change(df_full_months[f"{metric}"],df_full_months[f"{metric}_py"])

    for metric in vpo_metrics:

        df_full_months[f"{metric}_lifetime_average"] = df_full_months.groupby(attribute)["units"].cumsum().reset_index(level=0, drop=True)/df_full_months.groupby(attribute)["active_pods"].cumsum().reset_index(level=0, drop=True)/4

        # calculating 3m velocity
        df_full_months[f"{metric}_3m"] = df_full_months.groupby(attribute)["units"].rolling(3, min_periods=3).sum()/df_full_months.groupby(attribute)["active_pods"].rolling(3, min_periods=3).sum()/4
        #df_full_months[f"{metric}_l3m"] = df_full_months.groupby(attribute)["units"].shift(3).rolling(3, min_periods=3).sum().reset_index(level=0, drop=True)/df_full_months.groupby("chain")["active_pods"].shift(3).rolling(3, min_periods=3).sum().reset_index(level=0, drop=True)/4
        
        # Calculating prior values

        df_full_months[f"{metric}_l1m"] = df_full_months.groupby(attribute)[metric].shift(1)
        df_full_months[f"{metric}_py"] = df_full_months.groupby(attribute)[metric].shift(12)

        # Calculating percent change

        df_full_months[f"{metric}_l1m_pct"] = pct_change(df_full_months[f"{metric}"],df_full_months[f"{metric}_l1m"])
        df_full_months[f"{metric}_l3m_pct"] = pct_change(df_full_months[f"{metric}_3m"],df_full_months[f"{metric}_l3m"])
        df_full_months[f"{metric}_py_pct"] = pct_change(df_full_months[f"{metric}"],df_full_months[f"{metric}_py"])


    return df_full_months

def add_time_metrics_simple(df, unit_metrics=[],buyer_metrics=[],vpo_metrics=[],pod_metrics=[],reorder_metrics=[]):


    current_month = pd.Timestamp.today().to_period("M")

    df = df.sort_values("month_year").copy()
    df_full_months = df[df["month_year"] != current_month].copy()
    month_count = len(df["month_year"])

    # Error check for if there's no sales before the current month

    if df_full_months.empty:
        return {
            "units_kpis": [],
            "velocity_kpis": [],
            "buyers_kpis": [],
        }
    print("full-month rows:", len(df_full_months))



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
    
    for metric in reorder_metrics:


        df_full_months["reorder_rate_3m"] = calculate_reorder_rate(df_full_months,"3m")
        df_full_months["reorder_rate_l1m"] = calculate_reorder_rate(df_full_months,"l1m")
        df_full_months["reorder_rate_l3m"] = calculate_reorder_rate(df_full_months,"l3m")


        df_full_months[f"reorder_rate_l1m_abs"] = (df_full_months["reorder_rate"] - df_full_months["reorder_rate_l1m"])
        df_full_months[f"reorder_rate_l3m_abs"] = (df_full_months["reorder_rate_3m"] - df_full_months["reorder_rate_l3m"])

    return df_full_months


def add_time_metrics(df, attribute, unit_metrics=[],buyer_metrics=[],vpo_metrics=[],pod_metrics=[]):

    unit_metrics = unit_metrics or []
    vpo_metrics = vpo_metrics or []
    pod_metrics = pod_metrics or []

    current_month = pd.Timestamp.today().to_period("M")

    df = df.sort_values([attribute, "month_year"]).copy()
    df_full_months = df[df["month_year"] != current_month].copy()

    grouped = df_full_months.groupby(attribute) if attribute else df_full_months



    for metric in unit_metrics:
        
        # Calculating prior values

        df_full_months[f"{metric}_3m"] = grouped[metric].rolling(3, min_periods=3).sum().reset_index(level=0, drop=True)
        df_full_months[f"{metric}_l1m"] = df_full_months.groupby(attribute)[metric].shift(1)
        df_full_months[f"{metric}_l3m"] = df_full_months.groupby(attribute)[f"{metric}_3m"].shift(3)
        df_full_months[f"{metric}_py"] = df_full_months.groupby(attribute)[metric].shift(12)

        # Calculating percent change

        df_full_months = add_pct_change_columns(df_full_months, metric)

    for metric in buyer_metrics:
        
        # Calculating prior values

        df_full_months[f"{metric}_l1m"] = df_full_months.groupby(attribute)[metric].shift(1)
        df_full_months[f"{metric}_py"] = df_full_months.groupby(attribute)[metric].shift(12)

        # Calculating percent change

        df_full_months = add_pct_change_columns(df_full_months, metric)
    
    for metric in pod_metrics:
        
        # Calculating prior values

        df_full_months[f"{metric}_3m"] = df_full_months.groupby(attribute)[metric].rolling(3, min_periods=3).max().reset_index(level=0, drop=True)
        df_full_months[f"{metric}_l1m"] = df_full_months.groupby(attribute)[metric].shift(1)
        df_full_months[f"{metric}_l3m"] = df_full_months.groupby(attribute)[f"{metric}_3m"].shift(3)
        df_full_months[f"{metric}_py"] = df_full_months.groupby(attribute)[metric].shift(12)

        # Calculating percent change

        df_full_months = add_pct_change_columns(df_full_months, metric)

    for metric in vpo_metrics:

        df_full_months[f"{metric}_lifetime_average"] = df_full_months.groupby(attribute)["units"].cumsum().reset_index(level=0, drop=True)/df_full_months.groupby(attribute)["active_pods"].cumsum().reset_index(level=0, drop=True)/4

        # calculating 3m velocity
        df_full_months[f"{metric}_3m"] = df_full_months.groupby(attribute)["units"].rolling(3, min_periods=3).sum()/df_full_months.groupby(attribute)["active_pods"].rolling(3, min_periods=3).sum()/4
        #df_full_months[f"{metric}_l3m"] = df_full_months.groupby(attribute)["units"].shift(3).rolling(3, min_periods=3).sum().reset_index(level=0, drop=True)/df_full_months.groupby("chain")["active_pods"].shift(3).rolling(3, min_periods=3).sum().reset_index(level=0, drop=True)/4
        
        # Calculating prior values

        df_full_months[f"{metric}_l1m"] = df_full_months.groupby(attribute)[metric].shift(1)
        df_full_months[f"{metric}_py"] = df_full_months.groupby(attribute)[metric].shift(12)

        # Calculating percent change

        df_full_months = add_pct_change_columns(df_full_months, metric)
    


    return df_full_months

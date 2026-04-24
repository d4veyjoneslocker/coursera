import pandas as pd
from backend.transforms.kehe import transform_kehe_full_pod_vendor


def update_kehe_raw_master(raw_new_month_path, raw_master_path, raw_master_previous_path):
    # read newly uploaded month
    df_new = pd.read_csv(raw_new_month_path)

    if df_new.empty:
        raise ValueError("Uploaded file is empty.")

    if "DateRangeSelected" not in df_new.columns:
        raise ValueError("Uploaded file is missing required column: DateRangeSelected")

    # derive month_year from first date in DateRangeSelected
    df_new["start_date"] = df_new["DateRangeSelected"].astype(str).str.split(" to ").str[0]
    df_new["start_date"] = pd.to_datetime(df_new["start_date"])
    df_new["month_year"] = df_new["start_date"].dt.to_period("M")

    months_in_upload = df_new["month_year"].unique()

    # if no master exists yet, save new as master
    if not raw_master_path.exists():
        df_new.drop(columns=["start_date", "month_year"], errors="ignore").to_csv(raw_master_path, index=False)
        return

    # read existing master
    df_master = pd.read_csv(raw_master_path)

    if "DateRangeSelected" not in df_master.columns:
        raise ValueError("Existing master is missing required column: DateRangeSelected")

    df_master["start_date"] = df_master["DateRangeSelected"].astype(str).str.split(" to ").str[0]
    df_master["start_date"] = pd.to_datetime(df_master["start_date"])
    df_master["month_year"] = df_master["start_date"].dt.to_period("M")

    # backup old master
    raw_master_previous_path.parent.mkdir(parents=True, exist_ok=True)
    if raw_master_previous_path.exists():
        raw_master_previous_path.unlink()
    raw_master_path.replace(raw_master_previous_path)

    # remove overlapping months, then append new data
    df_master = df_master[~df_master["month_year"].isin(months_in_upload)]
    df_updated = pd.concat([df_master, df_new], ignore_index=True)

    # clean helper cols before saving
    df_updated = df_updated.drop(columns=["start_date", "month_year"], errors="ignore")

    df_updated.to_csv(raw_master_path, index=False)




def update_kehe_processed_data(raw_master_path, processed_current_path, processed_previous_path, org_id: str):
    print("1. starting processed update")

    if not raw_master_path.exists():
        raise ValueError("Raw master does not exist.")

    df_raw = pd.read_csv(raw_master_path)
    print("2. raw loaded", df_raw.shape)

    if df_raw.empty:
        raise ValueError("Raw master is empty.")

    df_raw = normalize_kehe_upload(df_raw)
    print("3. normalized raw")

    processed_current_path.parent.mkdir(parents=True, exist_ok=True)
    print("4. processed dir confirmed")

    if processed_current_path.exists():
        if processed_previous_path.exists():
            processed_previous_path.unlink()
        processed_current_path.replace(processed_previous_path)
        print("5. previous processed backed up")
    
    print(df_raw.dtypes)

    try:
        df_processed = transform_kehe_full_pod_vendor(df_raw, org_id=org_id)
        print("6. transform finished", df_processed.shape)
    except Exception as e:
        print("TRANSFORM ERROR:", repr(e))
        raise

    if df_processed.empty:
        raise ValueError("Processed dataframe is empty.")

    try:
        df_processed.to_parquet(processed_current_path, index=False)
        print("7. parquet saved", processed_current_path)
    except Exception as e:
        print("PARQUET ERROR:", repr(e))
        raise

def normalize_kehe_upload(df):
    df = df.copy()

    if "DateRangeSelected" in df.columns:
        parts = df["DateRangeSelected"].astype(str).str.split(" to ")

        if "DateRangeStart_Month" not in df.columns:
            df["DateRangeStart_Month"] = parts.str[0]

        if "DateRangeEnd" not in df.columns:
            df["DateRangeEnd"] = parts.str[-1]

    return df



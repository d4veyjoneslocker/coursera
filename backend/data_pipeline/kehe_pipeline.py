import pandas as pd
from backend.transforms.kehe import transform_kehe_full_pod_vendor
from backend.supabase.storage import upload_file, download_file


def update_kehe_raw_master(raw_new_month_path, raw_master_path, raw_master_previous_path, org_id: str):
    df_new = pd.read_csv(raw_new_month_path)

    if df_new.empty:
        raise ValueError("Uploaded file is empty.")

    if "DateRangeSelected" not in df_new.columns:
        raise ValueError("Uploaded file is missing required column: DateRangeSelected")

    df_new["start_date"] = df_new["DateRangeSelected"].astype(str).str.split(" to ").str[0]
    df_new["start_date"] = pd.to_datetime(df_new["start_date"])
    df_new["month_year"] = df_new["start_date"].dt.to_period("M")

    months_in_upload = df_new["month_year"].unique()

    upload_file(
        local_path=str(raw_new_month_path),
        org_id=org_id,
        remote_path="raw/kehe/raw_current_month.csv",
    )

    raw_master_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        download_file(
            org_id=org_id,
            remote_path="raw/kehe/raw_master.csv",
            local_path=str(raw_master_path),
        )
        master_exists = True
        print("Downloaded existing KeHE raw master from Supabase")
    except Exception as e:
        master_exists = False
        print("No existing KeHE raw master in Supabase:", repr(e))

    if not master_exists:
        df_new.drop(columns=["start_date", "month_year"], errors="ignore").to_csv(
            raw_master_path,
            index=False,
        )

        upload_file(
            local_path=str(raw_master_path),
            org_id=org_id,
            remote_path="raw/kehe/raw_master.csv",
        )

        return

    df_master = pd.read_csv(raw_master_path)

    if "DateRangeSelected" not in df_master.columns:
        raise ValueError("Existing master is missing required column: DateRangeSelected")

    df_master["start_date"] = df_master["DateRangeSelected"].astype(str).str.split(" to ").str[0]
    df_master["start_date"] = pd.to_datetime(df_master["start_date"])
    df_master["month_year"] = df_master["start_date"].dt.to_period("M")

    raw_master_previous_path.parent.mkdir(parents=True, exist_ok=True)

    if raw_master_previous_path.exists():
        raw_master_previous_path.unlink()

    raw_master_path.replace(raw_master_previous_path)

    upload_file(
        local_path=str(raw_master_previous_path),
        org_id=org_id,
        remote_path="raw/kehe/raw_master_previous.csv",
    )

    df_master = df_master[~df_master["month_year"].isin(months_in_upload)]
    df_updated = pd.concat([df_master, df_new], ignore_index=True)

    df_updated = df_updated.drop(columns=["start_date", "month_year"], errors="ignore")

    df_updated.to_csv(raw_master_path, index=False)

    upload_file(
        local_path=str(raw_master_path),
        org_id=org_id,
        remote_path="raw/kehe/raw_master.csv",
    )


def update_kehe_processed_data(raw_master_path, processed_current_path, processed_previous_path, org_id: str):
    raw_master_path.parent.mkdir(parents=True, exist_ok=True)

    download_file(
        org_id=org_id,
        remote_path="raw/kehe/raw_master.csv",
        local_path=str(raw_master_path),
    )

    df_raw = pd.read_csv(raw_master_path)

    if df_raw.empty:
        raise ValueError("Raw master is empty.")

    df_raw = normalize_kehe_upload(df_raw)

    processed_current_path.parent.mkdir(parents=True, exist_ok=True)

    if processed_current_path.exists():
        if processed_previous_path.exists():
            processed_previous_path.unlink()
        processed_current_path.replace(processed_previous_path)

    try:
        df_processed = transform_kehe_full_pod_vendor(df_raw, org_id=org_id)
    except Exception as e:
        print("TRANSFORM ERROR:", repr(e))
        raise

    if df_processed.empty:
        raise ValueError("Processed dataframe is empty.")

    try:
        df_processed.to_parquet(processed_current_path, index=False)
        print("Parquet saved", processed_current_path)
    except Exception as e:
        print("PARQUET ERROR:", repr(e))
        raise

    try:
        upload_file(
            local_path=str(processed_current_path),
            org_id=org_id,
            remote_path="processed_sources/kehe_processed.parquet",
        )
        print("✅ KeHE processed uploaded to Supabase")
    except Exception as e:
        print("SUPABASE UPLOAD ERROR:", repr(e))
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
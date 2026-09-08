import pandas as pd

from backend.transforms.kehe import transform_kehe_full_pod_vendor
from backend.supabase.storage import upload_file, download_file


def _add_month_key(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a canonical pandas Period[M] month_key derived from
    DateRangeSelected.

    month_key is for internal pipeline logic only and should be
    dropped before persisting raw files.
    """
    df = df.copy()

    if "DateRangeSelected" not in df.columns:
        raise ValueError(
            "Data is missing required column: DateRangeSelected"
        )

    start_dates = (
        df["DateRangeSelected"]
        .astype(str)
        .str.split(" to ")
        .str[0]
    )

    parsed_dates = pd.to_datetime(
        start_dates,
        errors="raise",
    )

    df["month_key"] = parsed_dates.dt.to_period("M")

    return df


def _get_months_from_processed(df: pd.DataFrame) -> set[pd.Period]:
    if "month_year" not in df.columns:
        raise ValueError(
            "Processed KeHE data is missing required column: month_year"
        )

    return set(df["month_year"].dropna().tolist())


def update_kehe_raw_master(
    raw_new_month_path,
    raw_master_path,
    raw_master_previous_path,
    org_id: str,
):
    """
    Builds and validates the updated KeHE raw master locally.

    Important:
    - Downloads the persisted master once at the beginning.
    - Replaces uploaded months using one canonical Period[M] key.
    - Confirms the uploaded rows were incorporated exactly.
    - DOES NOT upload the new raw master to Supabase.
      Persistence happens only after the full pipeline succeeds.

    Returns:
        list[pd.Period]: uploaded months
    """
    print("\n===== START KEHE RAW MASTER UPDATE =====")
    print("New upload path:", raw_new_month_path)
    print("Org ID:", org_id)

    df_new = pd.read_csv(raw_new_month_path)

    print("Uploaded rows:", len(df_new))
    print("Uploaded columns:", df_new.columns.tolist())

    if df_new.empty:
        raise ValueError("Uploaded file is empty.")

    if "DateRangeSelected" not in df_new.columns:
        raise ValueError(
            "Uploaded file is missing required column: DateRangeSelected"
        )

    # ---------------------------------------------------------
    # Canonical month normalization
    # ---------------------------------------------------------

    df_new = _add_month_key(df_new)

    months_in_upload = sorted(
        df_new["month_key"].unique().tolist()
    )

    uploaded_month_counts = (
        df_new
        .groupby("month_key")
        .size()
        .to_dict()
    )

    print(
        "Months in upload:",
        [str(month) for month in months_in_upload],
    )

    print(
        "Uploaded rows by month:",
        {
            str(month): count
            for month, count in uploaded_month_counts.items()
        },
    )

    # Keeping this is fine because raw_current_month is not a
    # canonical downstream artifact. It is simply the uploaded file.
    print("Uploading raw current month to Supabase...")

    upload_file(
        local_path=str(raw_new_month_path),
        org_id=org_id,
        remote_path="raw/kehe/raw_current_month.csv",
    )

    print("✅ Uploaded raw current month")

    raw_master_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ---------------------------------------------------------
    # Download persisted state ONCE
    # ---------------------------------------------------------

    print("Attempting to download existing raw master...")

    try:
        download_file(
            org_id=org_id,
            remote_path="raw/kehe/raw_master.csv",
            local_path=str(raw_master_path),
        )

        master_exists = True
        print(
            "✅ Downloaded existing KeHE raw master from Supabase"
        )

    except FileNotFoundError:
        master_exists = False
        print(
            "No existing KeHE raw master found. "
            "Creating new master."
        )

    except Exception as e:
        print("❌ FAILED TO DOWNLOAD EXISTING RAW MASTER")
        print("Error:", repr(e))
        raise

    # ---------------------------------------------------------
    # Existing master
    # ---------------------------------------------------------

    if master_exists:
        df_master = pd.read_csv(raw_master_path)

        print("Existing master rows:", len(df_master))

        if df_master.empty:
            raise ValueError("Existing raw master is empty.")

        if "DateRangeSelected" not in df_master.columns:
            raise ValueError(
                "Existing master is missing required column: "
                "DateRangeSelected"
            )

        df_master = _add_month_key(df_master)

        existing_months = sorted(
            df_master["month_key"]
            .astype(str)
            .unique()
            .tolist()
        )

        print("Existing master months:", existing_months)

        # -----------------------------------------------------
        # Local backup of prior master
        # -----------------------------------------------------

        raw_master_previous_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if raw_master_previous_path.exists():
            raw_master_previous_path.unlink()

        print("Backing up current raw master locally...")

        # Save from dataframe rather than moving raw_master_path,
        # because raw_master_path is about to become the new candidate.
        df_master_backup = df_master.drop(
            columns=["month_key"],
            errors="ignore",
        )

        df_master_backup.to_csv(
            raw_master_previous_path,
            index=False,
        )

        # Backup is not a canonical current-state artifact, so it can
        # still be persisted immediately.
        print("Uploading previous raw master backup...")

        upload_file(
            local_path=str(raw_master_previous_path),
            org_id=org_id,
            remote_path="raw/kehe/raw_master_previous.csv",
        )

        print("✅ Previous raw master backed up")

        # -----------------------------------------------------
        # Replace uploaded months
        # -----------------------------------------------------

        master_rows_before = len(df_master)

        df_master = df_master[
            ~df_master["month_key"].isin(months_in_upload)
        ].copy()

        master_rows_after_removal = len(df_master)

        print(
            "Master rows before month replacement:",
            master_rows_before,
        )

        print(
            "Master rows after removing uploaded months:",
            master_rows_after_removal,
        )

        print(
            "Rows removed:",
            master_rows_before - master_rows_after_removal,
        )

        df_updated = pd.concat(
            [df_master, df_new],
            ignore_index=True,
        )

    # ---------------------------------------------------------
    # New org / no prior master
    # ---------------------------------------------------------

    else:
        print("Creating new raw master")

        df_updated = df_new.copy()

    print("Updated master rows:", len(df_updated))

    updated_months = sorted(
        df_updated["month_key"]
        .astype(str)
        .unique()
        .tolist()
    )

    print("Updated master months:", updated_months)

    # ---------------------------------------------------------
    # TEST #1 — confirm THIS upload was incorporated correctly
    # ---------------------------------------------------------

    master_month_counts = (
        df_updated
        .groupby("month_key")
        .size()
        .to_dict()
    )

    for month, expected_count in uploaded_month_counts.items():
        actual_count = master_month_counts.get(month, 0)

        print(
            f"Validating {month}: "
            f"uploaded={expected_count}, "
            f"master={actual_count}"
        )

        if actual_count != expected_count:
            raise ValueError(
                f"Raw master validation failed for {month}: "
                f"uploaded file has {expected_count} rows, "
                f"updated master has {actual_count} rows."
            )

    print(
        "✅ Raw master validation passed for all uploaded months"
    )

    # ---------------------------------------------------------
    # Save candidate master LOCALLY only
    # ---------------------------------------------------------

    df_updated = df_updated.drop(
        columns=["month_key"],
        errors="ignore",
    )

    df_updated.to_csv(
        raw_master_path,
        index=False,
    )

    print(
        "✅ Updated KeHE raw master saved locally "
        "(not yet uploaded to Supabase)"
    )

    print("===== END KEHE RAW MASTER UPDATE =====\n")

    return months_in_upload


def update_kehe_processed_data(
    raw_master_path,
    processed_current_path,
    processed_previous_path,
    org_id: str,
    expected_months=None,
):
    """
    Builds and validates the KeHE processed file from the exact
    local raw master created in the current pipeline run.

    Important:
    - DOES NOT re-download raw_master from Supabase.
    - DOES NOT upload processed data to Supabase.
    - Confirms uploaded months propagate through the transform.
    """
    print("\n===== START KEHE PROCESSED UPDATE =====")
    print("Org ID:", org_id)

    raw_master_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ---------------------------------------------------------
    # Use exact validated candidate from current pipeline
    # ---------------------------------------------------------

    if not raw_master_path.exists():
        raise FileNotFoundError(
            f"Validated local raw master not found: "
            f"{raw_master_path}"
        )

    print("Reading validated local raw master...")

    df_raw = pd.read_csv(raw_master_path)

    print("✅ Local raw master loaded")
    print("Raw master rows:", len(df_raw))
    print("Raw master columns:", df_raw.columns.tolist())

    if df_raw.empty:
        raise ValueError("Raw master is empty.")

    if "DateRangeSelected" not in df_raw.columns:
        raise ValueError(
            "Raw master is missing required column: "
            "DateRangeSelected"
        )

    raw_with_month = _add_month_key(df_raw)

    raw_months = sorted(
        raw_with_month["month_key"]
        .astype(str)
        .unique()
        .tolist()
    )

    print("Raw master months:", raw_months)

    # Extra defensive check that the exact local candidate we're
    # about to process contains every uploaded month.
    if expected_months is not None:
        missing_raw_months = (
            set(expected_months)
            - set(raw_with_month["month_key"].unique())
        )

        if missing_raw_months:
            raise ValueError(
                "Validated raw master is missing uploaded months: "
                f"{sorted(str(m) for m in missing_raw_months)}"
            )

    print("Normalizing KeHE upload...")

    df_raw = normalize_kehe_upload(df_raw)

    print("✅ KeHE raw data normalized")

    processed_current_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ---------------------------------------------------------
    # Back up prior local processed artifact
    # ---------------------------------------------------------

    if processed_current_path.exists():
        print("Existing local processed file found")

        if processed_previous_path.exists():
            processed_previous_path.unlink()

        processed_current_path.replace(
            processed_previous_path
        )

        print(
            "Moved current processed file to previous:",
            processed_previous_path,
        )

    # ---------------------------------------------------------
    # Transform
    # ---------------------------------------------------------

    print("Running KeHE transform...")

    try:
        df_processed = transform_kehe_full_pod_vendor(
            df_raw,
            org_id=org_id,
        )

    except Exception as e:
        print("❌ TRANSFORM ERROR")
        print("Error:", repr(e))
        raise

    print("✅ Transform complete")
    print("Processed rows:", len(df_processed))
    print(
        "Processed columns:",
        df_processed.columns.tolist(),
    )

    if df_processed.empty:
        raise ValueError("Processed dataframe is empty.")

    # ---------------------------------------------------------
    # TEST #2 — uploaded month propagated through transform
    # ---------------------------------------------------------

    processed_months = _get_months_from_processed(
        df_processed
    )

    print(
        "Processed months:",
        sorted(str(month) for month in processed_months),
    )

    if expected_months is not None:
        missing_processed_months = (
            set(expected_months)
            - processed_months
        )

        if missing_processed_months:
            raise ValueError(
                "KeHE processed validation failed. "
                "Uploaded months missing after transform: "
                f"{sorted(str(m) for m in missing_processed_months)}"
            )

        print(
            "✅ Processed validation passed for all uploaded months"
        )

    # ---------------------------------------------------------
    # Save candidate processed file LOCALLY only
    # ---------------------------------------------------------

    print("Saving processed parquet locally...")

    try:
        df_processed.to_parquet(
            processed_current_path,
            index=False,
        )

        print(
            "✅ Parquet saved:",
            processed_current_path,
        )

    except Exception as e:
        print("❌ PARQUET ERROR")
        print("Error:", repr(e))
        raise

    print(
        "✅ KeHE processed candidate ready locally "
        "(not yet uploaded to Supabase)"
    )

    print("===== END KEHE PROCESSED UPDATE =====\n")

    return df_processed


def normalize_kehe_upload(df):
    df = df.copy()

    if "DateRangeSelected" in df.columns:
        parts = (
            df["DateRangeSelected"]
            .astype(str)
            .str.split(" to ")
        )

        if "DateRangeStart_Month" not in df.columns:
            df["DateRangeStart_Month"] = parts.str[0]

        if "DateRangeEnd" not in df.columns:
            df["DateRangeEnd"] = parts.str[-1]

    return df
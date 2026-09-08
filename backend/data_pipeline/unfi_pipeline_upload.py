import pandas as pd
import shutil

from backend.transforms.unfi_upload import transform_unfi_upload
from backend.supabase.storage import upload_file, download_file


def update_unfi_raw_master(
    raw_new_month_path,
    raw_master_path,
    raw_master_previous_path,
    selected_month: str,
    org_id: str,
):
    """
    Updates the raw UNFI master from a manually uploaded monthly CSV.

    The UNFI export does not contain the reporting month, so selected_month
    is supplied externally in YYYY-MM format and stamped onto every row.

    This function ONLY updates the raw master.
    It does not transform or process the data.
    """

    print("\n===== START UNFI RAW MASTER UPDATE =====")
    print("New upload path:", raw_new_month_path)
    print("Org ID:", org_id)
    print("Selected month:", selected_month)

    # -----------------------------------------------------
    # Load uploaded CSV
    # -----------------------------------------------------

    df_new = pd.read_csv(
        raw_new_month_path,
        dtype={
            "UPC": "string",
            "Product Code": "string",
            "Source Number": "string",
            "Zip": "string",
        },
    )

    print("Uploaded rows:", len(df_new))
    print("Uploaded columns:", df_new.columns.tolist())

    if df_new.empty:
        raise ValueError("Uploaded UNFI file is empty.")

    # -----------------------------------------------------
    # Validate expected UNFI columns
    # -----------------------------------------------------

    required_columns = {
        "Store",
        "Chain",
        "UPC",
        "Product Code",
        "Product/UPC",
        "Cases Shipped Selected Period",
        "Sales Dollars Selected Period",
    }

    missing_columns = sorted(
        required_columns - set(df_new.columns)
    )

    if missing_columns:
        raise ValueError(
            "UNFI file is missing required column(s): "
            + ", ".join(missing_columns)
        )

    # -----------------------------------------------------
    # Validate selected month
    # -----------------------------------------------------

    try:
        month_period = pd.Period(
            selected_month,
            freq="M",
        )
    except Exception as exc:
        raise ValueError(
            "selected_month must be in YYYY-MM format."
        ) from exc

    month_string = str(month_period)

    # -----------------------------------------------------
    # Stamp report month onto every row
    # -----------------------------------------------------

    df_new["user_report_month"] = month_string
    print("Stamped report month:", month_string)

    # -----------------------------------------------------
    # Upload the individual raw upload
    # -----------------------------------------------------

    upload_file(
        local_path=str(raw_new_month_path),
        org_id=org_id,
        remote_path="raw/unfi/raw_current_month.csv",
    )

    print("✅ Uploaded raw UNFI current month")

    # -----------------------------------------------------
    # Attempt to download existing raw master
    # -----------------------------------------------------

    raw_master_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if raw_master_path.exists():
        master_exists = True
        print("✅ Using existing local UNFI raw master")

    else:
        print("Attempting to download existing UNFI raw master...")

        try:
            download_file(
                org_id=org_id,
                remote_path="raw/unfi/raw_master.csv",
                local_path=str(raw_master_path),
            )

            master_exists = True
            print("✅ Downloaded existing UNFI raw master")

        except FileNotFoundError:
            master_exists = False
            print(
                "No existing UNFI raw master found. "
                "Creating new master."
            )

        except Exception as exc:
            print("❌ FAILED TO DOWNLOAD EXISTING UNFI RAW MASTER")
            print("Error:", repr(exc))
            raise


    # -----------------------------------------------------
    # First upload for this org
    # -----------------------------------------------------

    if not master_exists:
        df_new.to_csv(
            raw_master_path,
            index=False,
        )

        upload_file(
            local_path=str(raw_master_path),
            org_id=org_id,
            remote_path="raw/unfi/raw_master.csv",
        )

        print("✅ Created and uploaded new UNFI raw master")
        print("===== END UNFI RAW MASTER UPDATE =====\n")

        return

    # -----------------------------------------------------
    # Load existing raw master
    # -----------------------------------------------------

    df_master = pd.read_csv(
        raw_master_path,
        dtype={
            "UPC": "string",
            "Product Code": "string",
            "Source Number": "string",
            "Zip": "string",
            "user_report_month": "string",
        },
    )

    print("Existing UNFI raw master rows:", len(df_master))

    if df_master.empty:
        raise ValueError(
            "Existing UNFI raw master is empty."
        )

    if "user_report_month" not in df_master.columns:
        raise ValueError(
            "Existing UNFI raw master is missing user_report_month."
        )

    existing_months = sorted(
        df_master["user_report_month"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    print("Existing UNFI months:", existing_months)

    # -----------------------------------------------------
    # Backup current raw master
    # -----------------------------------------------------

    raw_master_previous_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if raw_master_previous_path.exists():
        raw_master_previous_path.unlink()

    print("Backing up existing UNFI raw master...")

    shutil.copy2(
        raw_master_path,
        raw_master_previous_path,
    )

    upload_file(
        local_path=str(raw_master_previous_path),
        org_id=org_id,
        remote_path="raw/unfi/raw_master_previous.csv",
    )

    print("✅ Previous UNFI raw master backed up")

    # -----------------------------------------------------
    # Remove existing rows for selected month
    # -----------------------------------------------------

    rows_before = len(df_master)

    df_master = df_master[
        df_master["user_report_month"].astype(str)
        != month_string
    ].copy()

    rows_removed = (
        rows_before
        - len(df_master)
    )

    if rows_removed:
        print(
            f"Replacing existing {month_string}: "
            f"removed {rows_removed} rows"
        )
    else:
        print(
            f"No existing rows found for {month_string}"
        )

    # -----------------------------------------------------
    # Append newly uploaded month
    # -----------------------------------------------------

    df_updated = pd.concat(
        [
            df_master,
            df_new,
        ],
        ignore_index=True,
    )

    print("Updated UNFI raw master rows:", len(df_updated))

    updated_months = sorted(
        df_updated["user_report_month"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    print("Updated UNFI months:", updated_months)

    # -----------------------------------------------------
    # Save and upload updated raw master
    # -----------------------------------------------------

    df_updated.to_csv(
        raw_master_path,
        index=False,
    )

    upload_file(
        local_path=str(raw_master_path),
        org_id=org_id,
        remote_path="raw/unfi/raw_master.csv",
    )

    print("✅ Updated UNFI raw master uploaded")
    print("===== END UNFI RAW MASTER UPDATE =====\n")


def update_unfi_processed_data(
    raw_master_path,
    processed_current_path,
    processed_previous_path,
    org_id: str,
):
    """
    Processes the manually-uploaded UNFI raw master into the canonical
    UNFI processed parquet.

    This should happen only after any required SKU reconciliation/mapping.
    """

    print("\n===== START UNFI PROCESSED UPDATE =====")
    print("Org ID:", org_id)

    # -----------------------------------------------------
    # Download latest raw master
    # -----------------------------------------------------

    raw_master_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("Downloading latest UNFI raw master...")

    download_file(
        org_id=org_id,
        remote_path="raw/unfi/raw_master.csv",
        local_path=str(raw_master_path),
    )

    print("✅ UNFI raw master downloaded")

    # -----------------------------------------------------
    # Load raw master
    # -----------------------------------------------------

    df_raw = pd.read_csv(
        raw_master_path,
        dtype={
            "UPC": "string",
            "Product Code": "string",
            "Source Number": "string",
            "Zip": "string",
            "user_report_month": "string",
        },
    )

    print("UNFI raw master rows:", len(df_raw))
    print("UNFI raw master columns:", df_raw.columns.tolist())

    if df_raw.empty:
        raise ValueError(
            "UNFI raw master is empty."
        )

    if "user_report_month" not in df_raw.columns:
        raise ValueError(
            "UNFI raw master is missing user_report_month."
        )

    # -----------------------------------------------------
    # Transform
    # -----------------------------------------------------

    print("Transforming UNFI upload...")

    df_processed = transform_unfi_upload(
        df_raw,
        org_id=org_id,
    )

    if df_processed.empty:
        raise ValueError(
            "UNFI transform returned an empty dataframe."
        )

    print(
        "Processed UNFI rows:",
        len(df_processed),
    )

    print(
        "Processed UNFI columns:",
        df_processed.columns.tolist(),
    )

    # -----------------------------------------------------
    # Ensure output directory
    # -----------------------------------------------------

    processed_current_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    processed_previous_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -----------------------------------------------------
    # Backup current processed version
    # -----------------------------------------------------

    if processed_previous_path.exists():
        processed_previous_path.unlink()

    if processed_current_path.exists():
        print(
            "Backing up existing UNFI processed parquet..."
        )

        processed_current_path.replace(
            processed_previous_path
        )

        upload_file(
            local_path=str(
                processed_previous_path
            ),
            org_id=org_id,
            remote_path=(
                "processed_sources/"
                "unfi_processed_previous.parquet"
            ),
        )

        print(
            "✅ Previous UNFI processed parquet backed up"
        )

    # -----------------------------------------------------
    # Save new processed parquet
    # -----------------------------------------------------

    df_processed.to_parquet(
        processed_current_path,
        index=False,
    )

    print(
        "Saved UNFI processed parquet locally:",
        processed_current_path,
    )

    # -----------------------------------------------------
    # Upload processed parquet
    # -----------------------------------------------------

    upload_file(
        local_path=str(
            processed_current_path
        ),
        org_id=org_id,
        remote_path=(
            "processed_sources/"
            "unfi_processed.parquet"
        ),
    )

    print("✅ UNFI processed parquet uploaded")
    print("===== END UNFI PROCESSED UPDATE =====\n")
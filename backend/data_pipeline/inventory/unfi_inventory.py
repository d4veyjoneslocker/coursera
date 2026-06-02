import pandas as pd

from backend.data_pipeline.inventory.inventory_helpers import (
    get_inventory_file_paths,
)
from backend.supabase.storage import upload_file, download_file


def update_unfi_inventory_raw_master(
    raw_new_month_path,
    org_id: str,
):
    paths = get_inventory_file_paths(org_id, "unfi")

    raw_master_path = paths["raw_master"]
    raw_master_previous_path = paths["raw_master_previous"]

    # -----------------------------
    # Read new upload
    # -----------------------------
    df_new = pd.read_csv(raw_new_month_path)

    if df_new.empty:
        raise ValueError("Uploaded UNFI inventory file is empty.")

    # -----------------------------
    # Upload current raw file
    # -----------------------------
    try:
        upload_file(
            local_path=str(raw_new_month_path),
            org_id=org_id,
            remote_path="raw/inventory/unfi/raw_current_month.csv",
        )

        print("✅ Uploaded UNFI inventory current month")

    except Exception as e:
        print(
            "⚠️ UNFI inventory current month upload failed:",
            repr(e),
        )

    # -----------------------------
    # Ensure local folders exist
    # -----------------------------
    raw_master_path.parent.mkdir(parents=True, exist_ok=True)

    # -----------------------------
    # Try downloading existing master
    # -----------------------------
    try:
        download_file(
            org_id=org_id,
            remote_path="raw/inventory/unfi/raw_master.csv",
            local_path=str(raw_master_path),
        )

        master_exists = True
        print("✅ Downloaded existing UNFI inventory master")

    except Exception as e:
        master_exists = False
        print("⚠️ No existing UNFI inventory master found:", repr(e))

    # -----------------------------
    # First upload case
    # -----------------------------
    if not master_exists:
        df_new.to_csv(raw_master_path, index=False)

        try:
            upload_file(
                local_path=str(raw_master_path),
                org_id=org_id,
                remote_path="raw/inventory/unfi/raw_master.csv",
            )

            print("✅ Created new UNFI inventory master")

        except Exception as e:
            print(
                "⚠️ UNFI inventory master upload failed:",
                repr(e),
            )

        return

    # -----------------------------
    # Read existing master
    # -----------------------------
    df_master = pd.read_csv(raw_master_path)

    # -----------------------------
    # Backup previous master
    # -----------------------------
    raw_master_previous_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if raw_master_previous_path.exists():
        raw_master_previous_path.unlink()

    raw_master_path.replace(raw_master_previous_path)

    try:
        upload_file(
            local_path=str(raw_master_previous_path),
            org_id=org_id,
            remote_path="raw/inventory/unfi/raw_master_previous.csv",
        )

        print("✅ Uploaded previous UNFI inventory master")

    except Exception as e:
        print(
            "⚠️ Previous UNFI inventory master upload failed:",
            repr(e),
        )

    # -----------------------------
    # Append new inventory data
    # -----------------------------
    df_updated = pd.concat(
        [df_master, df_new],
        ignore_index=True,
    )

    # -----------------------------
    # Save updated master
    # -----------------------------
    df_updated.to_csv(raw_master_path, index=False)

    try:
        upload_file(
            local_path=str(raw_master_path),
            org_id=org_id,
            remote_path="raw/inventory/unfi/raw_master.csv",
        )

        print("✅ Uploaded updated UNFI inventory master")

    except Exception as e:
        print(
            "⚠️ Updated UNFI inventory master upload failed:",
            repr(e),
        )


if __name__ == "__main__":
    update_unfi_inventory_raw_master(
        raw_new_month_path="backend/data/default_org/raw/inventory/unfi/unfi_inventory_new.csv",
        org_id="default_org",
    )
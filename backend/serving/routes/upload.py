from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.data_pipeline.pipeline_helpers import get_source_file_paths
from backend.data_pipeline.kehe_pipeline import (
    update_kehe_raw_master,
    update_kehe_processed_data,
)
from backend.data_pipeline.generate_tables import save_base_tables
from backend.data_pipeline.table_loader import clear_table_cache
import pandas as pd
from io import StringIO

router = APIRouter(prefix="/upload", tags=["Uploads"])


REQUIRED_COLUMNS_KEHE = [
    "DateRangeSelected",
    "CustomerPostalCode",
    'Addressline1',
    'CurrentYearQTY',
    'CustomerCity',
    'CustomerName',
    'CustomerStateCode',
    "RetailerName",
    'DC',
    'ProductSize',
    'UPC',
    'AddressBookNumber',
    'CurrentYearCost'
]


@router.post("/kehe")
async def upload_kehe(org_id: str, file: UploadFile = File(...)):
    org_id = org_id

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file was uploaded.")

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")

    paths = get_source_file_paths(org_id, "kehe")
    raw_new_month_path = paths["raw_new_month"]

    try:
        raw_new_month_path.parent.mkdir(parents=True, exist_ok=True)

        contents = await file.read()

        if not contents:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        print("1. file received")

        # -----------------------------
        # Column validation (NEW)
        # -----------------------------
        df_check = pd.read_csv(StringIO(contents.decode("utf-8")), nrows=5)

        missing_cols = [col for col in REQUIRED_COLUMNS_KEHE if col not in df_check.columns]

        if missing_cols:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_cols)}",
            )

        print("2. column validation passed")

        # -----------------------------
        # Save file
        # -----------------------------
        with raw_new_month_path.open("wb") as f:
            f.write(contents)
        print("3. raw file saved")

        # -----------------------------
        # Update raw + processed KeHE
        # -----------------------------
        update_kehe_raw_master(
            raw_new_month_path=paths["raw_new_month"],
            raw_master_path=paths["raw_master"],
            raw_master_previous_path=paths["raw_master_previous"],
        )
        print("4. raw master updated")

        update_kehe_processed_data(
            raw_master_path=paths["raw_master"],
            processed_current_path=paths["processed_current"],
            processed_previous_path=paths["processed_previous"],
            org_id=org_id
        )
        print("5. processed kehe updated")

        # -----------------------------
        # Rebuild combined tables (LOCAL ONLY)
        # -----------------------------
        save_base_tables(
            output_dir=f"backend/data/{org_id}",
            org_id=org_id,
        )
        print("6. base tables saved")

        # -----------------------------
        # Clear cache (in-process)
        # -----------------------------
        clear_table_cache(org_id)
        print("7. cache cleared")

        df_features = pd.read_parquet(f"backend/data/{org_id}/features_df.parquet")

        return {
            "status": "success",
            "message": f"{file.filename} uploaded and dashboard refreshed successfully.",
            "rows": len(df_features),
            "data_through": str(df_features["month_year"].max()) if "month_year" in df_features.columns else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
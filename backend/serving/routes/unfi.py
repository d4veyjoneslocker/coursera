import os

from fastapi import APIRouter, HTTPException

from backend.data_pipeline.unfi_pipeline import refresh_unfi_processed_data
from backend.data_pipeline.generate_tables import save_base_tables
from backend.data_pipeline.table_loader import clear_table_cache 
router = APIRouter(prefix="/unfi", tags=["UNFI"])


@router.post("/refresh")
def refresh_unfi(org_id: str):
    org_id = org_id

    unfi_cred = {
        "account_id": os.getenv("UNFI_ACCOUNT_ID"),
        "connector_id": os.getenv("UNFI_CONNECTOR_ID"),
        "username": os.getenv("UNFI_USERNAME"),
        "password": os.getenv("UNFI_PASSWORD"),
    }

    if not all(unfi_cred.values()):
        raise HTTPException(
            status_code=500,
            detail="Missing UNFI credentials in environment.",
        )

    try:
        refresh_unfi_processed_data(
            unfi_cred=unfi_cred,
            org_id=org_id,
        )

        save_base_tables(
            output_dir=f"backend/data/{org_id}",
            org_id=org_id,
        )

        clear_table_cache(org_id)


        return {
            "status": "success",
            "message": "UNFI data refreshed and dashboard updated.",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"UNFI refresh failed: {str(e)}",
        )
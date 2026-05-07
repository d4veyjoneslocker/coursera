from fastapi import APIRouter
from pathlib import Path
import io
from io import BytesIO
import zipfile
import shutil
import pandas as pd

from fastapi.responses import FileResponse, StreamingResponse
from starlette.background import BackgroundTask
from datetime import datetime
from backend.data_pipeline.table_loader import load_org_tables


from backend.exports.ai_ready.export_tables import (
    export_monthly_summary, 
    export_summary_by_grain, 
    export_store_level_table
)


router = APIRouter(prefix="/exports", tags=["Exports"])


EXPORT_DIR = Path("tmp_exports")
EXPORT_DIR.mkdir(exist_ok=True)


@router.get("/ai_package")
def export_ai_package(org_id: str):
    features_df = load_org_tables(org_id)

    df = features_df.copy()

    # unique folder per request
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    export_path = EXPORT_DIR / f"export_{timestamp}"
    export_path.mkdir(parents=True, exist_ok=True)

    zip_path = export_path / "ai_package.zip"

    # -------------------------
    # Build files
    # -------------------------
    export_monthly_summary(df).to_csv(export_path / "monthly_summary.csv", index=False)
    export_summary_by_grain(df, ["chain"]).to_csv(export_path / "chain_summary.csv", index=False)
    export_summary_by_grain(df, ["sku"]).to_csv(export_path / "sku_summary.csv", index=False)
    export_store_level_table(df, []).to_csv(export_path / "store_summary.csv", index=False)

    # -------------------------
    # Zip files
    # -------------------------
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in export_path.glob("*.csv"):
            zf.write(file, arcname=file.name)

    # -------------------------
    # Return download
    # -------------------------
    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename="ai_package.zip",
        background=BackgroundTask(lambda: shutil.rmtree(export_path, ignore_errors=True)),
    )

@router.get("/store_list")
def export_store_list(org_id: str):
    df = load_org_tables(org_id)

    result = (
        df.groupby("coded_customer", as_index=False)
        .agg({
            "chain": "first",
            "store_number": "first",
            "street_address": "first",
            "city": "first",
            "state": "first",
            "zip": "first",
        })
    )

    output = io.StringIO()
    result.to_csv(output, index=False)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=store_list.csv"
        },
    )
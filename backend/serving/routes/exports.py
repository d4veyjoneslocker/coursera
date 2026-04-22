from fastapi import APIRouter
from pathlib import Path
import zipfile

from fastapi.responses import FileResponse
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


@router.get("/export/ai_package")
def export_ai_package():
    features_df = load_org_tables("default_org")

    df = features_df.copy()

    # unique folder per request
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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
    )
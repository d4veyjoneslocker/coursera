import pandas as pd
from io import StringIO

from fastapi import APIRouter, UploadFile, File, HTTPException

from backend.data_pipeline.pipeline_helpers import get_source_file_paths
from backend.data_pipeline.kehe_pipeline import (
    update_kehe_raw_master,
    update_kehe_processed_data,
)
from backend.data_pipeline.generate_tables import save_base_tables
from backend.data_pipeline.table_loader import clear_table_cache
from backend.storage.local_cleanup import delete_local_org_data
from backend.supabase.storage import (
    get_supabase_client,
    upload_file,
)


router = APIRouter(prefix="/upload", tags=["Uploads"])


REQUIRED_COLUMNS_KEHE = [
    "DateRangeSelected",
    "CustomerPostalCode",
    "Addressline1",
    "CurrentYearQTY",
    "CustomerCity",
    "CustomerName",
    "CustomerStateCode",
    "RetailerName",
    "DC",
    "ProductSize",
    "UPC",
    "AddressBookNumber",
    "CurrentYearCost",
]


@router.post("/kehe")
async def upload_kehe(
    org_id: str,
    files: list[UploadFile] = File(...),
):
    if not files:
        raise HTTPException(
            status_code=400,
            detail="No files were uploaded.",
        )

    paths = get_source_file_paths(org_id, "kehe")
    raw_new_month_path = paths["raw_new_month"]

    try:
        raw_new_month_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        print(f"1. received {len(files)} KeHE file(s)")

        # =================================================
        # Validate + combine uploaded CSVs
        # =================================================

        uploaded_dfs = []

        for file in files:
            if not file.filename:
                raise HTTPException(
                    status_code=400,
                    detail="One of the uploaded files has no filename.",
                )

            if not file.filename.lower().endswith(".csv"):
                raise HTTPException(
                    status_code=400,
                    detail=f"{file.filename} is not a CSV file.",
                )

            contents = await file.read()

            if not contents:
                raise HTTPException(
                    status_code=400,
                    detail=f"{file.filename} is empty.",
                )

            try:
                df = pd.read_csv(
                    StringIO(contents.decode("utf-8"))
                )

            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Could not read {file.filename}: "
                        f"{str(e)}"
                    ),
                )

            missing_cols = [
                col
                for col in REQUIRED_COLUMNS_KEHE
                if col not in df.columns
            ]

            if missing_cols:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"{file.filename} is missing required columns: "
                        + ", ".join(missing_cols)
                    ),
                )

            uploaded_dfs.append(df)

            print(
                f"✅ validated {file.filename}: "
                f"{len(df)} rows"
            )

        df_upload = pd.concat(
            uploaded_dfs,
            ignore_index=True,
        )

        print(
            f"2. combined upload: "
            f"{len(df_upload)} total rows"
        )

        # =================================================
        # Determine months in combined upload
        # =================================================

        dates = pd.to_datetime(
            df_upload["DateRangeSelected"]
            .astype(str)
            .str.split(" to ")
            .str[0],
            errors="coerce",
        )

        uploaded_months = (
            dates
            .dropna()
            .dt.to_period("M")
            .unique()
            .tolist()
        )

        if not uploaded_months:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Could not determine any valid months "
                    "from DateRangeSelected."
                ),
            )

        print(
            "3. uploaded months:",
            [str(month) for month in uploaded_months],
        )

        # =================================================
        # Save combined upload locally
        # =================================================

        df_upload.to_csv(
            raw_new_month_path,
            index=False,
        )

        print(
            "4. combined raw upload saved locally:",
            raw_new_month_path,
        )

        # =================================================
        # TEST #1
        #
        # Build candidate raw_master locally.
        #
        # update_kehe_raw_master verifies that each uploaded
        # month's row count in the resulting raw master
        # exactly matches that month's row count in the
        # incoming upload.
        #
        # Nothing canonical is published yet.
        # =================================================

        pipeline_months = update_kehe_raw_master(
            raw_new_month_path=paths["raw_new_month"],
            raw_master_path=paths["raw_master"],
            raw_master_previous_path=paths["raw_master_previous"],
            org_id=org_id,
        )

        print(
            "5. raw master candidate validated:",
            [str(month) for month in pipeline_months],
        )

        # =================================================
        # TEST #2
        #
        # Transform the exact validated local raw master.
        # Confirm uploaded month(s) survive into processed
        # KeHE data.
        #
        # Still nothing canonical is published.
        # =================================================

        update_kehe_processed_data(
            raw_master_path=paths["raw_master"],
            processed_current_path=paths["processed_current"],
            processed_previous_path=paths["processed_previous"],
            org_id=org_id,
            expected_months=pipeline_months,
        )

        print("6. processed KeHE candidate validated")

        # =================================================
        # Build candidate features_df locally
        #
        # KeHE:
        #     use fresh local candidate from this run
        #
        # UNFI:
        #     force latest persisted canonical processed
        #     version from Supabase rather than trusting a
        #     stale local copy
        #
        # DO NOT upload features_df yet.
        # =================================================

        features_df, features_path = save_base_tables(
            output_dir=f"backend/data/{org_id}",
            org_id=org_id,
            upload=False,
            refresh_sources={"unfi"},
        )

        print("7. features_df candidate built")

        # =================================================
        # TEST #3
        #
        # Verify each uploaded month actually exists in the
        # final dataframe SKUba APIs consume.
        # =================================================

        required_feature_cols = {
            "year",
            "month",
        }

        if not required_feature_cols.issubset(
            features_df.columns
        ):
            raise ValueError(
                "features_df is missing required "
                "year/month columns."
            )

        feature_month_rows = (
            features_df[
                ["year", "month"]
            ]
            .copy()
        )

        feature_month_rows["year"] = pd.to_numeric(
            feature_month_rows["year"],
            errors="coerce",
        )

        feature_month_rows["month"] = pd.to_numeric(
            feature_month_rows["month"],
            errors="coerce",
        )

        feature_month_rows = (
            feature_month_rows
            .dropna()
            .drop_duplicates()
        )

        feature_months = {
            pd.Period(
                year=int(row.year),
                month=int(row.month),
                freq="M",
            )
            for row in feature_month_rows.itertuples(
                index=False
            )
        }

        missing_feature_months = [
            month
            for month in pipeline_months
            if month not in feature_months
        ]

        if missing_feature_months:
            raise ValueError(
                "Final features_df validation failed. "
                "Uploaded month(s) did not propagate into "
                "the final dataset: "
                + ", ".join(
                    str(month)
                    for month in missing_feature_months
                )
            )

        print(
            "8. features_df validated for months:",
            [str(month) for month in pipeline_months],
        )

        # =================================================
        # COMMIT
        #
        # All candidate stages have passed.
        #
        # Only now publish canonical artifacts.
        # =================================================

        print("9. publishing canonical artifacts...")

        upload_file(
            local_path=str(
                paths["raw_master"]
            ),
            org_id=org_id,
            remote_path=(
                "raw/kehe/raw_master.csv"
            ),
        )

        print("✅ raw_master published")

        upload_file(
            local_path=str(
                paths["processed_current"]
            ),
            org_id=org_id,
            remote_path=(
                "processed_sources/"
                "kehe_processed.parquet"
            ),
        )

        print("✅ KeHE processed published")

        upload_file(
            local_path=str(
                features_path
            ),
            org_id=org_id,
            remote_path=(
                "processed/features_df.parquet"
            ),
        )

        print("✅ features_df published")

        # =================================================
        # Record uploaded month coverage
        #
        # This happens only after features_df itself has
        # been validated and persisted.
        # =================================================

        supabase = get_supabase_client()

        month_rows = [
            {
                "org_id": org_id,
                "distributor": "kehe",
                "month": f"{month}-01",
            }
            for month in pipeline_months
        ]

        if month_rows:
            (
                supabase
                .table("org_distributor_months")
                .upsert(
                    month_rows,
                    on_conflict=(
                        "org_id,"
                        "distributor,"
                        "month"
                    ),
                )
                .execute()
            )

        print("10. uploaded months recorded")

        # =================================================
        # Clear runtime state only after successful commit
        # =================================================

        clear_table_cache(org_id)

        print("11. cache cleared")

        delete_local_org_data(org_id)

        print("12. local storage cleared")

        return {
            "status": "success",
            "message": (
                f"{len(files)} KeHE file"
                f"{'' if len(files) == 1 else 's'} "
                "uploaded successfully."
            ),
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}",
        )


@router.get("/kehe/months")
def get_kehe_uploaded_months(
    org_id: str,
):
    try:
        supabase = get_supabase_client()

        response = (
            supabase
            .table("org_distributor_months")
            .select("month")
            .eq("org_id", org_id)
            .eq("distributor", "kehe")
            .order("month")
            .execute()
        )

        months = [
            row["month"][:7]
            for row in (
                response.data or []
            )
        ]

        return {
            "months": months,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                "Could not determine uploaded KeHE "
                f"months: {str(e)}"
            ),
        )
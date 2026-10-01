import math
import numpy as np
import pandas as pd
from io import StringIO

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)

from backend.free_trial.run_insights import run_available_insights
from backend.data_pipeline.table_loader import load_org_tables, load_active_pods
from backend.data_pipeline.kehe_pipeline import update_kehe_raw_master, update_kehe_processed_data
from backend.data_pipeline.unfi_pipeline_upload import update_unfi_raw_master, update_unfi_processed_data
from backend.data_pipeline.generate_tables import save_base_tables
from backend.data_pipeline.pipeline_helpers import get_source_file_paths
from backend.supabase.storage import download_file, get_supabase_client, upload_file


router = APIRouter(
    prefix="/free-trial",
    tags=["free-trial"],
)


# =========================================================
# Helpers
# =========================================================


def clean_payload(value):
    if isinstance(value, dict):
        return {
            key: clean_payload(val)
            for key, val in value.items()
        }

    if isinstance(value, list):
        return [
            clean_payload(item)
            for item in value
        ]

    if isinstance(
        value,
        (
            float,
            np.floating,
        ),
    ) and math.isnan(value):
        return None

    return value


# =========================================================
# Free trial uploads
# =========================================================


@router.post("/upload/kehe")
async def upload_free_trial_kehe(
    files: list[UploadFile] = File(...),
    org_id: str = Form(...),
):
    """
    Free-trial KeHE upload.

    RAW ONLY.

    Accepts one or more KeHE CSVs, combines them, updates the
    canonical raw master, and records uploaded month coverage.

    Does NOT:
    - transform KeHE
    - create kehe_processed.parquet
    - build features_df
    - run insights

    Processing waits until onboarding configuration,
    including SKU reconciliation, is complete.
    """

    if not files:
        raise HTTPException(
            status_code=400,
            detail="No files were uploaded.",
        )

    paths = get_source_file_paths(
        org_id,
        "kehe",
    )

    raw_new_month_path = paths["raw_new_month"]

    raw_new_month_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        # =====================================================
        # Validate + combine uploaded CSVs
        # =====================================================

        uploaded_dfs = []

        for file in files:
            if (
                not file.filename
                or not file.filename.lower().endswith(".csv")
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Please upload KeHE CSV files.",
                )

            contents = await file.read()

            if not contents:
                raise HTTPException(
                    status_code=400,
                    detail=f"{file.filename} is empty.",
                )

            try:
                df = pd.read_csv(
                    StringIO(
                        contents.decode("utf-8")
                    )
                )
            except Exception as exc:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Could not read {file.filename}: "
                        f"{str(exc)}"
                    ),
                ) from exc

            # We need this column to determine the
            # report month(s).
            if "DateRangeSelected" not in df.columns:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"{file.filename} is missing "
                        "DateRangeSelected."
                    ),
                )

            uploaded_dfs.append(df)

        df_upload = pd.concat(
            uploaded_dfs,
            ignore_index=True,
        )

        # =====================================================
        # Save combined upload locally
        # =====================================================

        df_upload.to_csv(
            raw_new_month_path,
            index=False,
        )

        # =====================================================
        # Update RAW master
        #
        # update_kehe_raw_master returns the months contained
        # in this upload as pd.Period values.
        # =====================================================

        pipeline_months = update_kehe_raw_master(
            raw_new_month_path=raw_new_month_path,
            raw_master_path=paths["raw_master"],
            raw_master_previous_path=paths[
                "raw_master_previous"
            ],
            org_id=org_id,
        )

        if not pipeline_months:
            raise ValueError(
                "Could not determine any valid months "
                "from the KeHE upload."
            )

        # =====================================================
        # Persist canonical RAW master
        #
        # Important for free trial: processing may happen in
        # a later request / worker, so the raw master cannot
        # exist only on local disk.
        # =====================================================

        upload_file(
            local_path=str(
                paths["raw_master"]
            ),
            org_id=org_id,
            remote_path=(
                "raw/kehe/raw_master.csv"
            ),
        )

        # =====================================================
        # Record raw upload coverage
        # =====================================================

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
                .table(
                    "org_distributor_months"
                )
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

        return {
            "status": "uploaded",
            "distributor": "kehe",
            "months": [
                str(month)
                for month in pipeline_months
            ],
            "processed": False,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:
        print(
            "FREE TRIAL KEHE UPLOAD ERROR:",
            repr(exc),
        )

        raise HTTPException(
            status_code=500,
            detail="KeHE upload failed, try again.",
        ) from exc


@router.post("/upload/unfi")
async def upload_free_trial_unfi(
    file: UploadFile = File(...),
    org_id: str = Form(...),
    month: str = Form(...),
    confirm_all_results: bool = Form(False),
):
    """
    Free-trial UNFI upload.

    RAW ONLY.

    `month` must be supplied as YYYY-MM.

    Example:
        2026-08

    Updates the canonical raw master and records raw
    upload coverage.

    Does NOT:
    - transform UNFI
    - create unfi_processed.parquet
    - build features_df
    - run insights

    Processing waits until onboarding configuration,
    including SKU reconciliation, is complete.
    """

    if (
        not file.filename
        or not file.filename.lower().endswith(".csv")
    ):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file.",
        )

    # =========================================================
    # Validate month
    # =========================================================

    try:
        selected_period = pd.Period(
            month,
            freq="M",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid report month. "
                "Expected YYYY-MM."
            ),
        ) from exc

    month_string = str(selected_period)

    paths = get_source_file_paths(
        org_id,
        "unfi",
    )

    raw_new_month_path = paths[
        "raw_new_month"
    ]

    raw_new_month_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        # =====================================================
        # Save upload locally
        # =====================================================

        contents = await file.read()

        if not contents:
            raise HTTPException(
                status_code=400,
                detail="The uploaded CSV is empty.",
            )

        try:
            df_upload = pd.read_csv(
                StringIO(contents.decode("utf-8"))
            )
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail="Could not read the uploaded UNFI CSV.",
            ) from exc


        # =====================================================
        # Detect likely UNFI 500-row export limit
        # =====================================================

        if len(df_upload) == 500 and not confirm_all_results:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "unfi_possible_truncation",
                    "message": (
                        "This UNFI file contains exactly 500 data rows. "
                        "This can happen when the export is limited instead "
                        "of using 'All results'."
                    ),
                },
            )


        # =====================================================
        # Save upload locally
        # =====================================================

        with open(
            raw_new_month_path,
            "wb",
        ) as f:
            f.write(contents)

        # =====================================================
        # Update RAW master
        #
        # This stamps every incoming UNFI row with:
        # user_report_month = YYYY-MM
        # =====================================================

        update_unfi_raw_master(
            raw_new_month_path=raw_new_month_path,
            raw_master_path=paths[
                "raw_master"
            ],
            raw_master_previous_path=paths[
                "raw_master_previous"
            ],
            selected_month=month_string,
            org_id=org_id,
        )

        # =====================================================
        # Persist canonical RAW master
        #
        # Even if update_unfi_raw_master currently uploads it
        # internally, doing persistence here makes the
        # free-trial route's contract explicit and symmetric
        # with KeHE.
        # =====================================================

        upload_file(
            local_path=str(
                paths["raw_master"]
            ),
            org_id=org_id,
            remote_path=(
                "raw/unfi/raw_master.csv"
            ),
        )

        # =====================================================
        # Record raw upload coverage
        # =====================================================

        supabase = get_supabase_client()

        (
            supabase
            .table(
                "org_distributor_months"
            )
            .upsert(
                {
                    "org_id": org_id,
                    "distributor": "unfi",
                    "month": (
                        f"{month_string}-01"
                    ),
                },
                on_conflict=(
                    "org_id,"
                    "distributor,"
                    "month"
                ),
            )
            .execute()
        )

        return {
            "status": "uploaded",
            "distributor": "unfi",
            "month": month_string,
            "processed": False,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:
        print(
            "FREE TRIAL UNFI UPLOAD ERROR:",
            repr(exc),
        )

        raise HTTPException(
            status_code=500,
            detail="UNFI upload failed.",
        ) from exc

# =========================================================
# Free trial processing
# =========================================================


@router.post("/process")
def process_free_trial(
    org_id: str = Query(...),
):
    """
    Finalize free-trial data after onboarding configuration
    has been completed.

    This endpoint:

    1. Looks for raw KeHE data.
    2. Transforms KeHE if present.
    3. Looks for raw UNFI data.
    4. Transforms UNFI if present.
    5. Builds the combined features dataframe.
    6. Uploads processed/features_df.parquet.

    Only after this endpoint succeeds should the frontend
    navigate to the main free-trial results page.
    """

    print(
        "\n===== START FREE TRIAL PROCESSING ====="
    )
    print(
        "Org ID:",
        org_id,
    )

    try:
        processed_distributors = []

        # =================================================
        # KeHE
        # =================================================

        kehe_paths = get_source_file_paths(
            org_id,
            "kehe",
        )

        kehe_raw_exists = (
            kehe_paths[
                "raw_master"
            ].exists()
        )

        # If there is no local raw master,
        # check canonical storage.
        if not kehe_raw_exists:
            try:
                print(
                    "Checking Supabase for KeHE raw master..."
                )

                download_file(
                    org_id=org_id,
                    remote_path=(
                        "raw/kehe/raw_master.csv"
                    ),
                    local_path=str(
                        kehe_paths[
                            "raw_master"
                        ]
                    ),
                )

                kehe_raw_exists = True

                print(
                    "✅ KeHE raw master found"
                )

            except FileNotFoundError:
                print(
                    "No KeHE raw master found."
                )

            except Exception as exc:
                print(
                    "⚠️ Could not check KeHE raw master:",
                    repr(exc),
                )

                raise

        if kehe_raw_exists:
            print(
                "\nProcessing KeHE..."
            )

            update_kehe_processed_data(
                raw_master_path=kehe_paths[
                    "raw_master"
                ],
                processed_current_path=kehe_paths[
                    "processed_current"
                ],
                processed_previous_path=kehe_paths[
                    "processed_previous"
                ],
                org_id=org_id,
            )

            processed_distributors.append(
                "kehe"
            )

            print(
                "✅ KeHE processing complete"
            )

        # =================================================
        # UNFI
        # =================================================

        unfi_paths = get_source_file_paths(
            org_id,
            "unfi",
        )

        unfi_raw_exists = (
            unfi_paths[
                "raw_master"
            ].exists()
        )

        # If there is no local raw master,
        # check canonical storage.
        if not unfi_raw_exists:
            try:
                print(
                    "Checking Supabase for UNFI raw master..."
                )

                download_file(
                    org_id=org_id,
                    remote_path=(
                        "raw/unfi/raw_master.csv"
                    ),
                    local_path=str(
                        unfi_paths[
                            "raw_master"
                        ]
                    ),
                )

                unfi_raw_exists = True

                print(
                    "✅ UNFI raw master found"
                )

            except FileNotFoundError:
                print(
                    "No UNFI raw master found."
                )

            except Exception as exc:
                print(
                    "⚠️ Could not check UNFI raw master:",
                    repr(exc),
                )

                raise

        if unfi_raw_exists:
            print(
                "\nProcessing UNFI..."
            )

            update_unfi_processed_data(
                raw_master_path=unfi_paths[
                    "raw_master"
                ],
                processed_current_path=unfi_paths[
                    "processed_current"
                ],
                processed_previous_path=unfi_paths[
                    "processed_previous"
                ],
                org_id=org_id,
            )

            processed_distributors.append(
                "unfi"
            )

            print(
                "✅ UNFI processing complete"
            )

        # =================================================
        # Require at least one source
        # =================================================

        if not processed_distributors:
            raise ValueError(
                "No raw distributor data was found to process."
            )

        # =================================================
        # Build combined features table
        # =================================================

        print(
            "\nBuilding combined features dataframe..."
        )

        output_dir = (
            f"backend/data/"
            f"{org_id}/processed"
        )

        (
            features_df,
            active_pods_df,
            fill_rate_df,
            features_path,
            active_pods_path,
            fill_rate_path,
        ) = save_base_tables(
            output_dir=output_dir,
            org_id=org_id,
            upload=True,
        )

        if features_df.empty:
            raise ValueError(
                "Processing completed but features_df is empty."
            )

        print(
            "✅ Combined features dataframe built"
        )

        print(
            "Processed distributors:",
            processed_distributors,
        )

        print(
            "Feature rows:",
            len(features_df),
        )

        print(
            "Saved:",
            features_path,
        )

        print(
            "===== END FREE TRIAL PROCESSING =====\n"
        )

        return {
            "status": "ready",
            "processed": True,
            "distributors": (
                processed_distributors
            ),
            "feature_rows": len(
                features_df
            ),
        }

    except ValueError as exc:
        print(
            "FREE TRIAL PROCESSING ERROR:",
            repr(exc),
        )

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:
        print(
            "FREE TRIAL PROCESSING ERROR:",
            repr(exc),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Free trial processing failed."
            ),
        ) from exc


# =========================================================
# Free trial insights
# =========================================================


@router.get("/insights")
def get_free_trial_insights(org_id: str = Query(...)):
    df = load_org_tables(org_id)
    active_pods_df = load_active_pods(org_id)

    df_all_time = df.copy()

    available_months = (
        df[
            [
                "year",
                "month",
            ]
        ]
        .drop_duplicates()
        .shape[0]
    )

    insights = run_available_insights(
        df=df,
        df_all_time=df_all_time,
        active_pods_df=active_pods_df,
        available_months=available_months,
        filters=None,
    )

    top_findings = insights[:5]

    return {
        "available_months": available_months,
        "top_findings": clean_payload(
            top_findings
        ),
        "additional_findings_count": max(
            len(insights) - 5,
            0,
        ),
    }
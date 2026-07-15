from pathlib import Path
from io import BytesIO
import os

import pandas as pd

from backend.demo.demo_data_generator import generate_dummy_cpg_data
from backend.metrics.features import add_features
from backend.supabase.storage import (
    upload_file,
    get_supabase_client,
    BUCKET_NAME,
)


DEMO_ORG_ID = "839a67d6-7afa-4607-8524-8621184bfabc"


def seed_demo():
    df = generate_dummy_cpg_data()

    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")

    print("Before add_features:")
    print(df["month_year"].min(), "->", df["month_year"].max())

    features_df = add_features(df)

    print("After add_features:")
    print(features_df["month_year"].min(), "->", features_df["month_year"].max())

    temp_path = Path("/tmp/features_df.parquet")
    features_df.to_parquet(temp_path, index=False)

    upload_file(
        local_path=str(temp_path),
        org_id=DEMO_ORG_ID,
        remote_path="processed/features_df.parquet",
    )

    print("✅ Demo features uploaded to Supabase")

    # Download the exact file that was just uploaded
    supabase = get_supabase_client()

    remote_path = f"{DEMO_ORG_ID}/processed/features_df.parquet"

    uploaded_bytes = (
        supabase.storage
        .from_(BUCKET_NAME)
        .download(remote_path)
    )

    uploaded_df = pd.read_parquet(BytesIO(uploaded_bytes))

    print("Remote file latest month:", uploaded_df["month_year"].max())
    print("Supabase URL:", os.getenv("SUPABASE_URL"))
    print("Bucket:", BUCKET_NAME)
    print("Remote path:", remote_path)


if __name__ == "__main__":
    seed_demo()
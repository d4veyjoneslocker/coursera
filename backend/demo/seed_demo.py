from pathlib import Path

import pandas as pd

from backend.demo.demo_data_generator import generate_dummy_cpg_data
from backend.metrics.features import add_features
from backend.supabase.storage import upload_file


DEMO_ORG_ID = "839a67d6-7afa-4607-8524-8621184bfabc"


def seed_demo():
    df = generate_dummy_cpg_data()

    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")

    features_df = add_features(df)

    out_dir = Path(f"backend/data/{DEMO_ORG_ID}/processed")
    out_dir.mkdir(parents=True, exist_ok=True)

    local_path = out_dir / "features_df.parquet"
    features_df.to_parquet(local_path, index=False)

    upload_file(
        local_path=str(local_path),
        org_id=DEMO_ORG_ID,
        remote_path="processed/features_df.parquet",
    )

    print(f"✅ Demo features saved locally: {local_path}")
    print("✅ Demo features uploaded to Supabase")


if __name__ == "__main__":
    seed_demo()
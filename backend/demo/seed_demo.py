from pathlib import Path
import pandas as pd

from backend.demo.demo_data_generator import generate_dummy_cpg_data
from backend.metrics.features import add_features

DEMO_ORG_ID = "839a67d6-7afa-4607-8524-8621184bfabc"

df = generate_dummy_cpg_data()

df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")

features_df = add_features(df)

out_dir = Path(f"backend/data/{DEMO_ORG_ID}")
out_dir.mkdir(parents=True, exist_ok=True)

features_df.to_parquet(out_dir / "features_df.parquet", index=False)

print("✅ Demo org ready")
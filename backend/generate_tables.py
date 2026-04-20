from pathlib import Path
import os

from dotenv import load_dotenv

from backend.crisp_data_pull import pull_crisp_data
from backend.transforms.kehe import transform_kehe_full_pod_vendor
from backend.transforms.unfi import transform_unfi_natural_vendor_sales
from backend.transforms.combine_sources import combine_distributors
from backend.metrics.features import add_features
from backend.tests.validate_data import validate_data


load_dotenv()


def validate_credential_set(cred: dict, source_name: str) -> None:
    required_fields = ["account_id", "connector_id", "username", "password"]

    missing = [field for field in required_fields if not cred.get(field)]
    if missing:
        raise ValueError(
            f"Missing required {source_name} credential fields: {', '.join(missing)}"
        )


def build_base_tables(
    kehe_cred: dict | None = None,
    unfi_cred: dict | None = None,
):
    if kehe_cred is None and unfi_cred is None:
        raise ValueError("At least one credential set (KEHE or UNFI) is required.")

    clean_kehe_df = None
    clean_unfi_df = None

    if kehe_cred is not None:
        validate_credential_set(kehe_cred, "KEHE")

        raw_kehe_df = pull_crisp_data(
            kehe_cred["account_id"],
            kehe_cred["connector_id"],
            kehe_cred["username"],
            kehe_cred["password"],
            table="Kehe_Full_Pod_Vendor",
        )
        clean_kehe_df = transform_kehe_full_pod_vendor(raw_kehe_df)

    if unfi_cred is not None:
        validate_credential_set(unfi_cred, "UNFI")

        raw_unfi_df = pull_crisp_data(
            unfi_cred["account_id"],
            unfi_cred["connector_id"],
            unfi_cred["username"],
            unfi_cred["password"],
            table="Direct_Unfi_Insights_Natural_Vendor_Sales_Customer_Details_Weekly",
        )
        clean_unfi_df = transform_unfi_natural_vendor_sales(raw_unfi_df)

    if clean_kehe_df is not None and clean_unfi_df is not None:
        combined_df = combine_distributors(clean_kehe_df, clean_unfi_df)
    elif clean_kehe_df is not None:
        combined_df = clean_kehe_df.copy()
    elif clean_unfi_df is not None:
        combined_df = clean_unfi_df.copy()
    else:
        raise ValueError("No usable source data was built.")

    combined_w_features = add_features(combined_df)

    errors = validate_data(combined_df)
    if errors:
        print("❌ Data validation failed:")
        for e in errors:
            print(f"- {e}")
    else:
        print("✅ Data validated")

    return combined_df, combined_w_features


def save_base_tables(
    output_dir: str = "backend/data/default_org",
    kehe_cred: dict | None = None,
    unfi_cred: dict | None = None,
):
    combined_df, combined_w_features = build_base_tables(
        kehe_cred=kehe_cred,
        unfi_cred=unfi_cred,
    )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    combined_df.to_parquet(out / "combined_df.parquet", index=False)
    combined_w_features.to_parquet(out / "combined_w_features.parquet", index=False)

    print(f"✅ base tables saved to {out}")


def get_local_env_credentials():
    kehe_cred = {
        "account_id": os.getenv("KEHE_ACCOUNT_ID"),
        "connector_id": os.getenv("KEHE_CONNECTOR_ID"),
        "username": os.getenv("KEHE_USERNAME"),
        "password": os.getenv("KEHE_PASSWORD"),
    }

    unfi_cred = {
        "account_id": os.getenv("UNFI_ACCOUNT_ID"),
        "connector_id": os.getenv("UNFI_CONNECTOR_ID"),
        "username": os.getenv("UNFI_USERNAME"),
        "password": os.getenv("UNFI_PASSWORD"),
    }

    if not any(kehe_cred.values()):
        kehe_cred = None
    if not any(unfi_cred.values()):
        unfi_cred = None

    return kehe_cred, unfi_cred


if __name__ == "__main__":
    kehe_cred, unfi_cred = get_local_env_credentials()
    save_base_tables(
        output_dir="backend/data/default_org",
        kehe_cred=kehe_cred,
        unfi_cred=unfi_cred,
    )
import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

BUCKET_NAME = "org-data"


def get_supabase_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")

    return create_client(url, key)


def upload_file(local_path: str, org_id: str, remote_path: str, upsert: bool = True):
    """
    Example:
    upload_file(
        local_path="backend/data/org_123/processed/kehe_current.parquet",
        org_id="org_123",
        remote_path="processed/clean_df.parquet",
    )

    Uploads to:
    org-data/org_123/processed/clean_df.parquet
    """
    supabase = get_supabase_client()

    local_path_obj = Path(local_path)
    if not local_path_obj.exists():
        raise FileNotFoundError(f"File not found: {local_path}")

    storage_path = f"{org_id}/{remote_path}"

    with open(local_path_obj, "rb") as f:
        return supabase.storage.from_(BUCKET_NAME).upload(
            path=storage_path,
            file=f,
            file_options={
                "content-type": "application/octet-stream",
                "upsert": str(upsert).lower(),
            },
        )


def download_file(org_id: str, remote_path: str, local_path: str):
    """
    Downloads:
    org-data/org_123/processed/clean_df.parquet

    To:
    backend/data/org_123/processed/clean_df.parquet
    """
    supabase = get_supabase_client()

    storage_path = f"{org_id}/{remote_path}"
    data = supabase.storage.from_(BUCKET_NAME).download(storage_path)

    local_path_obj = Path(local_path)
    local_path_obj.parent.mkdir(parents=True, exist_ok=True)

    with open(local_path_obj, "wb") as f:
        f.write(data)

    return local_path
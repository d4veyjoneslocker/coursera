# backend/storage/local_cleanup.py

import shutil
from pathlib import Path

def delete_local_org_data(org_id: str):
    org_path = Path(f"backend/data/{org_id}")

    if org_path.exists():
        shutil.rmtree(org_path)
        print(f"🧹 Deleted local data for {org_id}")
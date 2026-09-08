import pandas as pd
import requests
from supabase import Client
from backend.data_pipeline.pipeline_helpers import get_source_file_paths
from backend.transforms.unfi_crisp import transform_unfi_natural_vendor_sales
from backend.supabase.storage import upload_file
from backend.supabase.credentials import get_source_credentials


def refresh_unfi_processed_data(org_id: str, supabase: Client):
    unfi_cred = get_source_credentials(
        supabase=supabase,
        org_id=org_id,
        source="unfi",
        required=True,
    )

    if not all(unfi_cred.values()):
        raise ValueError("Missing UNFI credentials for org_id={org_id}")

    paths = get_source_file_paths(org_id, "unfi")
    current_path = paths["processed_current"]
    previous_path = paths["processed_previous"]

    raw_unfi_df = pull_crisp_data(
        unfi_cred["account_id"],
        unfi_cred["connector_id"],
        unfi_cred["username"],
        unfi_cred["password"],
        table="Direct_Unfi_Insights_Natural_Vendor_Sales_Customer_Details_Weekly",
    )

    current_path.parent.mkdir(parents=True, exist_ok=True)

    raw_path = current_path.parent.parent / "raw" / "unfi" / "raw_master.parquet"
    raw_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        raw_unfi_df.to_parquet(raw_path, index=False)
        print("Raw UNFI parquet saved", raw_path)
    except Exception as e:
        print("RAW PARQUET ERROR:", repr(e))
        raise

    try:
        upload_file(
            local_path=str(raw_path),
            org_id=org_id,
            remote_path="raw/unfi/raw_master.parquet",
        )
        print("✅ UNFI raw uploaded to Supabase")
    except Exception as e:
        print("SUPABASE RAW UPLOAD ERROR:", repr(e))
        raise

    clean_unfi_df = transform_unfi_natural_vendor_sales(raw_unfi_df, org_id)

    if current_path.exists():
        if previous_path.exists():
            previous_path.unlink()
        current_path.replace(previous_path)

    try:
        clean_unfi_df.to_parquet(current_path, index=False)
        print("Parquet saved", current_path)
    except Exception as e:
        print("PARQUET ERROR:", repr(e))
        raise

    try:
        upload_file(
            local_path=str(current_path),
            org_id=org_id,
            remote_path="processed_sources/unfi_processed.parquet",
        )
        print("✅ UNFI processed uploaded to Supabase")
    except Exception as e:
        print("SUPABASE UPLOAD ERROR:", repr(e))
        raise

    return clean_unfi_df

def pull_crisp_data(account_id, connector_id, username, password, table=None):

    # Endpoint format: "https://api.gocrisp.com/odata/accounts/{account_id}/connector_configurations/{connector_id}/v1/feed.svc/"

    base_url = f"https://api.gocrisp.com/odata/accounts/{account_id}/connector_configurations/{connector_id}/v1/feed.svc"

    # Loop cycles through paginated results until there are no more pages (i.e., no @odata.nextLink, which is the URL for the next page of results)

    if table is None:

        url = base_url

        response = requests.get(
            url,
            auth=(username, password),
            headers={"Accept": "application/json"},
            timeout=30)
        
        response.raise_for_status()  # Check if the request was successful

        data = response.json()

        tables = [t["name"] for t in data["value"]]

        return tables
    
    else:    
        rows = []
        url = f"{base_url}/{table}?$top=1000"

        while url:
            response = requests.get(
                url,
                auth=(username, password),
                headers={"Accept": "application/json"},
                timeout=30
            )
            
            response.raise_for_status()  # Check if the request was successful 

            data = response.json()

            rows.extend(data.get("value", []))
            url = data.get("@odata.nextLink")
        df = pd.DataFrame(rows)

        return df
import os
import pandas as pd
import requests
from backend.data_pipeline.pipeline_helpers import get_source_file_paths
from backend.transforms.unfi import transform_unfi_natural_vendor_sales
from dotenv import load_dotenv

load_dotenv()



def get_unfi_env_credentials():
    return {
        "account_id": os.getenv("UNFI_ACCOUNT_ID"),
        "connector_id": os.getenv("UNFI_CONNECTOR_ID"),
        "username": os.getenv("UNFI_USERNAME"),
        "password": os.getenv("UNFI_PASSWORD"),
    }


def refresh_unfi_processed_data(org_id: str):
    unfi_cred = get_unfi_env_credentials()

    if not all(unfi_cred.values()):
        raise ValueError("Missing UNFI credentials in environment.")

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

    clean_unfi_df = transform_unfi_natural_vendor_sales(raw_unfi_df, org_id)

    current_path.parent.mkdir(parents=True, exist_ok=True)

    if current_path.exists():
        if previous_path.exists():
            previous_path.unlink()
        current_path.replace(previous_path)

    clean_unfi_df.to_parquet(current_path, index=False)

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
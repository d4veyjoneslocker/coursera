import os
import requests
import pandas as pd

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

 

    #df.to_csv("kehe_full_pod_vendor.csv", index=False)
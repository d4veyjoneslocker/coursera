from dataclasses import dataclass
from supabase import Client


@dataclass
class OrgCredentials:
    org_id: str
    provider: str | None
    source: str | None
    account_id: str | None
    connector_id: str | None
    username: str | None
    password: str | None

def _get_org_credentials_row(supabase: Client, org_id: str, source: str) -> OrgCredentials:
    response = (
        supabase
        .table("org_credentials")
        .select("org_id, provider, source, account_id, connector_id, username, password")
        .eq("org_id", org_id)
        .eq("source", source)
        .single()
        .execute()
    )

    row = response.data

    if not row:
        raise ValueError(f"No credentials found for org_id={org_id}, source={source}")

    return OrgCredentials(
        org_id=row["org_id"],
        provider=row.get("provider"),
        source=row.get("source"),
        account_id=row.get("account_id"),
        connector_id=row.get("connector_id"),
        username=row.get("username"),
        password=row.get("password"),
    )

def _resolve_vault_secrets(supabase: Client, creds: OrgCredentials) -> OrgCredentials:
    secret_names = [
        creds.account_id,
        creds.connector_id,
        creds.username,
        creds.password,
    ]

    secrets = (
        supabase
        .rpc("get_vault_secrets", {"secret_names": secret_names})
        .execute()
    ).data or []

    secret_map = {s["name"]: s["decrypted_secret"] for s in secrets}

    return OrgCredentials(
        org_id=creds.org_id,
        provider=creds.provider,
        source=creds.source,
        account_id=secret_map.get(creds.account_id),
        connector_id=secret_map.get(creds.connector_id),
        username=secret_map.get(creds.username),
        password=secret_map.get(creds.password),
    )

def get_source_credentials(
    supabase: Client,
    org_id: str,
    source: str,
    required: bool = True,
) -> dict[str, str] | None:
    try:
        creds = _get_org_credentials_row(supabase, org_id, source)
    except Exception:
        if required:
            raise
        return None

    creds = _resolve_vault_secrets(supabase, creds)

    is_complete = all([
        creds.account_id,
        creds.connector_id,
        creds.username,
        creds.password,
    ])

    if not is_complete:
        if required:
            raise ValueError(
                f"Incomplete credentials for org_id={org_id}, source={source}"
            )
        return None

    return {
        "account_id": creds.account_id,
        "connector_id": creds.connector_id,
        "username": creds.username,
        "password": creds.password,
    }
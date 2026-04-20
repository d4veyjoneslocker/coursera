from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from supabase import Client, create_client

from backend.generate_tables import save_base_tables


load_dotenv()


DATA_ROOT = Path("backend/data")
ALLOWED_CADENCES = {"daily", "weekly", "monthly"}


@dataclass
class OrgRecord:
    id: str
    name: str | None
    refresh_cadence: str | None


@dataclass
class OrgCredentials:
    org_id: str
    provider: str | None
    source: str | None
    account_id: str | None
    connector_id: str | None
    username: str | None
    password: str | None


def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        raise ValueError(
            "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in environment."
        )

    return create_client(url, key)


def get_orgs_for_cadence(supabase: Client, cadence: str) -> list[OrgRecord]:
    response = (
        supabase.table("organizations")
        .select("id, name, refresh_cadence")
        .eq("refresh_cadence", cadence)
        .execute()
    )

    rows = response.data or []

    return [
        OrgRecord(
            id=row["id"],
            name=row.get("name"),
            refresh_cadence=row.get("refresh_cadence"),
        )
        for row in rows
    ]


def get_org_credentials(supabase: Client, org_id: str) -> list[OrgCredentials]:
    response = (
        supabase.table("org_credentials")
        .select(
            "org_id, provider, source, account_id, connector_id, username, password"
        )
        .eq("org_id", org_id)
        .execute()
    )

    rows = response.data or []

    return [
        OrgCredentials(
            org_id=row["org_id"],
            provider=row.get("provider"),
            source=row.get("source"),
            account_id=row.get("account_id"),
            connector_id=row.get("connector_id"),
            username=row.get("username"),
            password=row.get("password"),
        )
        for row in rows
    ]


def ensure_org_output_dir(org_id: str) -> Path:
    output_dir = DATA_ROOT / org_id
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def write_refresh_metadata(
    output_dir: Path,
    org: OrgRecord,
    refreshed_at: datetime,
    row_counts: dict[str, int],
) -> None:
    meta = {
        "org_id": org.id,
        "org_name": org.name,
        "refresh_cadence": org.refresh_cadence,
        "refreshed_at_utc": refreshed_at.isoformat(),
        "row_counts": row_counts,
    }

    pd.Series(meta).to_json(output_dir / "refresh_metadata.json", indent=2)


def build_credential_dict(cred: OrgCredentials) -> dict[str, str]:
    if not cred.account_id or not cred.connector_id or not cred.username or not cred.password:
        raise ValueError(
            f"Missing required credential fields for org_id={cred.org_id}, source={cred.source}"
        )

    return {
        "account_id": cred.account_id,
        "connector_id": cred.connector_id,
        "username": cred.username,
        "password": cred.password,
    }


def get_row_counts_from_saved_tables(output_dir: Path) -> dict[str, int]:
    row_counts: dict[str, int] = {}

    for file_path in output_dir.glob("*.parquet"):
        df = pd.read_parquet(file_path)
        row_counts[file_path.stem] = len(df)

    return row_counts


def refresh_org(
    supabase: Client,
    org: OrgRecord,
) -> None:
    print(f"\nRefreshing org: {org.name or org.id} ({org.id})")

    credentials = get_org_credentials(supabase, org.id)
    if not credentials:
        raise ValueError(f"No credentials found for org_id={org.id}")

    kehe_cred = next((c for c in credentials if (c.source or "").lower() == "kehe"), None)
    unfi_cred = next((c for c in credentials if (c.source or "").lower() == "unfi"), None)

    if not kehe_cred and not unfi_cred:
        raise ValueError(f"Missing both KEHE and UNFI credentials for org_id={org.id}")

    output_dir = ensure_org_output_dir(org.id)

    save_base_tables(
        output_dir=str(output_dir),
        kehe_cred=build_credential_dict(kehe_cred) if kehe_cred else None,
        unfi_cred=build_credential_dict(unfi_cred) if unfi_cred else None,
    )

    refreshed_at = datetime.now(timezone.utc)
    row_counts = get_row_counts_from_saved_tables(output_dir)

    write_refresh_metadata(
        output_dir=output_dir,
        org=org,
        refreshed_at=refreshed_at,
        row_counts=row_counts,
    )

    (
        supabase.table("organizations")
        .update({"last_refreshed_at": refreshed_at.isoformat()})
        .eq("id", org.id)
        .execute()
    )

    print("  refresh complete")


def refresh_all_for_cadence(cadence: str) -> None:
    if cadence not in ALLOWED_CADENCES:
        raise ValueError(
            f"Invalid cadence '{cadence}'. Must be one of: {sorted(ALLOWED_CADENCES)}"
        )

    supabase = get_supabase_client()
    orgs = get_orgs_for_cadence(supabase, cadence)

    if not orgs:
        print(f"No orgs found for cadence='{cadence}'")
        return

    print(f"Found {len(orgs)} org(s) for cadence='{cadence}'")

    failures: list[tuple[str, str]] = []

    for org in orgs:
        try:
            refresh_org(supabase, org)
        except Exception as exc:
            failures.append((org.id, str(exc)))
            print(f"  FAILED for org {org.id}: {exc}")

    print("\nDone.")
    print(f"Successful: {len(orgs) - len(failures)}")
    print(f"Failed: {len(failures)}")

    if failures:
        print("\nFailure summary:")
        for org_id, message in failures:
            print(f"- {org_id}: {message}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh cached base tables by cadence.")
    parser.add_argument(
        "--cadence",
        required=True,
        choices=sorted(ALLOWED_CADENCES),
        help="Refresh cadence tier to process.",
    )
    args = parser.parse_args()

    refresh_all_for_cadence(args.cadence)


if __name__ == "__main__":
    main()
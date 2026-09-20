from __future__ import annotations

import argparse
import os
import requests
import pandas as pd
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from supabase import Client, create_client
from backend.data_pipeline.generate_tables import save_base_tables
from backend.supabase.storage import get_supabase_client


load_dotenv()

DATA_ROOT = Path("backend/data")
ALLOWED_CADENCES = {"daily", "weekly", "monthly"}


@dataclass
class OrgRecord:
    id: str
    name: str | None
    refresh_cadence: str | None


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

    output_dir = ensure_org_output_dir(org.id)

    save_base_tables(
        output_dir=str(output_dir),
        org_id=org.id,
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

    if len(orgs) - len(failures) > 0:
        notify_api_to_reload_cache(org_id)

    if failures:
        print("\nFailure summary:")
        for org_id, message in failures:
            print(f"- {org_id}: {message}")


def notify_api_to_reload_cache(org_id: str):
    api_url = os.getenv("API_BASE_URL")
    secret = os.getenv("ADMIN_REFRESH_SECRET")

    if not api_url or not secret:
        print("Skipping cache reload: missing API_BASE_URL or ADMIN_REFRESH_SECRET")
        return

    try:
        response = requests.post(
            f"{api_url}/admin/reload-cache",
            headers={"x-refresh-secret": secret},
            params={"org_id": org_id},
            timeout=60,
        )
        response.raise_for_status()
        print(f"API cache reloaded for {org_id}")
    except Exception as e:
        print(f"Failed to reload API cache for {org_id}: {e}")


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
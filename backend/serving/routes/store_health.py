from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, Query

from backend.data_pipeline.table_loader import load_org_tables, load_active_pods
from backend.filters.filter_table import filter_table
from backend.filters.filters import get_filters, generate_filter_api
from backend.metrics.metric_tables import store_performance, status_counts_dict
from backend.serving.api_helpers import clean_for_json


router = APIRouter(prefix="/store_health", tags=["Store Health"])


BASE_DATA_DIR = Path("backend/data")


# =============================================================================
# HELPERS
# =============================================================================


def _add_store_coordinates(
    stores: pd.DataFrame,
    coordinates_path: Path,
) -> pd.DataFrame:
    """
    Add store latitude / longitude from the existing store coordinate map.

    Coordinates are display metadata, not store-performance metrics, so they
    are joined at the API layer rather than calculated in store_performance().
    """

    if not coordinates_path.exists():
        stores = stores.copy()
        stores["latitude"] = None
        stores["longitude"] = None
        return stores

    coordinates = pd.read_csv(coordinates_path)

    coordinates = (
        coordinates[
            [
                "coded_customer",
                "latitude",
                "longitude",
            ]
        ]
        .drop_duplicates(
            subset=["coded_customer"]
        )
    )

    return stores.merge(
        coordinates,
        on="coded_customer",
        how="left",
    )


# =============================================================================
# FILTERS
# =============================================================================


@router.get("/filters")
def get_filter_options(
    column_name: str,
    org_id: str = Query(...),
    chain: list[str] | None = Query(None),
    distributor: list[str] | None = Query(None),
    dc: list[str] | None = Query(None),
    channel: list[str] | None = Query(None),
    state: list[str] | None = Query(None),
    status: list[str] | None = Query(None),
):
    filters = {
        "chain": chain,
        "distributor": distributor,
        "dc": dc,
        "channel": channel,
        "state": state,
        "status": status,
    }

    features_df = load_org_tables(org_id)

    filters.pop(column_name, None)

    df = filter_table(
        features_df,
        **filters,
    )

    return generate_filter_api(
        df,
        column_name,
    )


# =============================================================================
# STATUS
# =============================================================================


@router.get("/status")
def status(
    org_id: str = Query(...),
    filters: dict = Depends(get_filters),
):
    features_df = load_org_tables(org_id)

    df = filter_table(
        features_df,
        **filters,
    )

    return status_counts_dict(df)


# =============================================================================
# STORE PERFORMANCE
# =============================================================================


@router.get("/store_performance")
def store_performance_table(
    org_id: str = Query(...),
    filters: dict = Depends(get_filters),
):
    features_df = load_org_tables(org_id)
    active_pods_df = load_active_pods(org_id)

    df = filter_table(
        features_df,
        **filters,
    )

    active_pods_df = filter_table(
        active_pods_df,
        **filters,
    )

    result = store_performance(
        df=df,
        active_pods_df=active_pods_df,
    )

    coordinates_path = (
        BASE_DATA_DIR
        / org_id
        / "maps"
        / "store_coordinates.csv"
    )

    result = _add_store_coordinates(
        stores=result,
        coordinates_path=coordinates_path,
    )

    result = clean_for_json(result)

    return result.to_dict(orient="records")
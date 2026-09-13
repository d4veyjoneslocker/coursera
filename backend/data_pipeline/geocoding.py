
import time
import os
import certifi

from pathlib import Path
import pandas as pd
from geopy.geocoders import Nominatim

os.environ["SSL_CERT_FILE"] = certifi.where()

BASE_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def get_store_coordinates_path(org_id: str) -> Path:
    return BASE_DATA_DIR / org_id / "maps" / "store_coordinates.csv"


def get_features_path(org_id: str) -> Path:
    return BASE_DATA_DIR / org_id / "processed" / "features_df.parquet"


def get_unique_store_addresses(features_df: pd.DataFrame) -> pd.DataFrame:
    required_columns = [
        "coded_customer",
        "street_address",
        "city",
        "state",
        "zip",
    ]

    missing = [
        column
        for column in required_columns
        if column not in features_df.columns
    ]

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    stores = features_df[required_columns].copy()

    for column in ["street_address", "city", "state", "zip"]:
        stores[column] = stores[column].astype("string").str.strip()

    stores = stores[
        stores["street_address"].notna()
        & stores["street_address"].ne("")
        & stores["city"].notna()
        & stores["city"].ne("")
        & stores["state"].notna()
        & stores["state"].ne("")
        & stores["zip"].notna()
        & stores["zip"].ne("")
    ].copy()

    stores["geocode_address"] = (
        stores["street_address"]
        + ", "
        + stores["city"]
        + ", "
        + stores["state"]
        + " "
        + stores["zip"]
    )

    stores = (
        stores
        .drop_duplicates("coded_customer")
        .reset_index(drop=True)
    )

    return stores


def load_existing_coordinates(output_path: Path) -> pd.DataFrame:
    if not output_path.exists():
        return pd.DataFrame(
            columns=[
                "coded_customer",
                "street_address",
                "city",
                "state",
                "zip",
                "geocode_address",
                "latitude",
                "longitude",
            ]
        )

    return pd.read_csv(output_path, dtype={"zip": "string"})


def geocode_stores(org_id: str) -> pd.DataFrame:
    features_path = get_features_path(org_id)
    output_path = get_store_coordinates_path(org_id)

    if not features_path.exists():
        raise FileNotFoundError(f"features_df not found: {features_path}")

    features_df = pd.read_parquet(features_path)
    stores = get_unique_store_addresses(features_df)
    existing = load_existing_coordinates(output_path)

    existing_lookup = set(
        zip(
            existing["coded_customer"].astype(str),
            existing["geocode_address"].astype(str),
        )
    )

    stores["needs_geocoding"] = stores.apply(
        lambda row: (
            str(row["coded_customer"]),
            str(row["geocode_address"]),
        ) not in existing_lookup,
        axis=1,
    )

    stores_to_geocode = stores[stores["needs_geocoding"]].copy()

    print(f"Unique stores: {len(stores)}")
    print(f"Already geocoded: {len(stores) - len(stores_to_geocode)}")
    print(f"Need geocoding: {len(stores_to_geocode)}")

    if stores_to_geocode.empty:
        print("Nothing new to geocode.")
        return existing

    geolocator = Nominatim(user_agent="skuba-store-geocoder")

    new_rows = []

    for _, row in stores_to_geocode.iterrows():
        address = row["geocode_address"]

        print(f"Geocoding: {address}")

        try:
            location = geolocator.geocode(
                address,
                timeout=10,
                country_codes="us",
            )

            latitude = location.latitude if location else None
            longitude = location.longitude if location else None

            if location:
                print(f"  Found: {latitude}, {longitude}")
            else:
                print("  No match found.")

        except Exception as exc:
            print(f"  Failed: {exc}")

            latitude = None
            longitude = None

        new_rows.append(
            {
                "coded_customer": row["coded_customer"],
                "street_address": row["street_address"],
                "city": row["city"],
                "state": row["state"],
                "zip": row["zip"],
                "geocode_address": address,
                "latitude": latitude,
                "longitude": longitude,
            }
        )

        # Nominatim's public service should not be hammered
        # with rapid requests.
        time.sleep(1)

    new_coordinates = pd.DataFrame(new_rows)

    combined = pd.concat(
        [
            existing,
            new_coordinates,
        ],
        ignore_index=True,
    )

    combined = (
        combined
        .drop_duplicates(
            [
                "coded_customer",
                "geocode_address",
            ],
            keep="last",
        )
        .reset_index(drop=True)
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    combined.to_csv(
        output_path,
        index=False,
    )

    print(f"Saved {len(combined)} store coordinates to {output_path}")

    return combined


if __name__ == "__main__":
    geocode_stores("default_org")
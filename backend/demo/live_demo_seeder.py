from __future__ import annotations
import argparse
import hashlib
import hmac
import os
import re
import shutil
import tempfile
from pathlib import Path
import pandas as pd
from backend.supabase.storage import download_file, upload_file

# ---------------------------------------------------------------------
# Files to copy from the source org into the demo org.
#
# Add/remove paths here as SKUba evolves.
# ---------------------------------------------------------------------

SUPABASE_FILES = [
    "processed/features_df.parquet",
    "processed/active_pods_df.parquet",
    "processed/fill_rate_df.parquet",
    "processed_sources/kehe_processed.parquet",
    "processed_sources/unfi_processed.parquet",
    "maps/sku_name_map.csv",
    "maps/store_coordinates.csv",
]

LOCAL_INVENTORY_FILES = [
    "inventory_features_test.csv",
    "inventory_combined.parquet",
    "raw/inventory/unfi/Purchase Orders.csv",
    "raw/inventory/unfi/Projected Orders Detail.csv",
    "raw/inventory/kehe/Order Projections Report.csv",
]

LOCAL_DATA_ROOT = Path("backend/data").resolve()

# ---------------------------------------------------------------------
# Column groups
# ---------------------------------------------------------------------

ORG_ID_COLUMNS = {
    "org_id",
    "organization_id",
}

SKU_COLUMNS = {
    "sku",
    "sku_name",
    "raw_sku",
    "clean_sku",
    "product_name",
    "product_description",
    "productdescription",
    "product",
    "item_description",
}

CHAIN_COLUMNS = {
    "chain",
    "retailer",
    "retailer_name",
    "chain_name",
}

STORE_NAME_COLUMNS = {
    "customer_name",
    "store_name",
    "location_name",
}

# DC identifiers are intentionally preserved so inventory, PO, and projected-order
# mappings continue to match SKUba's existing DC logic.
DC_COLUMNS = {
    "dc",
    "dc_name",
    "distribution_center",
    "distribution_center_name",
    "dc_code",
}

STORE_ID_COLUMNS = {
    "chain_store_key",
    "store_id",
    "customer_id",
    "customer_number",
    "account_id",
    "account_number",
}

PRODUCT_ID_COLUMNS = {
    "upc",
    "normalized_upc",
    "sku_id",
    "product_id",
    "product_code",
}

ADDRESS_COLUMNS = {
    "address",
    "address1",
    "address_1",
    "street_address",
    "street",
}

BRAND_COLUMNS = {
    "brand",
    "brand_name",
}

PERSON_COLUMNS = {
    "po_buyer_name",
}

PO_ID_COLUMNS = {
    "po_number",
}

CODED_CUSTOMER_COLUMNS = {
    "coded_customer",
}

# I would generally KEEP city/state for demo usefulness unless you decide
# the client's geographic footprint itself is sensitive.
LOCATION_COLUMNS_TO_KEEP = {
    "city",
    "state",
    "zip",
    "zipcode",
    "postal_code",
    "latitude",
    "longitude",
    "lat",
    "lon",
    "lng",
}

# ---------------------------------------------------------------------
# Deterministic masking
# ---------------------------------------------------------------------

CHAIN_FIRST = [
    "Green",
    "Harvest",
    "Fresh",
    "Golden",
    "Sunrise",
    "Evergreen",
    "River",
    "Maple",
    "Cedar",
    "Oak",
    "Meadow",
    "Blue",
    "Silver",
    "Bright",
    "Coastal",
    "Valley",
    "Summit",
    "Pine",
    "Willow",
    "Stone",
]

CHAIN_SECOND = [
    "Market",
    "Grocer",
    "Foods",
    "Provisions",
    "Marketplace",
    "Fresh Market",
    "Food Co.",
    "Natural Foods",
    "Grocery",
    "Markets",
]

SKU_FIRST = [
    "Classic",
    "Original",
    "Bright",
    "Smooth",
    "Bold",
    "Golden",
    "Fresh",
    "Pure",
    "Daily",
    "Signature",
    "Light",
    "Rich",
]

SKU_SECOND = [
    "Vanilla",
    "Mocha",
    "Cocoa",
    "Caramel",
    "Berry",
    "Coconut",
    "Cinnamon",
    "Maple",
    "Coffee",
    "Cream",
    "Honey",
    "Almond",
]

DC_FIRST = [
    "North",
    "South",
    "East",
    "West",
    "Central",
    "Coastal",
    "Metro",
    "Regional",
]


def _normalize(value) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).strip()).upper()


def _digest(secret: str, namespace: str, value) -> bytes:
    normalized = _normalize(value)
    payload = f"{namespace}|{normalized}".encode("utf-8")
    return hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).digest()


def _int_from_digest(secret: str, namespace: str, value) -> int:
    return int.from_bytes(_digest(secret, namespace, value)[:8], "big")


def fake_chain(value, secret: str) -> str:
    """
    Deterministically turn any real retailer/chain into a believable fake chain.

    Same source chain -> same fake chain across every dataframe and every run,
    as long as DEMO_MASKING_SECRET stays the same.
    """
    if pd.isna(value) or str(value).strip() == "":
        return value

    n = _int_from_digest(secret, "chain", value)
    first = CHAIN_FIRST[n % len(CHAIN_FIRST)]
    second = CHAIN_SECOND[(n // len(CHAIN_FIRST)) % len(CHAIN_SECOND)]

    suffix_num = (
        n // (len(CHAIN_FIRST) * len(CHAIN_SECOND))
    ) % 997

    if suffix_num % 4:
        return f"{first} {second}"

    return f"{first} {second} {suffix_num:02d}"


def fake_sku(value, secret: str) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return value

    normalized = _normalize(value)

    if "VANILLA BEAN" in normalized or "VNLLA BN" in normalized:
        return "BERRY"

    if "PEANUT BUTTER" in normalized or "PNT BTTR" in normalized:
        return "CARAMEL"

    if "MOCHA JOE" in normalized or "MOCHA JO" in normalized:
        return "MOCHA"

    if "STRAWBERRY" in normalized or "STRWBRY" in normalized:
        return "COCONUT"

    n = _int_from_digest(secret, "sku", value)
    first = SKU_FIRST[n % len(SKU_FIRST)]
    second = SKU_SECOND[
        (n // len(SKU_FIRST)) % len(SKU_SECOND)
    ]

    return f"{first} {second}".upper()


def fake_dc(value, secret: str) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return value

    n = _int_from_digest(secret, "dc", value)
    prefix = DC_FIRST[n % len(DC_FIRST)]
    num = 100 + ((n // len(DC_FIRST)) % 900)

    return f"{prefix} DC {num}"


def fake_identifier(value, secret: str, namespace: str) -> str:
    """
    Deterministic opaque ID for join keys/customer IDs/etc.
    """
    if pd.isna(value) or str(value).strip() == "":
        return value

    token = hmac.new(
        secret.encode("utf-8"),
        f"{namespace}|{_normalize(value)}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:16]

    return f"demo_{token}"


def fake_upc(value, secret: str) -> str:
    """
    Produce a deterministic 12-digit UPC-looking value.

    This is for demo display only; it is not intended to be a valid GS1 identity.
    """
    if pd.isna(value) or str(value).strip() == "":
        return value

    n = _int_from_digest(secret, "upc", value)
    return f"{n % 1_000_000_000_000:012d}"


def fake_store_name(
    value,
    secret: str,
    row_index,
    chain_value=None,
) -> str:
    """
    Store names become:
        Green Market #1842

    When chain_value is available, the fake store inherits the fake chain name.
    """
    if pd.isna(value) or str(value).strip() == "":
        return value

    n = _int_from_digest(secret, "store_name", value)
    store_num = 100 + (n % 9900)

    if chain_value is not None and not pd.isna(chain_value):
        chain = fake_chain(chain_value, secret)
        return f"{chain} #{store_num}"

    return f"Demo Store #{store_num}"


def fake_brand(value, secret: str) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return value

    return "Demo Brand"


def fake_person(value, secret: str) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return value

    n = _int_from_digest(secret, "person", value)

    first_names = [
        "Alex",
        "Jordan",
        "Taylor",
        "Morgan",
        "Casey",
        "Riley",
    ]

    last_names = [
        "Lee",
        "Parker",
        "Reed",
        "Morgan",
        "Hayes",
        "Stone",
    ]

    return (
        f"{first_names[n % len(first_names)]} "
        f"{last_names[(n // len(first_names)) % len(last_names)]}"
    )


def fake_po_number(value, secret: str) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return value

    n = _int_from_digest(secret, "po_number", value)
    return f"DEMO-PO-{n % 10_000_000:07d}"


def fake_coded_customer(
    value,
    secret: str,
    chain_value=None,
) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return value

    n = _int_from_digest(
        secret,
        "coded_customer",
        value,
    )

    store_num = 100 + (n % 9900)

    if chain_value is not None and not pd.isna(chain_value):
        chain = fake_chain(
            chain_value,
            secret,
        )

        return f"{chain} #{store_num}"

    return f"Demo Store #{store_num}"


def build_coded_customer_map(
    features_df: pd.DataFrame,
    secret: str,
) -> dict:
    """
    Build the canonical original -> masked coded_customer mapping from
    source features_df before any masking happens.

    Every other file reuses this map so coded_customer stays readable
    and remains identical across features, coordinates, and other tables.
    """
    if "coded_customer" not in features_df.columns:
        return {}

    chain_col = None

    for candidate in CHAIN_COLUMNS:
        if candidate in features_df.columns:
            chain_col = candidate
            break

    mapping = {}

    for _, row in features_df.iterrows():
        original = row.get("coded_customer")

        if pd.isna(original) or str(original).strip() == "":
            continue

        key = _normalize(original)

        if key in mapping:
            continue

        chain_value = (
            row.get(chain_col)
            if chain_col is not None
            else None
        )

        mapping[key] = fake_coded_customer(
            original,
            secret,
            chain_value=chain_value,
        )

    return mapping


def fake_address(value, secret: str) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return value

    n = _int_from_digest(secret, "address", value)
    number = 100 + (n % 9800)

    streets = [
        "Market St",
        "Main St",
        "Oak Ave",
        "Pine St",
        "Sunset Blvd",
        "Commerce Dr",
        "Central Ave",
        "Park Rd",
        "Broadway",
        "Lakeview Dr",
    ]

    street = streets[(n // 10000) % len(streets)]

    return f"{number} {street}"


# ---------------------------------------------------------------------
# DataFrame masking
# ---------------------------------------------------------------------

def mask_dataframe(
    df: pd.DataFrame,
    demo_org_id: str,
    secret: str,
    file_name: str,
    coded_customer_map: dict | None = None,
) -> pd.DataFrame:
    df = df.copy()
    original_columns = list(df.columns)

    def normalize_column_name(name) -> str:
        return re.sub(
            r"[^a-z0-9]+",
            "_",
            str(name).strip().lower(),
        ).strip("_")

    normalized_to_original = {
        normalize_column_name(c): c
        for c in df.columns
    }

    chain_source_col = None

    for candidate in CHAIN_COLUMNS:
        if candidate in normalized_to_original:
            chain_source_col = normalized_to_original[candidate]
            break

    original_chain = (
        df[chain_source_col].copy()
        if chain_source_col is not None
        else None
    )

    is_sku_map = (
        file_name == "maps/sku_name_map.csv"
        and "raw_sku" in normalized_to_original
        and "clean_sku" in normalized_to_original
    )

    if is_sku_map:
        raw_col = normalized_to_original["raw_sku"]
        clean_col = normalized_to_original["clean_sku"]

        original_raw = df[raw_col].copy()
        original_clean = df[clean_col].copy()

        df[raw_col] = original_raw.map(
            lambda x: fake_sku(x, secret)
        )

        df[clean_col] = original_clean.map(
            lambda x: fake_sku(x, secret)
        )

    for lower_name, col in normalized_to_original.items():
        if lower_name in ORG_ID_COLUMNS:
            df[col] = demo_org_id

        elif lower_name in SKU_COLUMNS:
            if (
                is_sku_map
                and lower_name in {"raw_sku", "clean_sku"}
            ):
                continue

            df[col] = df[col].map(
                lambda x: fake_sku(x, secret)
            )

        elif lower_name in CHAIN_COLUMNS:
            df[col] = df[col].map(
                lambda x: fake_chain(x, secret)
            )

        elif lower_name in CODED_CUSTOMER_COLUMNS:
            df[col] = [
                (
                    coded_customer_map.get(
                        _normalize(value),
                        fake_coded_customer(
                            value,
                            secret,
                            chain_value=(
                                original_chain.iloc[idx]
                                if original_chain is not None
                                else None
                            ),
                        ),
                    )
                    if (
                        coded_customer_map
                        and not pd.isna(value)
                        and str(value).strip() != ""
                    )
                    else fake_coded_customer(
                        value,
                        secret,
                        chain_value=(
                            original_chain.iloc[idx]
                            if original_chain is not None
                            else None
                        ),
                    )
                )
                for idx, value in enumerate(df[col])
            ]

        elif lower_name in BRAND_COLUMNS:
            df[col] = df[col].map(
                lambda x: fake_brand(x, secret)
            )

        elif lower_name in PERSON_COLUMNS:
            df[col] = df[col].map(
                lambda x: fake_person(x, secret)
            )

        elif lower_name in PO_ID_COLUMNS:
            df[col] = df[col].map(
                lambda x: fake_po_number(x, secret)
            )

        elif lower_name in STORE_NAME_COLUMNS:
            if original_chain is not None:
                df[col] = [
                    fake_store_name(
                        value,
                        secret,
                        idx,
                        chain_value=chain_value,
                    )
                    for idx, (
                        value,
                        chain_value,
                    ) in enumerate(
                        zip(
                            df[col],
                            original_chain,
                        )
                    )
                ]

            else:
                df[col] = [
                    fake_store_name(
                        value,
                        secret,
                        idx,
                    )
                    for idx, value in enumerate(df[col])
                ]

        elif lower_name in STORE_ID_COLUMNS:
            df[col] = df[col].map(
                lambda x: fake_identifier(
                    x,
                    secret,
                    namespace=lower_name,
                )
            )

        elif lower_name in PRODUCT_ID_COLUMNS:
            if "upc" in lower_name:
                df[col] = df[col].map(
                    lambda x: fake_upc(x, secret)
                )

            else:
                df[col] = df[col].map(
                    lambda x: fake_identifier(
                        x,
                        secret,
                        namespace=lower_name,
                    )
                )

        elif lower_name in ADDRESS_COLUMNS:
            df[col] = df[col].map(
                lambda x: fake_address(x, secret)
            )

    print(f"\n[{file_name}]")
    print(f"rows: {len(df):,}")
    print(f"columns: {len(df.columns)}")

    changed = []

    for col in original_columns:
        lower = re.sub(
            r"[^a-z0-9]+",
            "_",
            str(col).strip().lower(),
        ).strip("_")

        if (
            lower in ORG_ID_COLUMNS
            or lower in SKU_COLUMNS
            or lower in CHAIN_COLUMNS
            or lower in STORE_NAME_COLUMNS
            or lower in STORE_ID_COLUMNS
            or lower in PRODUCT_ID_COLUMNS
            or lower in ADDRESS_COLUMNS
            or lower in BRAND_COLUMNS
            or lower in PERSON_COLUMNS
            or lower in PO_ID_COLUMNS
            or lower in CODED_CUSTOMER_COLUMNS
        ):
            changed.append(col)

    print(
        "masked:",
        ", ".join(map(str, changed)) or "none",
    )

    return df


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------

def validate_masked(
    original: pd.DataFrame,
    masked: pd.DataFrame,
    demo_org_id: str,
    file_name: str,
):
    if len(original) != len(masked):
        raise ValueError(
            f"{file_name}: row count changed "
            f"({len(original)} -> {len(masked)})"
        )

    if list(original.columns) != list(masked.columns):
        raise ValueError(
            f"{file_name}: columns changed"
        )

    original_numeric = original.select_dtypes(
        include="number"
    )

    masked_numeric = masked.select_dtypes(
        include="number"
    )

    shared_numeric = [
        col
        for col in original_numeric.columns
        if col in masked_numeric.columns
        and str(col).lower() not in PRODUCT_ID_COLUMNS
        and str(col).lower() not in STORE_ID_COLUMNS
    ]

    for col in shared_numeric:
        if not original_numeric[col].equals(
            masked_numeric[col]
        ):
            raise ValueError(
                f"{file_name}: numeric metric changed unexpectedly: "
                f"{col}"
            )

    for col in masked.columns:
        if str(col).lower() in ORG_ID_COLUMNS:
            non_null_values = set(
                masked[col]
                .dropna()
                .astype(str)
                .unique()
            )

            if (
                non_null_values
                and non_null_values != {str(demo_org_id)}
            ):
                raise ValueError(
                    f"{file_name}: "
                    f"{col} contains non-demo org IDs"
                )


def scan_for_source_values(
    original: pd.DataFrame,
    masked: pd.DataFrame,
    file_name: str,
):
    """
    Basic leak check for the fields we intentionally mask.
    """

    def normalize_column_name(name) -> str:
        return re.sub(
            r"[^a-z0-9]+",
            "_",
            str(name).strip().lower(),
        ).strip("_")

    normalized_to_original = {
        normalize_column_name(c): c
        for c in original.columns
    }

    sensitive_groups = (
        SKU_COLUMNS
        | CHAIN_COLUMNS
        | STORE_NAME_COLUMNS
        | STORE_ID_COLUMNS
        | PRODUCT_ID_COLUMNS
        | ADDRESS_COLUMNS
        | BRAND_COLUMNS
        | PERSON_COLUMNS
        | PO_ID_COLUMNS
        | CODED_CUSTOMER_COLUMNS
    )

    leaks = []

    for lower_name in sensitive_groups:
        if lower_name not in normalized_to_original:
            continue

        col = normalized_to_original[lower_name]

        original_values = {
            str(x)
            for x in original[col].dropna().unique()
            if str(x).strip()
        }

        masked_values = {
            str(x)
            for x in masked[col].dropna().unique()
            if str(x).strip()
        }

        overlap = original_values & masked_values

        if overlap:
            examples = sorted(overlap)[:5]

            leaks.append(
                (
                    col,
                    examples,
                )
            )

    if leaks:
        details = "\n".join(
            f"  {col}: {examples}"
            for col, examples in leaks
        )

        raise ValueError(
            f"{file_name}: possible unmasked values detected:\n"
            f"{details}"
        )


# ---------------------------------------------------------------------
# File IO
# ---------------------------------------------------------------------

def read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()

    if suffix == ".parquet":
        return pd.read_parquet(path)

    if suffix == ".csv":
        return pd.read_csv(path)

    raise ValueError(
        f"Unsupported file type: {path}"
    )


def write_table(
    df: pd.DataFrame,
    path: Path,
):
    suffix = path.suffix.lower()

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if suffix == ".parquet":
        df.to_parquet(
            path,
            index=False,
        )
        return

    if suffix == ".csv":
        df.to_csv(
            path,
            index=False,
        )
        return

    raise ValueError(
        f"Unsupported file type: {path}"
    )


def download_org_file(
    org_id: str,
    remote_path: str,
    local_path: Path,
):
    local_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    download_file(
        org_id=org_id,
        remote_path=remote_path,
        local_path=str(local_path),
    )


def upload_org_file(
    org_id: str,
    remote_path: str,
    local_path: Path,
):
    """
    Assumes backend.supabase.storage.upload_file mirrors download_file:

        upload_file(
            org_id=...,
            remote_path=...,
            local_path=...,
        )

    If your existing helper uses a slightly different signature,
    this is the only function you need to adjust.
    """
    upload_file(
        org_id=org_id,
        remote_path=remote_path,
        local_path=str(local_path),
    )


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def create_demo_data(
    source_org_id: str,
    demo_org_id: str,
    apply: bool,
):
    if source_org_id == demo_org_id:
        raise ValueError(
            "source_org_id and demo_org_id MUST be different"
        )

    secret = os.environ.get(
        "DEMO_MASKING_SECRET"
    )

    if not secret:
        raise RuntimeError(
            "Set DEMO_MASKING_SECRET before running this script.\n"
            "Example:\n"
            'export DEMO_MASKING_SECRET="some-long-random-string"'
        )

    work_root = Path(
        tempfile.mkdtemp(
            prefix="skuba_demo_mask_"
        )
    ).resolve()

    source_root = work_root / "source"
    demo_root = work_root / "demo"

    print("=" * 70)
    print("SKUba demo data generator")
    print("=" * 70)
    print("source org:", source_org_id)
    print("demo org:  ", demo_org_id)

    print(
        "mode:      ",
        "APPLY" if apply else "DRY RUN",
    )

    print("workspace: ", work_root)
    print()

    try:
        processed_files = []
        coded_customer_map = {}

        # Supabase-backed files
        for remote_path in SUPABASE_FILES:
            print(
                f"\nDownloading {remote_path}..."
            )

            source_path = (
                source_root / remote_path
            )

            demo_path = (
                demo_root / remote_path
            )

            try:
                download_org_file(
                    org_id=source_org_id,
                    remote_path=remote_path,
                    local_path=source_path,
                )

            except Exception as exc:
                print(
                    f"SKIP {remote_path}: {exc}"
                )
                continue

            original = read_table(
                source_path
            )

            if remote_path == "processed/features_df.parquet":
                coded_customer_map = build_coded_customer_map(
                    features_df=original,
                    secret=secret,
                )

                print(
                    f"canonical coded_customer mappings: "
                    f"{len(coded_customer_map):,}"
                )

            masked = mask_dataframe(
                df=original,
                demo_org_id=demo_org_id,
                secret=secret,
                file_name=remote_path,
                coded_customer_map=coded_customer_map,
            )

            validate_masked(
                original=original,
                masked=masked,
                demo_org_id=demo_org_id,
                file_name=remote_path,
            )

            scan_for_source_values(
                original=original,
                masked=masked,
                file_name=remote_path,
            )

            write_table(
                masked,
                demo_path,
            )

            local_demo_path = (
                LOCAL_DATA_ROOT
                / demo_org_id
                / remote_path
            ).resolve()

            if not str(
                local_demo_path
            ).startswith(
                str(LOCAL_DATA_ROOT)
            ):
                raise ValueError(
                    "Invalid local demo path"
                )

            write_table(
                masked,
                local_demo_path,
            )

            print(
                f"saved locally: {local_demo_path}"
            )

            processed_files.append(
                (
                    "supabase",
                    remote_path,
                    source_path,
                    demo_path,
                )
            )

        # Railway/local inventory files
        source_org_root = (
            LOCAL_DATA_ROOT
            / source_org_id
        ).resolve()

        demo_org_root = (
            LOCAL_DATA_ROOT
            / demo_org_id
        ).resolve()

        if not str(
            source_org_root
        ).startswith(
            str(LOCAL_DATA_ROOT)
        ):
            raise ValueError(
                "Invalid source org path"
            )

        if not str(
            demo_org_root
        ).startswith(
            str(LOCAL_DATA_ROOT)
        ):
            raise ValueError(
                "Invalid demo org path"
            )

        for relative_path in LOCAL_INVENTORY_FILES:
            source_path = (
                source_org_root
                / relative_path
            )

            demo_path = (
                demo_org_root
                / relative_path
            )

            print(
                f"\nLoading local inventory file "
                f"{relative_path}..."
            )

            if not source_path.exists():
                print(
                    f"SKIP {relative_path}: "
                    f"local file not found at "
                    f"{source_path}"
                )
                continue

            original = read_table(
                source_path
            )

            masked = mask_dataframe(
                df=original,
                demo_org_id=demo_org_id,
                secret=secret,
                file_name=relative_path,
                coded_customer_map=coded_customer_map,
            )

            validate_masked(
                original=original,
                masked=masked,
                demo_org_id=demo_org_id,
                file_name=relative_path,
            )

            scan_for_source_values(
                original=original,
                masked=masked,
                file_name=relative_path,
            )

            write_table(
                masked,
                demo_path,
            )

            print(
                f"saved locally: {demo_path}"
            )

            processed_files.append(
                (
                    "local",
                    relative_path,
                    source_path,
                    demo_path,
                )
            )

        print(
            "\n" + "=" * 70
        )

        print(
            f"Validated {len(processed_files)} files."
        )

        print("=" * 70)

        if not apply:
            print(
                "\nDRY RUN COMPLETE.\n"
                "Nothing was uploaded to Supabase.\n"
                f"All masked demo files were saved under: "
                f"{LOCAL_DATA_ROOT / demo_org_id}\n\n"
                "Inspect that demo-org folder, then rerun with --apply "
                "when you want to upload the Supabase-backed files."
            )
            return

        print(
            "\nWriting masked files to demo org...\n"
        )

        for (
            storage_type,
            relative_path,
            _,
            demo_path,
        ) in processed_files:

            if storage_type == "supabase":
                print(
                    f"Uploading {relative_path}..."
                )

                upload_org_file(
                    org_id=demo_org_id,
                    remote_path=relative_path,
                    local_path=demo_path,
                )

            elif storage_type == "local":
                print(
                    f"Local inventory file already saved: "
                    f"{LOCAL_DATA_ROOT / demo_org_id / relative_path}"
                )

        print("\nDONE.")

        print(
            "Masked Supabase + local inventory data "
            f"was written only to demo org {demo_org_id}."
        )

    finally:
        shutil.rmtree(
            work_root,
            ignore_errors=True,
        )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Create a masked SKUba demo org "
            "from an existing org."
        )
    )

    parser.add_argument(
        "--source-org",
        required=True,
        help="Real/source organization UUID",
    )

    parser.add_argument(
        "--demo-org",
        required=True,
        help="Destination demo organization UUID",
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Upload Supabase-backed masked files to the demo org. "
            "Without this flag the script only validates."
        ),
    )

    args = parser.parse_args()

    create_demo_data(
        source_org_id=args.source_org,
        demo_org_id=args.demo_org,
        apply=args.apply,
    )


if __name__ == "__main__":
    main()
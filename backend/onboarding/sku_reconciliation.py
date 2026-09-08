from pathlib import Path

import pandas as pd

from backend.supabase.storage import download_file, upload_file


def get_reconciliation_products(org_id: str) -> list[dict]:
    """
    Return the distinct raw products across distributors
    that need SKU reconciliation.
    """

    products = []

    # =====================================================
    # KeHE
    # =====================================================

    kehe_path = Path(
        f"backend/data/{org_id}/raw/kehe/raw_master.csv"
    )

    print(f"KeHE local path exists: {kehe_path.exists()} — {kehe_path}")

    if not kehe_path.exists():
        try:
            print(f"Downloading KeHE raw master from Supabase...")
            download_file(
                org_id=org_id,
                remote_path="raw/kehe/raw_master.csv",
                local_path=str(kehe_path),
            )
            print(f"✅ KeHE downloaded to {kehe_path}")
        except Exception as e:
            print(f"❌ Failed to download KeHE raw master: {repr(e)}")

    if kehe_path.exists():
        df_kehe = pd.read_csv(
            kehe_path,
            dtype={
                "UPC": "string",
                "ProductDescription": "string",
            },
        )

        unique_kehe = (
            df_kehe[
                [
                    "ProductDescription",
                    "UPC",
                ]
            ]
            .dropna(subset=["ProductDescription"])
            .drop_duplicates()
            .rename(
                columns={
                    "ProductDescription": "raw_sku",
                    "UPC": "raw_upc",
                }
            )
        )

        for row in unique_kehe.to_dict("records"):
            products.append(
                {
                    "source": "kehe",
                    "raw_sku": row["raw_sku"],
                    "raw_upc": row["raw_upc"],
                }
            )

    # =====================================================
    # UNFI
    # =====================================================

    unfi_path = Path(
        f"backend/data/{org_id}/raw/unfi/raw_master.csv"
    )

    print(f"UNFI local path exists: {unfi_path.exists()} — {unfi_path}")

    if not unfi_path.exists():
        try:
            print(f"Downloading UNFI raw master from Supabase...")
            download_file(
                org_id=org_id,
                remote_path="raw/unfi/raw_master.csv",
                local_path=str(unfi_path),
            )
            print(f"✅ UNFI downloaded to {unfi_path}")
        except Exception as e:
            print(f"❌ Failed to download UNFI raw master: {repr(e)}")

    if unfi_path.exists():
        df_unfi = pd.read_csv(
            unfi_path,
            dtype={
                "UPC": "string",
            },
        )

        # UNFI's product description is the blank column
        # immediately preceding UPC.
        upc_idx = df_unfi.columns.get_loc("UPC")
        sku_col = df_unfi.columns[upc_idx - 1]

        unique_unfi = (
            df_unfi[
                [
                    sku_col,
                    "UPC",
                ]
            ]
            .dropna(subset=[sku_col])
            .drop_duplicates()
            .rename(
                columns={
                    sku_col: "raw_sku",
                    "UPC": "raw_upc",
                }
            )
        )

        for row in unique_unfi.to_dict("records"):
            products.append(
                {
                    "source": "unfi",
                    "raw_sku": row["raw_sku"],
                    "raw_upc": row["raw_upc"],
                }
            )

    return products

def normalize_upc(upc) -> str | None:
    """
    Convert distributor UPC/GTIN representations into a common
    product-identity comparison key.

    This value is only for matching. Raw UPCs are preserved separately.
    """

    if upc is None:
        return None

    digits = "".join(
        char for char in str(upc).strip()
        if char.isdigit()
    )

    if not digits:
        return None

    # Strip distributor/GTIN leading zero padding.
    digits = digits.lstrip("0")

    # KeHE UPC-A values include a check digit.
    # UNFI's representation in our export effectively corresponds
    # to the UPC body without that final check digit.
    #
    # Bring both down to the 11-digit UPC body.
    if len(digits) >= 12:
        digits = digits[:11]

    return digits

def add_reconciliation_keys(products: list[dict]) -> list[dict]:
    enriched = []

    for product in products:
        enriched.append(
            {
                **product,
                "normalized_upc": normalize_upc(
                    product.get("raw_upc")
                ),
            }
        )

    return enriched

def auto_match_products(products: list[dict]) -> list[dict]:
    """
    Automatically match raw distributor products using normalized UPC.

    Returns one suggestion per normalized UPC that appears across
    multiple distributor sources.

    Example output:
    {
        "match_type": "upc",
        "confidence": "high",
        "normalized_upc": "85006308602",
        "products": [
            {
                "source": "kehe",
                "raw_sku": "ICE CREAM FROCO PNT BTTR",
                "raw_upc": "850063086028",
            },
            {
                "source": "unfi",
                "raw_sku": "FROCO,PEANUT BUTTER",
                "raw_upc": "0085006308602",
            },
        ],
    }
    """

    products_with_keys = add_reconciliation_keys(products)

    grouped = {}

    for product in products_with_keys:
        normalized_upc = product.get("normalized_upc")

        if not normalized_upc:
            continue

        grouped.setdefault(
            normalized_upc,
            [],
        ).append(product)

    matches = []

    for normalized_upc, grouped_products in grouped.items():
        sources = {
            product["source"]
            for product in grouped_products
        }

        # Only treat this as a reconciliation match when
        # the UPC appears across multiple distributor sources.
        if len(sources) < 2:
            continue

        matches.append(
            {
                "match_type": "upc",
                "confidence": "high",
                "normalized_upc": normalized_upc,
                "products": [
                    {
                        "source": product["source"],
                        "raw_sku": product["raw_sku"],
                        "raw_upc": product["raw_upc"],
                    }
                    for product in grouped_products
                ],
            }
        )

    return matches

def get_unmatched_products(
    products: list[dict],
    matches: list[dict],
) -> list[dict]:
    """
    Return products that were not included in any auto-match.
    """

    matched_keys = {
        (
            product["source"],
            product["raw_sku"],
            product["raw_upc"],
        )
        for match in matches
        for product in match["products"]
    }

    unmatched = []

    for product in products:
        key = (
            product["source"],
            product["raw_sku"],
            product["raw_upc"],
        )

        if key not in matched_keys:
            unmatched.append(product)

    return unmatched


def get_reconciliation_payload(org_id: str) -> dict:
    products = get_reconciliation_products(org_id)
    matches = auto_match_products(products)
    unmatched_products = get_unmatched_products(
        products,
        matches,
    )

    return {
        "products": products,
        "suggested_matches": matches,
        "unmatched_products": unmatched_products,
    }

def save_sku_reconciliation(
    org_id: str,
    groups: list[dict],
) -> dict:
    """
    Save the user's finalized SKU reconciliation as sku_name_map.csv.

    Each frontend product group becomes one canonical clean_sku.
    Every raw distributor SKU in that group maps to that clean_sku.
    """

    rows = []

    for group in groups:
        clean_sku = str(
            group.get("cleanSku", "")
        ).strip()

        units_per_case = group.get(
            "unitsPerCase"
        )

        products = group.get(
            "products",
            [],
        )

        # -----------------------------------------------
        # Validate canonical product
        # -----------------------------------------------

        if not clean_sku:
            raise ValueError(
                "Every product group must have a product name."
            )

        try:
            units_per_case = int(
                units_per_case
            )
        except (TypeError, ValueError):
            raise ValueError(
                f"Invalid units per case for {clean_sku}."
            )

        if units_per_case <= 0:
            raise ValueError(
                f"Units per case must be greater than 0 for {clean_sku}."
            )

        if not products:
            raise ValueError(
                f"{clean_sku} does not contain any raw SKUs."
            )

        # -----------------------------------------------
        # Flatten raw SKUs
        # -----------------------------------------------

        for product in products:
            raw_sku = str(
                product.get("rawSku", "")
            ).strip()

            if not raw_sku:
                raise ValueError(
                    f"A raw SKU is missing for {clean_sku}."
                )

            rows.append(
                {
                    "raw_sku": raw_sku,
                    "clean_sku": clean_sku,
                    "units_per_case": units_per_case,
                }
            )

    if not rows:
        raise ValueError(
            "No SKU reconciliation rows were provided."
        )

    df = pd.DataFrame(rows)

    # ---------------------------------------------------
    # Protect against conflicting mappings
    # ---------------------------------------------------

    conflicts = (
        df.groupby("raw_sku")["clean_sku"]
        .nunique()
    )

    conflicting_raw_skus = conflicts[
        conflicts > 1
    ].index.tolist()

    if conflicting_raw_skus:
        raise ValueError(
            "The same raw SKU was assigned to multiple products: "
            + ", ".join(conflicting_raw_skus)
        )

    # Remove accidental exact duplicates
    df = df.drop_duplicates(
        subset=[
            "raw_sku",
            "clean_sku",
            "units_per_case",
        ]
    )

    # ---------------------------------------------------
    # Save locally
    # ---------------------------------------------------

    map_path = Path(
        f"backend/data/{org_id}/maps/sku_name_map.csv"
    )

    map_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        map_path,
        index=False,
    )

    # ---------------------------------------------------
    # Upload to Supabase
    # ---------------------------------------------------

    upload_file(
        local_path=str(map_path),
        org_id=org_id,
        remote_path="maps/sku_name_map.csv",
    )

    print(
        f"✅ Saved SKU reconciliation: {len(df)} mappings"
    )

    return {
        "status": "success",
        "mapping_count": len(df),
        "product_count": df[
            "clean_sku"
        ].nunique(),
    }
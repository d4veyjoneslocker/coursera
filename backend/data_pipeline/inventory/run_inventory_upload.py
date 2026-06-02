from backend.data_pipeline.inventory.kehe_inventory import update_kehe_inventory_raw_master
from backend.data_pipeline.inventory.unfi_inventory import update_unfi_inventory_raw_master

def run_inventory_upload(distributor: str, raw_new_month_path: str, org_id: str):
    distributor = distributor.lower().strip()

    if distributor == "kehe":
        return update_kehe_inventory_raw_master(raw_new_month_path, org_id)

    if distributor == "unfi":
        return update_unfi_inventory_raw_master(raw_new_month_path, org_id)

    raise ValueError(f"Unsupported inventory distributor: {distributor}")


if __name__ == "__main__":
    run_inventory_upload(
        distributor="unfi",
        raw_new_month_path="backend/data/default_org/raw/inventory/unfi/unfi_inventory_new.csv",
        org_id="default_org",
    )
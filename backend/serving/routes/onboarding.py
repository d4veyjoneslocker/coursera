from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.onboarding.sku_reconciliation import get_reconciliation_payload, save_sku_reconciliation
from backend.onboarding.sku_reconciliation import get_reconciliation_payload


router = APIRouter(
    prefix="/onboarding",
    tags=["onboarding"],
)

class ReconciliationProductRequest(BaseModel):
    id: str
    source: str
    rawSku: str
    rawUpc: str | None = None


class ReconciliationGroupRequest(BaseModel):
    id: str
    cleanSku: str
    unitsPerCase: int
    products: list[ReconciliationProductRequest]


class SaveReconciliationRequest(BaseModel):
    org_id: str
    groups: list[ReconciliationGroupRequest]


@router.get("/sku-reconciliation")
def get_sku_reconciliation(org_id: str):
    return get_reconciliation_payload(org_id)



@router.post("/sku-reconciliation")
def save_reconciliation(
    request: SaveReconciliationRequest,
):
    try:
        groups = [
            group.model_dump()
            for group in request.groups
        ]

        return save_sku_reconciliation(
            org_id=request.org_id,
            groups=groups,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        print(
            f"❌ Failed to save SKU reconciliation: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to save SKU reconciliation.",
        )
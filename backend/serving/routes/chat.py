import os
import traceback

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.chat.service import ask_metric


router = APIRouter(
    prefix="/api/chat",
    tags=["Ask SKUba"],
)


class AskSkubaRequest(BaseModel):
    message: str = Field(min_length=1)
    context: dict | None = None


@router.post("/ask")
def ask_skuba(body: AskSkubaRequest):
    org_id = os.getenv("ASK_SKUBA_ORG_ID")

    if not org_id:
        raise HTTPException(
            status_code=500,
            detail="ASK_SKUBA_ORG_ID is not configured.",
        )

    try:
        return ask_metric(
            org_id=org_id,
            user_message=body.message.strip(),
            context=body.context,
        )

    except ValueError as e:
        return {
            "status": "clarification",
            "message": str(e),
            "options": None,
        }

    except Exception as e:
        print(f"❌ ASK SKUBA ERROR: {e}")
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail="SKUba was unable to answer that question.",
        )
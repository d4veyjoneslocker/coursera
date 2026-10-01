import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from backend.serving.routes.overview import router as overview_router
from backend.serving.routes.store_health import router as store_health_router
from backend.serving.routes.upload import router as upload_router
from backend.serving.routes.distributors import router as distributors_router
from backend.serving.routes.exports import router as exports_router
from backend.serving.routes.email import router as email_router
from backend.serving.routes.insights_new import router as insights_new
from backend.data_pipeline.table_loader import clear_table_cache, load_org_tables
from backend.serving.routes.business_analysis import router as business_analysis
from backend.serving.routes.free_trial import router as free_trial
from backend.serving.routes.onboarding import router as onboarding
from backend.serving.routes.business_review import router as business_review
from backend.serving.routes.inventory.inventory import (router as inventory, _load_cached_inventory_assessments)

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):

    BASE_DATA_DIR = Path("backend/data")
    org_id = "67a96381-5014-4a9b-bfe8-a14e6da5affe"

    try:
        _load_cached_inventory_assessments(
            org_dir=BASE_DATA_DIR / org_id,
            org_id=org_id,
        )

        print(
            f"🔥 INVENTORY CACHE WARMED: {org_id}",
            flush=True,
        )

    except Exception as exc:
        print(
            f"⚠️ INVENTORY CACHE WARM FAILED "
            f"for {org_id}: {repr(exc)}",
            flush=True,
        )

    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://crisp-dashboard.vercel.app",
        "https://crisp-dashboard-git-dev-d4veyjoneslockers-projects.vercel.app",
        "https://app.sku-ba.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "API is running"}

app.include_router(overview_router)
app.include_router(store_health_router)
app.include_router(upload_router)
app.include_router(distributors_router)
app.include_router(exports_router)
app.include_router(email_router)
app.include_router(insights_new)
app.include_router(business_analysis)
app.include_router(free_trial)
app.include_router(onboarding)
app.include_router(business_review)
app.include_router(inventory)


ADMIN_REFRESH_SECRET = os.getenv("ADMIN_REFRESH_SECRET")

@app.post("/admin/clear-cache")
def clear_cache(x_refresh_secret: str | None = Header(default=None)):

    if x_refresh_secret != ADMIN_REFRESH_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    clear_table_cache()


    return {"message": "cache cleared"}

   
@app.post("/admin/warm-cache")
def warm_cache(x_refresh_secret: str | None = Header(default=None)):

    if x_refresh_secret != ADMIN_REFRESH_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    org_ids = [
        "default_org",
    ]

    warmed = []

    for org_id in org_ids:
        load_org_tables(org_id)
        warmed.append(org_id)

    return {
        "message": "cache warmed",
        "organizations": warmed,
    }


@app.post("/admin/reload-cache")
def reload_cache(
    org_id: str,
    x_refresh_secret: str | None = Header(default=None),
):
    if x_refresh_secret != ADMIN_REFRESH_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    clear_table_cache(org_id)
    load_org_tables(org_id)

    return {
        "message": "cache cleared and warmed",
        "org_id": org_id,
    }

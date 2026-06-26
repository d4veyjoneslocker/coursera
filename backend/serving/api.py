import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from backend.serving.routes.overview import router as overview_router
from backend.serving.routes.store_health import router as store_health_router
from backend.serving.routes.upload import router as upload_router
from backend.serving.routes.distributors import router as distributors_router
from backend.serving.routes.exports import router as exports_router
from backend.serving.routes.insights import router as insights_router
from backend.serving.routes.email import router as email_router
from backend.serving.routes.insights_new import router as insights_new
from backend.data_pipeline.table_loader import clear_table_cache

load_dotenv()

app = FastAPI()

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
app.include_router(insights_router)
app.include_router(email_router)
app.include_router(insights_new)


ADMIN_REFRESH_SECRET = os.getenv("ADMIN_REFRESH_SECRET")

@app.post("/admin/clear-cache")
def clear_cache(x_refresh_secret: str | None = Header(default=None)):

    if x_refresh_secret != ADMIN_REFRESH_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    clear_table_cache()


    return {"message": "cache cleared"}


   






from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware

from backend.serving.routes.overview import router as overview_router
from backend.serving.routes.store_health import router as store_health_router
import os
from fastapi import FastAPI, HTTPException, Header
from backend.data_pipeline.table_loader import clear_table_cache
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://crisp-dashboard.vercel.app",  # use your real URL
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



ADMIN_REFRESH_SECRET = os.getenv("ADMIN_REFRESH_SECRET")

@app.post("/admin/clear-cache")
def clear_cache(x_refresh_secret: str | None = Header(default=None)):

    if x_refresh_secret != ADMIN_REFRESH_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    clear_table_cache()


    return {"message": "cache cleared"}


   






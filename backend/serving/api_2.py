from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.serving.routes.overview import router as overview_router
from backend.serving.routes.store_health import router as store_health_router

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
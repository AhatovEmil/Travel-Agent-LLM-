from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import ensure_schema
from .routers import auth, share, trips

ensure_schema()

app = FastAPI(
    title=settings.app_name,
    description="ИИ-агент, который планирует поездки: маршрут, бюджет и чеклист.",
    version="1.0.0",
)

origins = [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(trips.router)
app.include_router(share.router)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok", "service": settings.app_name}

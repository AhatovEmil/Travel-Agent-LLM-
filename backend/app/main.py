from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import ensure_schema
from .routers import auth, billing, photos, share, trips

ensure_schema()

from .services.recover import fail_stuck_running_trips

fail_stuck_running_trips()

_docs = None if settings.is_production else "/docs"
_redoc = None if settings.is_production else "/redoc"
_openapi = None if settings.is_production else "/openapi.json"

app = FastAPI(
    title=settings.app_name,
    description="ИИ-агент, который планирует поездки: маршрут, бюджет и чеклист.",
    version="1.0.0",
    docs_url=_docs,
    redoc_url=_redoc,
    openapi_url=_openapi,
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
# credentials + "*" несовместимы безопасно — при * отключаем cookies/credentials
allow_credentials = "*" not in origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if allow_credentials else ["*"],
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(billing.router)
app.include_router(trips.router)
app.include_router(share.router)
app.include_router(photos.router)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok", "service": settings.app_name}

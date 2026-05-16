from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from app.config import settings
    from app.routers.journey import router as journey_router
    from app.routers.policies import router as policies_router
    from app.routers.status import router as status_router
except ModuleNotFoundError:
    from config import settings
    from routers.journey import router as journey_router
    from routers.policies import router as policies_router
    from routers.status import router as status_router

app = FastAPI(
    title="PolicyChesko API",
    version="0.1.0",
    description="Prototype API for policy enquiries, KYC, and claim/fund status.",
)


def _build_allowed_origins(raw_origin: str) -> list[str]:
    # Supports single origin or comma-separated origins in FRONTEND_ORIGIN.
    values = [part.strip().rstrip("/") for part in (raw_origin or "").split(",")]
    origins = [item for item in values if item]
    defaults = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://policychesko-frontend.vercel.app",
    ]
    for item in defaults:
        if item not in origins:
            origins.append(item)
    return origins


allowed_origins = _build_allowed_origins(settings.frontend_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(policies_router, prefix="/api", tags=["policies"])
app.include_router(status_router, prefix="/api", tags=["status"])
app.include_router(journey_router, prefix="/api", tags=["journey"])

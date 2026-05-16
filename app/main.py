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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173"],
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

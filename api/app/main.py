from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.db.session import SessionLocal
from app.services.demo import DemoService


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db = SessionLocal()
    try:
        await DemoService(db).seed_baseline()
    finally:
        db.close()
    yield


app = FastAPI(
    title="GovDoc SecureFlow API",
    description="Backend for public-sector document intake and triage",
    version="0.1.0",
    lifespan=lifespan,
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "api"}


app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

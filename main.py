from fastapi import FastAPI

from app.routes.health import router as health_router


app = FastAPI(
    title="RefCentral API",
    description="RefCentral rugby management backend",
    version="1.0.0",
)


app.include_router(health_router)


@app.get("/")
def root():
    return {
        "success": True,
        "message": "Welcome to RefCentral API",
        "version": "1.0.0",
    }
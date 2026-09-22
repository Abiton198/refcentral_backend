from fastapi import FastAPI

# Import application route modules
from app.routes.health import router as health_router
from app.routes.clubs import router as clubs_router
from app.routes.players import router as players_router


# Create the FastAPI application
app = FastAPI(
    title="RefCentral API",
    description="Backend API for RefCentral rugby management",
    version="1.0.0",
)


# Register API routes
app.include_router(health_router)
app.include_router(clubs_router)
app.include_router(players_router)


@app.get("/")
def root():
    """
    Confirm that the backend is running.
    """

    return {
        "success": True,
        "message": "Welcome to RefCentral API",
        "version": "1.0.0",
    }
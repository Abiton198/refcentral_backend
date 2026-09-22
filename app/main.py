from fastapi import FastAPI

# Import application route modules
from app.routes.health import router as health_router
from app.routes.clubs import router as clubs_router


# Create the FastAPI application
app = FastAPI(
    title="RefCentral API",
    description="Backend API for RefCentral rugby management",
    version="1.0.0",
)


# Register the health-check routes
app.include_router(health_router)

# Register the club-management routes
app.include_router(clubs_router)


@app.get("/")
def root():
    """
    Basic endpoint used to confirm that the API is running.
    """

    return {
        "success": True,
        "message": "Welcome to RefCentral API",
        "version": "1.0.0",
    }
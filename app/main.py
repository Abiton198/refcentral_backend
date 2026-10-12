"""
RefCentral API

Main FastAPI application.

The backend is structured around the new RefCentral model:

Users
  ↓
Team Memberships
  ↓
Teams
  ↓
Players
  ↓
Appointments
  ↓
Matchday Squads
  ↓
Referee Verification
"""

from fastapi import FastAPI

from app.routes.health import router as health_router
from app.routes.teams import router as teams_router
from app.routes.players import router as players_router
from app.routes.appointments import router as appointments_router
from app.routes.team_memberships import (router as team_memberships_router,)
from app.routes.player_documents import (router as player_documents_router,)
from app.routes.player_photos import (router as player_photos_router,)
from app.routes.team_registrations import (
    router as team_registrations_router,
)

# ---------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------

app = FastAPI(
    title="RefCentral API",
    description=(
        "Backend API for RefCentral rugby management, "
        "including teams, player registration, fixtures, "
        "teamsheets and matchday verification."
    ),
    version="1.0.0",
)



from fastapi.middleware.cors import CORSMiddleware

# Allow the RefCentral frontend to communicate with the backend.
# Add your actual deployed frontend domains to this list.
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://127.0.0.1:5173",
    "https://refcentral.netlify.app",
    "https://epreferees.netlify.app",
    "https://epreferees.co.za",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# API routes
# ---------------------------------------------------------

# Basic health/status endpoint.
app.include_router(health_router)

# Team management.
app.include_router(teams_router)

# Team administrator and player registration.
app.include_router(players_router)

# Executive-created fixtures and referee appointments.
app.include_router(appointments_router)

# Assign users to teams as team administrators.
app.include_router(team_memberships_router)

# Player National ID / passport documents.
app.include_router(player_documents_router)

# Private player profile photographs.
app.include_router(player_photos_router)

# team onboard
app.include_router(team_registrations_router)

# ---------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------

@app.get("/")
def root():
    """
    Basic API welcome endpoint.

    Useful for confirming that the backend is running.
    """
    return {
        "success": True,
        "message": "Welcome to RefCentral API",
        "version": "1.0.0",
    }
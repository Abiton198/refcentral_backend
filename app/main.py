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
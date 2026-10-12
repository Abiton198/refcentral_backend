"""
Player Document Schemas

Identity documents are deliberately separated from the
normal player profile.

Examples:

- National ID
- Passport

The full document number is NEVER returned by the normal
player endpoints.
"""


from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PlayerDocumentResponse(BaseModel):
    """
    Safe representation of a player's identity document.
    """

    document_id: str

    player_id: str

    document_type: str

    document_last4: Optional[str] = None

    document_url: Optional[str] = None

    status: str

    verified: bool

    created_at: Optional[datetime] = None

    updated_at: Optional[datetime] = None

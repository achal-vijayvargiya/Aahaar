"""Token schemas for authentication."""
from typing import Optional
from pydantic import BaseModel


class Token(BaseModel):
    """Token response schema."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token data schema."""
    username: Optional[str] = None
    user_id: Optional[int] = None


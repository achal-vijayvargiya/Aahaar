"""Token schemas for authentication."""
from typing import Optional
from pydantic import BaseModel


class Token(BaseModel):
    """Token response schema."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token data schema."""
    sub: Optional[str] = None  # username from token


class LoginRequest(BaseModel):
    """Login request schema for form data."""
    username: str
    password: str


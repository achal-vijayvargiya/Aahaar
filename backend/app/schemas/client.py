"""Client schemas for request/response validation."""
from typing import Optional
from datetime import datetime, date
from pydantic import BaseModel, EmailStr, ConfigDict


class ClientBase(BaseModel):
    """Base client schema."""
    first_name: str
    last_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    medical_history: Optional[str] = None
    notes: Optional[str] = None
    assigned_doctor_id: Optional[int] = None


class ClientCreate(ClientBase):
    """Schema for creating a client."""
    pass


class ClientUpdate(BaseModel):
    """Schema for updating a client."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    medical_history: Optional[str] = None
    notes: Optional[str] = None
    assigned_doctor_id: Optional[int] = None


class Client(ClientBase):
    """Schema for client response."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


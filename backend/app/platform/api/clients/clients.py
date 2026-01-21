"""
Platform Clients API Routes.
Client management endpoints for the platform.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
import re
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.platform.data.repositories.platform_client_repository import PlatformClientRepository

router = APIRouter(prefix="/clients", tags=["Platform Clients"])


# Request/Response Models
class ClientCreate(BaseModel):
    """Client creation request model."""
    external_client_id: Optional[str] = None
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    location: Optional[str] = None
    wake_time: Optional[str] = None
    sleep_time: Optional[str] = None
    work_schedule_start: Optional[str] = None
    work_schedule_end: Optional[str] = None
    
    @field_validator('wake_time', 'sleep_time', 'work_schedule_start', 'work_schedule_end')
    @classmethod
    def validate_time_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate time format is HH:MM (24-hour format)."""
        if v is None:
            return v
        if not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', v):
            raise ValueError('Time must be in HH:MM format (24-hour)')
        return v


class ClientUpdate(BaseModel):
    """Client update request model."""
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    location: Optional[str] = None
    wake_time: Optional[str] = None
    sleep_time: Optional[str] = None
    work_schedule_start: Optional[str] = None
    work_schedule_end: Optional[str] = None
    
    @field_validator('wake_time', 'sleep_time', 'work_schedule_start', 'work_schedule_end')
    @classmethod
    def validate_time_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate time format is HH:MM (24-hour format)."""
        if v is None:
            return v
        if not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', v):
            raise ValueError('Time must be in HH:MM format (24-hour)')
        return v


class ClientResponse(BaseModel):
    """Client response model."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    external_client_id: Optional[str]
    name: str
    age: Optional[int]
    gender: Optional[str]
    height_cm: Optional[float]
    weight_kg: Optional[float]
    location: Optional[str]
    wake_time: Optional[str] = None
    sleep_time: Optional[str] = None
    work_schedule_start: Optional[str] = None
    work_schedule_end: Optional[str] = None
    created_at: datetime
    updated_at: datetime


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    client_data: ClientCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new platform client.
    
    Args:
        client_data: Client creation data
        db: Database session
        
    Returns:
        Created client information
        
    Raises:
        HTTPException: If validation fails or creation error occurs
    """
    repository = PlatformClientRepository(db)
    try:
        client = repository.create(client_data.model_dump())
        return ClientResponse.model_validate(client)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create client: {str(e)}"
        )


@router.get("/", response_model=List[ClientResponse])
async def get_clients(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    Get list of platform clients with pagination.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        List of clients
    """
    repository = PlatformClientRepository(db)
    clients = repository.get_all(skip=skip, limit=limit)
    return [ClientResponse.model_validate(client) for client in clients]


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get platform client by ID.
    
    Args:
        client_id: Client UUID
        db: Database session
        
    Returns:
        Client information
        
    Raises:
        HTTPException: If client not found
    """
    repository = PlatformClientRepository(db)
    client = repository.get_by_id(client_id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with id {client_id} not found"
        )
    return ClientResponse.model_validate(client)


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: UUID,
    client_data: ClientUpdate,
    db: Session = Depends(get_db)
):
    """
    Update platform client.
    
    Args:
        client_id: Client UUID
        client_data: Client update data
        db: Database session
        
    Returns:
        Updated client information
        
    Raises:
        HTTPException: If client not found or update fails
    """
    repository = PlatformClientRepository(db)
    update_dict = client_data.model_dump(exclude_unset=True)
    
    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update"
        )
    
    client = repository.update(client_id, update_dict)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with id {client_id} not found"
        )
    
    return ClientResponse.model_validate(client)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Delete platform client.
    
    Args:
        client_id: Client UUID
        db: Database session
        
    Raises:
        HTTPException: If client not found
    """
    repository = PlatformClientRepository(db)
    deleted = repository.delete(client_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with id {client_id} not found"
        )
    return None


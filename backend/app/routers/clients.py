"""Client management routes."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.client import Client
from app.models.user import User
from app.schemas.client import Client as ClientSchema, ClientCreate, ClientUpdate
from app.utils.logger import logger
from app.routers.auth import get_current_active_user

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.get("/", response_model=List[ClientSchema])
async def read_clients(
    skip: int = 0,
    limit: int = 100,
    search: str = Query(None, description="Search by name or email"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get list of clients with optional search."""
    query = db.query(Client)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Client.first_name.ilike(search_filter)) |
            (Client.last_name.ilike(search_filter)) |
            (Client.email.ilike(search_filter))
        )
    
    clients = query.offset(skip).limit(limit).all()
    logger.info(f"User {current_user.username} retrieved {len(clients)} clients")
    return clients


@router.get("/{client_id}", response_model=ClientSchema)
async def read_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get client by ID."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.post("/", response_model=ClientSchema, status_code=status.HTTP_201_CREATED)
async def create_client(
    client_in: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create new client."""
    # Check if client with email already exists
    if client_in.email:
        existing_client = db.query(Client).filter(Client.email == client_in.email).first()
        if existing_client:
            raise HTTPException(
                status_code=400,
                detail="Client with this email already exists"
            )
    
    # Create new client
    client = Client(**client_in.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    
    logger.info(f"User {current_user.username} created new client: {client.first_name} {client.last_name}")
    return client


@router.put("/{client_id}", response_model=ClientSchema)
async def update_client(
    client_id: int,
    client_in: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update client."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Update fields
    update_data = client_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)
    
    db.commit()
    db.refresh(client)
    
    logger.info(f"User {current_user.username} updated client: {client.first_name} {client.last_name}")
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete client."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    
    db.delete(client)
    db.commit()
    
    logger.info(f"User {current_user.username} deleted client: {client.first_name} {client.last_name}")
    return None


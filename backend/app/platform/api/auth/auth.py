"""Platform authentication routes."""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.platform.data.models.platform_user import PlatformUser
from app.platform.data.repositories.platform_user_repository import PlatformUserRepository
from app.platform.schemas.auth import Token
from app.platform.schemas.user import User
from app.platform.utils.security import verify_password, create_access_token, verify_token

router = APIRouter(prefix="/auth", tags=["Platform Auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/platform/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db)
) -> PlatformUser:
    """
    Get current authenticated user.
    
    Args:
        token: JWT token from Authorization header
        db: Database session
        
    Returns:
        PlatformUser instance
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = verify_token(token)
    if payload is None:
        raise credentials_exception
    
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    user_repo = PlatformUserRepository(db)
    user = user_repo.get_by_username(username)
    if user is None:
        raise credentials_exception
    
    return user


def get_current_active_user(
    current_user: Annotated[PlatformUser, Depends(get_current_user)]
) -> PlatformUser:
    """
    Get current active user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Active PlatformUser instance
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db)
):
    """
    Login endpoint to get access token.
    
    Args:
        form_data: OAuth2 password form with username and password
        db: Database session
        
    Returns:
        Token response with access_token and token_type
        
    Raises:
        HTTPException: If credentials are invalid or user is inactive
    """
    user_repo = PlatformUserRepository(db)
    user = user_repo.get_by_username(form_data.username)
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    access_token = create_access_token(
        data={"sub": user.username, "user_id": str(user.id)}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=User)
async def read_users_me(
    current_user: Annotated[PlatformUser, Depends(get_current_active_user)]
):
    """
    Get current user information.
    
    Args:
        current_user: Current authenticated and active user
        
    Returns:
        User schema with current user information
    """
    return current_user


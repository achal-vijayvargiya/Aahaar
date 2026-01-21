"""
Platform User Repository.
CRUD operations for platform users.
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from app.platform.data.models.platform_user import PlatformUser


class PlatformUserRepository:
    """
    Repository for platform user operations.
    
    Provides CRUD and basic query methods for platform users.
    No business logic - data access only.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(self, user_data: dict) -> PlatformUser:
        """
        Create a new platform user.
        
        Args:
            user_data: Dictionary with user fields
            
        Returns:
            Created PlatformUser instance
        """
        user = PlatformUser(**user_data)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def get_by_id(self, user_id: UUID) -> Optional[PlatformUser]:
        """
        Get platform user by ID.
        
        Args:
            user_id: User UUID
            
        Returns:
            PlatformUser instance or None
        """
        return self.db.query(PlatformUser).filter(PlatformUser.id == user_id).first()
    
    def get_by_username(self, username: str) -> Optional[PlatformUser]:
        """
        Get platform user by username.
        
        Args:
            username: User username
        
        Returns:
            PlatformUser instance or None
        """
        return self.db.query(PlatformUser).filter(
            PlatformUser.username == username
        ).first()
    
    def get_by_email(self, email: str) -> Optional[PlatformUser]:
        """
        Get platform user by email.
        
        Args:
            email: User email
            
        Returns:
            PlatformUser instance or None
        """
        return self.db.query(PlatformUser).filter(
            PlatformUser.email == email
        ).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[PlatformUser]:
        """
        Get all platform users with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of PlatformUser instances
        """
        return self.db.query(PlatformUser).offset(skip).limit(limit).all()
    
    def update(self, user_id: UUID, update_data: dict) -> Optional[PlatformUser]:
        """
        Update platform user.
        
        Args:
            user_id: User UUID
            update_data: Dictionary with fields to update
            
        Returns:
            Updated PlatformUser instance or None
        """
        user = self.get_by_id(user_id)
        if user:
            for key, value in update_data.items():
                setattr(user, key, value)
            self.db.commit()
            self.db.refresh(user)
        return user
    
    def delete(self, user_id: UUID) -> bool:
        """
        Delete platform user.
        
        Args:
            user_id: User UUID
            
        Returns:
            True if deleted, False if not found
        """
        user = self.get_by_id(user_id)
        if user:
            self.db.delete(user)
            self.db.commit()
            return True
        return False


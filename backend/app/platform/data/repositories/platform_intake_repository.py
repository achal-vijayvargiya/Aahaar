"""
Platform Intake Repository.
CRUD operations for platform intakes.
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from app.platform.data.models.platform_intake import PlatformIntake


class PlatformIntakeRepository:
    """
    Repository for platform intake operations.
    
    Provides CRUD and basic query methods for platform intakes.
    No business logic - data access only.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(self, intake_data: dict) -> PlatformIntake:
        """
        Create a new platform intake.
        
        Args:
            intake_data: Dictionary with intake fields
            
        Returns:
            Created PlatformIntake instance
        """
        intake = PlatformIntake(**intake_data)
        self.db.add(intake)
        self.db.commit()
        self.db.refresh(intake)
        return intake
    
    def get_by_id(self, intake_id: UUID) -> Optional[PlatformIntake]:
        """
        Get platform intake by ID.
        
        Args:
            intake_id: Intake UUID
            
        Returns:
            PlatformIntake instance or None
        """
        return self.db.query(PlatformIntake).filter(PlatformIntake.id == intake_id).first()
    
    def get_by_client_id(self, client_id: UUID) -> List[PlatformIntake]:
        """
        Get all intakes for a client.
        
        Args:
            client_id: Client UUID
            
        Returns:
            List of PlatformIntake instances
        """
        return self.db.query(PlatformIntake).filter(
            PlatformIntake.client_id == client_id
        ).all()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[PlatformIntake]:
        """
        Get all platform intakes with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of PlatformIntake instances
        """
        return self.db.query(PlatformIntake).offset(skip).limit(limit).all()
    
    def update(self, intake_id: UUID, intake_data: dict) -> Optional[PlatformIntake]:
        """
        Update platform intake.
        
        Args:
            intake_id: Intake UUID
            intake_data: Dictionary with fields to update
            
        Returns:
            Updated PlatformIntake instance or None
        """
        intake = self.get_by_id(intake_id)
        if intake:
            for key, value in intake_data.items():
                setattr(intake, key, value)
            self.db.commit()
            self.db.refresh(intake)
        return intake
    
    def delete(self, intake_id: UUID) -> bool:
        """
        Delete platform intake.
        
        Args:
            intake_id: Intake UUID
            
        Returns:
            True if deleted, False if not found
        """
        intake = self.get_by_id(intake_id)
        if intake:
            self.db.delete(intake)
            self.db.commit()
            return True
        return False


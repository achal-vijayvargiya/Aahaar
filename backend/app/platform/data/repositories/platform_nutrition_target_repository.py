"""
Platform Nutrition Target Repository.
CRUD operations for platform nutrition targets.
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from app.platform.data.models.platform_nutrition_target import PlatformNutritionTarget


class PlatformNutritionTargetRepository:
    """
    Repository for platform nutrition target operations.
    
    Provides CRUD and basic query methods for platform nutrition targets.
    No business logic - data access only.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(self, target_data: dict) -> PlatformNutritionTarget:
        """
        Create a new platform nutrition target.
        
        Args:
            target_data: Dictionary with target fields
            
        Returns:
            Created PlatformNutritionTarget instance
        """
        target = PlatformNutritionTarget(**target_data)
        self.db.add(target)
        self.db.commit()
        self.db.refresh(target)
        return target
    
    def get_by_id(self, target_id: UUID) -> Optional[PlatformNutritionTarget]:
        """
        Get platform nutrition target by ID.
        
        Args:
            target_id: Target UUID
            
        Returns:
            PlatformNutritionTarget instance or None
        """
        return self.db.query(PlatformNutritionTarget).filter(
            PlatformNutritionTarget.id == target_id
        ).first()
    
    def get_by_assessment_id(self, assessment_id: UUID) -> Optional[PlatformNutritionTarget]:
        """
        Get nutrition target for an assessment.
        
        Args:
            assessment_id: Assessment UUID
            
        Returns:
            PlatformNutritionTarget instance or None
        """
        return self.db.query(PlatformNutritionTarget).filter(
            PlatformNutritionTarget.assessment_id == assessment_id
        ).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[PlatformNutritionTarget]:
        """
        Get all platform nutrition targets with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of PlatformNutritionTarget instances
        """
        return self.db.query(PlatformNutritionTarget).offset(skip).limit(limit).all()
    
    def update(self, target_id: UUID, target_data: dict) -> Optional[PlatformNutritionTarget]:
        """
        Update platform nutrition target.
        
        Args:
            target_id: Target UUID
            target_data: Dictionary with fields to update
            
        Returns:
            Updated PlatformNutritionTarget instance or None
        """
        target = self.get_by_id(target_id)
        if target:
            for key, value in target_data.items():
                setattr(target, key, value)
            self.db.commit()
            self.db.refresh(target)
        return target
    
    def delete(self, target_id: UUID) -> bool:
        """
        Delete platform nutrition target.
        
        Args:
            target_id: Target UUID
            
        Returns:
            True if deleted, False if not found
        """
        target = self.get_by_id(target_id)
        if target:
            self.db.delete(target)
            self.db.commit()
            return True
        return False


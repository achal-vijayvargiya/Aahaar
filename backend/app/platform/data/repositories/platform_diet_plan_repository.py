"""
Platform Diet Plan Repository.
CRUD operations for platform diet plans.
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from app.platform.data.models.platform_diet_plan import PlatformDietPlan


class PlatformDietPlanRepository:
    """
    Repository for platform diet plan operations.
    
    Provides CRUD and basic query methods for platform diet plans.
    No business logic - data access only.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(self, plan_data: dict) -> PlatformDietPlan:
        """
        Create a new platform diet plan.
        
        Args:
            plan_data: Dictionary with plan fields
            
        Returns:
            Created PlatformDietPlan instance
        """
        plan = PlatformDietPlan(**plan_data)
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan
    
    def get_by_id(self, plan_id: UUID) -> Optional[PlatformDietPlan]:
        """
        Get platform diet plan by ID.
        
        Args:
            plan_id: Plan UUID
            
        Returns:
            PlatformDietPlan instance or None
        """
        return self.db.query(PlatformDietPlan).filter(
            PlatformDietPlan.id == plan_id
        ).first()
    
    def get_by_client_id(self, client_id: UUID) -> List[PlatformDietPlan]:
        """
        Get all diet plans for a client.
        
        Args:
            client_id: Client UUID
            
        Returns:
            List of PlatformDietPlan instances
        """
        return self.db.query(PlatformDietPlan).filter(
            PlatformDietPlan.client_id == client_id
        ).all()
    
    def get_by_assessment_id(self, assessment_id: UUID) -> List[PlatformDietPlan]:
        """
        Get all diet plans for an assessment.
        
        Args:
            assessment_id: Assessment UUID
            
        Returns:
            List of PlatformDietPlan instances
        """
        return self.db.query(PlatformDietPlan).filter(
            PlatformDietPlan.assessment_id == assessment_id
        ).all()
    
    def get_by_status(self, status: str) -> List[PlatformDietPlan]:
        """
        Get diet plans by status.
        
        Args:
            status: Plan status (active | archived | draft)
            
        Returns:
            List of PlatformDietPlan instances
        """
        return self.db.query(PlatformDietPlan).filter(
            PlatformDietPlan.status == status
        ).all()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[PlatformDietPlan]:
        """
        Get all platform diet plans with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of PlatformDietPlan instances
        """
        return self.db.query(PlatformDietPlan).offset(skip).limit(limit).all()
    
    def update(self, plan_id: UUID, plan_data: dict) -> Optional[PlatformDietPlan]:
        """
        Update platform diet plan.
        
        Args:
            plan_id: Plan UUID
            plan_data: Dictionary with fields to update
            
        Returns:
            Updated PlatformDietPlan instance or None
        """
        plan = self.get_by_id(plan_id)
        if plan:
            for key, value in plan_data.items():
                setattr(plan, key, value)
            self.db.commit()
            self.db.refresh(plan)
        return plan
    
    def delete(self, plan_id: UUID) -> bool:
        """
        Delete platform diet plan.
        
        Args:
            plan_id: Plan UUID
            
        Returns:
            True if deleted, False if not found
        """
        plan = self.get_by_id(plan_id)
        if plan:
            self.db.delete(plan)
            self.db.commit()
            return True
        return False


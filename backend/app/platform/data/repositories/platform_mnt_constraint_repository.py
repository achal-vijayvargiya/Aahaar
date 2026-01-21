"""
Platform MNT Constraint Repository.
CRUD operations for platform MNT constraints.
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from app.platform.data.models.platform_mnt_constraint import PlatformMNTConstraint


class PlatformMNTConstraintRepository:
    """
    Repository for platform MNT constraint operations.
    
    Provides CRUD and basic query methods for platform MNT constraints.
    No business logic - data access only.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(self, constraint_data: dict) -> PlatformMNTConstraint:
        """
        Create a new platform MNT constraint.
        
        Args:
            constraint_data: Dictionary with constraint fields
            
        Returns:
            Created PlatformMNTConstraint instance
        """
        constraint = PlatformMNTConstraint(**constraint_data)
        self.db.add(constraint)
        self.db.commit()
        self.db.refresh(constraint)
        return constraint
    
    def get_by_id(self, constraint_id: UUID) -> Optional[PlatformMNTConstraint]:
        """
        Get platform MNT constraint by ID.
        
        Args:
            constraint_id: Constraint UUID
            
        Returns:
            PlatformMNTConstraint instance or None
        """
        return self.db.query(PlatformMNTConstraint).filter(
            PlatformMNTConstraint.id == constraint_id
        ).first()
    
    def get_by_assessment_id(self, assessment_id: UUID) -> List[PlatformMNTConstraint]:
        """
        Get all MNT constraints for an assessment.
        
        Args:
            assessment_id: Assessment UUID
            
        Returns:
            List of PlatformMNTConstraint instances
        """
        return self.db.query(PlatformMNTConstraint).filter(
            PlatformMNTConstraint.assessment_id == assessment_id
        ).all()
    
    def get_by_rule_id(self, rule_id: str) -> List[PlatformMNTConstraint]:
        """
        Get MNT constraints by rule ID.
        
        Args:
            rule_id: MNT rule identifier
            
        Returns:
            List of PlatformMNTConstraint instances
        """
        return self.db.query(PlatformMNTConstraint).filter(
            PlatformMNTConstraint.rule_id == rule_id
        ).all()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[PlatformMNTConstraint]:
        """
        Get all platform MNT constraints with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of PlatformMNTConstraint instances
        """
        return self.db.query(PlatformMNTConstraint).offset(skip).limit(limit).all()
    
    def update(self, constraint_id: UUID, constraint_data: dict) -> Optional[PlatformMNTConstraint]:
        """
        Update platform MNT constraint.
        
        Args:
            constraint_id: Constraint UUID
            constraint_data: Dictionary with fields to update
            
        Returns:
            Updated PlatformMNTConstraint instance or None
        """
        constraint = self.get_by_id(constraint_id)
        if constraint:
            for key, value in constraint_data.items():
                setattr(constraint, key, value)
            self.db.commit()
            self.db.refresh(constraint)
        return constraint
    
    def delete(self, constraint_id: UUID) -> bool:
        """
        Delete platform MNT constraint.
        
        Args:
            constraint_id: Constraint UUID
            
        Returns:
            True if deleted, False if not found
        """
        constraint = self.get_by_id(constraint_id)
        if constraint:
            self.db.delete(constraint)
            self.db.commit()
            return True
        return False


"""
Platform Exchange Allocation Repository.
CRUD operations for platform exchange allocations.
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from app.platform.data.models.platform_exchange_allocation import PlatformExchangeAllocation


class PlatformExchangeAllocationRepository:
    """
    Repository for platform exchange allocation operations.
    
    Provides CRUD and basic query methods for platform exchange allocations.
    No business logic - data access only.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(self, allocation_data: dict) -> PlatformExchangeAllocation:
        """
        Create a new platform exchange allocation.
        
        Args:
            allocation_data: Dictionary with allocation fields
            
        Returns:
            Created PlatformExchangeAllocation instance
        """
        allocation = PlatformExchangeAllocation(**allocation_data)
        self.db.add(allocation)
        self.db.commit()
        self.db.refresh(allocation)
        return allocation
    
    def get_by_id(self, allocation_id: UUID) -> Optional[PlatformExchangeAllocation]:
        """
        Get platform exchange allocation by ID.
        
        Args:
            allocation_id: Allocation UUID
            
        Returns:
            PlatformExchangeAllocation instance or None
        """
        return self.db.query(PlatformExchangeAllocation).filter(
            PlatformExchangeAllocation.id == allocation_id
        ).first()
    
    def get_by_assessment_id(self, assessment_id: UUID) -> Optional[PlatformExchangeAllocation]:
        """
        Get exchange allocation for an assessment.
        
        Args:
            assessment_id: Assessment UUID
            
        Returns:
            PlatformExchangeAllocation instance or None
        """
        return self.db.query(PlatformExchangeAllocation).filter(
            PlatformExchangeAllocation.assessment_id == assessment_id
        ).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[PlatformExchangeAllocation]:
        """
        Get all platform exchange allocations with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of PlatformExchangeAllocation instances
        """
        return self.db.query(PlatformExchangeAllocation).offset(skip).limit(limit).all()
    
    def update(self, allocation_id: UUID, allocation_data: dict) -> Optional[PlatformExchangeAllocation]:
        """
        Update platform exchange allocation.
        
        Args:
            allocation_id: Allocation UUID
            allocation_data: Dictionary with fields to update
            
        Returns:
            Updated PlatformExchangeAllocation instance or None
        """
        allocation = self.get_by_id(allocation_id)
        if allocation:
            for key, value in allocation_data.items():
                setattr(allocation, key, value)
            self.db.commit()
            self.db.refresh(allocation)
        return allocation
    
    def update_by_assessment_id(self, assessment_id: UUID, allocation_data: dict) -> Optional[PlatformExchangeAllocation]:
        """
        Update platform exchange allocation by assessment ID.
        
        Args:
            assessment_id: Assessment UUID
            allocation_data: Dictionary with fields to update
            
        Returns:
            Updated PlatformExchangeAllocation instance or None
        """
        allocation = self.get_by_assessment_id(assessment_id)
        if allocation:
            for key, value in allocation_data.items():
                setattr(allocation, key, value)
            self.db.commit()
            self.db.refresh(allocation)
        return allocation
    
    def delete(self, allocation_id: UUID) -> bool:
        """
        Delete platform exchange allocation.
        
        Args:
            allocation_id: Allocation UUID
            
        Returns:
            True if deleted, False if not found
        """
        allocation = self.get_by_id(allocation_id)
        if allocation:
            self.db.delete(allocation)
            self.db.commit()
            return True
        return False


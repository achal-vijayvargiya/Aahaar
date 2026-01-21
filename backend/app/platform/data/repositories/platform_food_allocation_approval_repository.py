"""
Platform Food Allocation Approval Repository.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.platform.data.models.platform_food_allocation_approval import PlatformFoodAllocationApproval


class PlatformFoodAllocationApprovalRepository:
    """Repository for food allocation approval operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, data: Dict[str, Any]) -> PlatformFoodAllocationApproval:
        """Create a new approval record."""
        approval = PlatformFoodAllocationApproval(**data)
        self.db.add(approval)
        self.db.commit()
        self.db.refresh(approval)
        return approval
    
    def get_by_assessment_id(self, assessment_id: UUID) -> List[PlatformFoodAllocationApproval]:
        """Get all approvals for an assessment."""
        return self.db.query(PlatformFoodAllocationApproval).filter(
            PlatformFoodAllocationApproval.assessment_id == assessment_id
        ).all()
    
    def get_by_meal(
        self,
        assessment_id: UUID,
        day_number: str,
        meal_name: str
    ) -> Optional[PlatformFoodAllocationApproval]:
        """Get approval for a specific meal."""
        return self.db.query(PlatformFoodAllocationApproval).filter(
            and_(
                PlatformFoodAllocationApproval.assessment_id == assessment_id,
                PlatformFoodAllocationApproval.day_number == day_number,
                PlatformFoodAllocationApproval.meal_name == meal_name
            )
        ).first()
    
    def update_approval(
        self,
        assessment_id: UUID,
        day_number: str,
        meal_name: str,
        is_approved: bool,
        approved_by: Optional[UUID] = None,
        notes: Optional[Dict[str, Any]] = None
    ) -> Optional[PlatformFoodAllocationApproval]:
        """Update approval status for a meal."""
        approval = self.get_by_meal(assessment_id, day_number, meal_name)
        
        if approval:
            approval.is_approved = is_approved
            if is_approved:
                from datetime import datetime
                approval.approved_at = datetime.utcnow()
                approval.approved_by = approved_by
            if notes is not None:
                approval.notes = notes
            self.db.commit()
            self.db.refresh(approval)
        else:
            # Create new approval record
            approval = self.create({
                "assessment_id": assessment_id,
                "day_number": day_number,
                "meal_name": meal_name,
                "is_approved": is_approved,
                "approved_by": approved_by,
                "notes": notes
            })
        
        return approval
    
    def get_approval_status_map(
        self,
        assessment_id: UUID
    ) -> Dict[str, Dict[str, bool]]:
        """
        Get approval status as a map: {day_number: {meal_name: is_approved}}
        """
        approvals = self.get_by_assessment_id(assessment_id)
        status_map = {}
        
        for approval in approvals:
            if approval.day_number not in status_map:
                status_map[approval.day_number] = {}
            status_map[approval.day_number][approval.meal_name] = approval.is_approved
        
        return status_map
    
    def get_all_approved_meals(
        self,
        assessment_id: UUID
    ) -> List[Dict[str, str]]:
        """Get list of all approved meals."""
        approvals = self.db.query(PlatformFoodAllocationApproval).filter(
            and_(
                PlatformFoodAllocationApproval.assessment_id == assessment_id,
                PlatformFoodAllocationApproval.is_approved == True
            )
        ).all()
        
        return [
            {
                "day_number": approval.day_number,
                "meal_name": approval.meal_name
            }
            for approval in approvals
        ]

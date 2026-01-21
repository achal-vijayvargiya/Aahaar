"""
Knowledge Base Medical Condition Repository.
Enhanced CRUD and query operations for KB medical conditions.
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.platform.data.models.kb_medical_condition import KBMedicalCondition


class KBMedicalConditionRepository:
    """
    Repository for KB medical condition operations.
    
    Provides CRUD and enhanced query methods for KB medical conditions.
    Includes retrieval logic for lab-based condition matching.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(self, condition_data: dict) -> KBMedicalCondition:
        """
        Create a new KB medical condition.
        
        Args:
            condition_data: Dictionary with condition fields
            
        Returns:
            Created KBMedicalCondition instance
        """
        condition = KBMedicalCondition(**condition_data)
        self.db.add(condition)
        self.db.commit()
        self.db.refresh(condition)
        return condition
    
    def get_by_id(self, condition_id: UUID) -> Optional[KBMedicalCondition]:
        """
        Get KB medical condition by UUID.
        
        Args:
            condition_id: Condition UUID
            
        Returns:
            KBMedicalCondition instance or None
        """
        return self.db.query(KBMedicalCondition).filter(
            KBMedicalCondition.id == condition_id
        ).first()
    
    def get_by_condition_id(self, condition_id: str) -> Optional[KBMedicalCondition]:
        """
        Get KB medical condition by condition_id (string identifier).
        
        Args:
            condition_id: Condition string identifier (e.g., "type_2_diabetes")
            
        Returns:
            KBMedicalCondition instance or None
        """
        return self.db.query(KBMedicalCondition).filter(
            KBMedicalCondition.condition_id == condition_id,
            KBMedicalCondition.status == 'active'
        ).first()
    
    def get_all(self, skip: int = 0, limit: int = 100, active_only: bool = True) -> List[KBMedicalCondition]:
        """
        Get all KB medical conditions with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            active_only: If True, only return active conditions
            
        Returns:
            List of KBMedicalCondition instances
        """
        query = self.db.query(KBMedicalCondition)
        if active_only:
            query = query.filter(KBMedicalCondition.status == 'active')
        return query.offset(skip).limit(limit).all()
    
    def get_by_category(self, category: str, active_only: bool = True) -> List[KBMedicalCondition]:
        """
        Get all medical conditions in a specific category.
        
        Args:
            category: Condition category (e.g., "metabolic", "cardiovascular")
            active_only: If True, only return active conditions
            
        Returns:
            List of KBMedicalCondition instances
        """
        query = self.db.query(KBMedicalCondition).filter(
            KBMedicalCondition.category == category
        )
        if active_only:
            query = query.filter(KBMedicalCondition.status == 'active')
        return query.all()
    
    def find_by_labs(self, labs: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Find conditions matching lab values.
        
        Args:
            labs: Dictionary of lab_name -> lab_value (e.g., {"HbA1c": 7.5, "FBS": 140})
            
        Returns:
            List of dictionaries with:
            - condition: KBMedicalCondition instance
            - matched_labs: Dict of matched lab values with severity
            - overall_severity: Overall severity (mild/moderate/severe)
        """
        all_conditions = self.get_all(active_only=True)
        matches = []
        
        for condition in all_conditions:
            if not condition.severity_thresholds:
                continue
                
            matched_labs = {}
            max_severity_level = 0  # 1=mild, 2=moderate, 3=severe
            
            for lab_name, lab_value in labs.items():
                if not isinstance(lab_value, (int, float)):
                    continue
                    
                # Check if this lab is in the condition's thresholds
                if lab_name in condition.severity_thresholds:
                    thresholds = condition.severity_thresholds[lab_name]
                    severity_info = self._check_lab_threshold(lab_value, thresholds)
                    
                    if severity_info:
                        matched_labs[lab_name] = {
                            "value": lab_value,
                            "severity": severity_info["severity"],
                            "threshold": severity_info["threshold"]
                        }
                        # Track max severity
                        severity_level = {"mild": 1, "moderate": 2, "severe": 3}.get(severity_info["severity"], 0)
                        max_severity_level = max(max_severity_level, severity_level)
            
            if matched_labs:
                severity_map = {1: "mild", 2: "moderate", 3: "severe"}
                matches.append({
                    "condition": condition,
                    "matched_labs": matched_labs,
                    "overall_severity": severity_map.get(max_severity_level, "unknown")
                })
        
        return matches
    
    def _check_lab_threshold(self, value: float, thresholds: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Check if lab value matches any threshold and return severity.
        
        Args:
            value: Lab value
            thresholds: Threshold dictionary with mild/moderate/severe ranges
            
        Returns:
            Dict with severity and threshold info, or None if no match
        """
        # Check severe first (highest priority)
        if "severe" in thresholds:
            severe = thresholds["severe"]
            if isinstance(severe, dict):
                min_val = severe.get("min")
                max_val = severe.get("max")
                if min_val is not None and value >= min_val:
                    if max_val is None or value <= max_val:
                        return {"severity": "severe", "threshold": severe}
        
        # Check moderate
        if "moderate" in thresholds:
            moderate = thresholds["moderate"]
            if isinstance(moderate, dict):
                min_val = moderate.get("min")
                max_val = moderate.get("max")
                if min_val is not None and value >= min_val:
                    if max_val is None or value <= max_val:
                        return {"severity": "moderate", "threshold": moderate}
        
        # Check mild
        if "mild" in thresholds:
            mild = thresholds["mild"]
            if isinstance(mild, dict):
                min_val = mild.get("min")
                max_val = mild.get("max")
                if min_val is not None and value >= min_val:
                    if max_val is None or value <= max_val:
                        return {"severity": "mild", "threshold": mild}
        
        return None
    
    def update(self, condition_id: UUID, condition_data: dict) -> Optional[KBMedicalCondition]:
        """
        Update KB medical condition.
        
        Args:
            condition_id: Condition UUID
            condition_data: Dictionary with fields to update
            
        Returns:
            Updated KBMedicalCondition instance or None
        """
        condition = self.get_by_id(condition_id)
        if condition:
            for key, value in condition_data.items():
                setattr(condition, key, value)
            self.db.commit()
            self.db.refresh(condition)
        return condition
    
    def update_by_condition_id(self, condition_id: str, condition_data: dict) -> Optional[KBMedicalCondition]:
        """
        Update KB medical condition by condition_id string.
        
        Args:
            condition_id: Condition string identifier
            condition_data: Dictionary with fields to update
            
        Returns:
            Updated KBMedicalCondition instance or None
        """
        condition = self.get_by_condition_id(condition_id)
        if condition:
            for key, value in condition_data.items():
                setattr(condition, key, value)
            self.db.commit()
            self.db.refresh(condition)
        return condition
    
    def delete(self, condition_id: UUID) -> bool:
        """
        Delete KB medical condition.
        
        Args:
            condition_id: Condition UUID
            
        Returns:
            True if deleted, False if not found
        """
        condition = self.get_by_id(condition_id)
        if condition:
            self.db.delete(condition)
            self.db.commit()
            return True
        return False


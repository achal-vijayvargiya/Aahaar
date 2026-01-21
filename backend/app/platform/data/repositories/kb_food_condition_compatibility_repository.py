"""
Knowledge Base Food-Condition Compatibility Repository.
CRUD and query operations for KB food-condition compatibility.
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_


from app.platform.data.models.kb_food_condition_compatibility import KBFoodConditionCompatibility


class KBFoodConditionCompatibilityRepository:
    """
    Repository for KB food-condition compatibility operations.
    
    Provides CRUD and query methods for food-condition compatibility matrix.
    Defines which foods are safe, caution, avoid, or contraindicated for conditions.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(self, compatibility_data: dict):
        """
        Create a new KB food-condition compatibility record.
        
        Args:
            compatibility_data: Dictionary with compatibility fields
            
        Returns:
            Created KBFoodConditionCompatibility instance
        """
        compatibility = KBFoodConditionCompatibility(**compatibility_data)
        self.db.add(compatibility)
        self.db.commit()
        self.db.refresh(compatibility)
        return compatibility
    
    def get_by_id(self, compatibility_id: UUID):
        """
        Get KB food-condition compatibility by UUID.
        
        Args:
            compatibility_id: Compatibility UUID
            
        Returns:
            KBFoodConditionCompatibility instance or None
        """
        return self.db.query(KBFoodConditionCompatibility).filter(
            KBFoodConditionCompatibility.id == compatibility_id
        ).first()
    
    def get_by_food_and_condition(
        self,
        food_id: str,
        condition_id: str,
        active_only: bool = True
    ):
        """
        Get compatibility record for a specific food and condition.
        
        Args:
            food_id: Food ID
            condition_id: Condition ID
            active_only: If True, only return active records
            
        Returns:
            KBFoodConditionCompatibility instance or None
        """
        if KBFoodConditionCompatibility is None:
            raise ImportError("KBFoodConditionCompatibility model not yet created")
        query = self.db.query(KBFoodConditionCompatibility).filter(
            KBFoodConditionCompatibility.food_id == food_id,
            KBFoodConditionCompatibility.condition_id == condition_id
        )
        if active_only:
            query = query.filter(KBFoodConditionCompatibility.status == 'active')
        return query.first()
    
    def get_all(self, skip: int = 0, limit: int = 100, active_only: bool = True) -> List:
        """
        Get all KB food-condition compatibility records with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            active_only: If True, only return active records
            
        Returns:
            List of KBFoodConditionCompatibility instances
        """
        if KBFoodConditionCompatibility is None:
            raise ImportError("KBFoodConditionCompatibility model not yet created")
        query = self.db.query(KBFoodConditionCompatibility)
        if active_only:
            query = query.filter(KBFoodConditionCompatibility.status == 'active')
        return query.offset(skip).limit(limit).all()
    
    def get_by_food_id(
        self,
        food_id: str,
        active_only: bool = True
    ) -> List:
        """
        Get all compatibility records for a food.
        
        Args:
            food_id: Food ID
            active_only: If True, only return active records
            
        Returns:
            List of KBFoodConditionCompatibility instances
        """
        if KBFoodConditionCompatibility is None:
            raise ImportError("KBFoodConditionCompatibility model not yet created")
        query = self.db.query(KBFoodConditionCompatibility).filter(
            KBFoodConditionCompatibility.food_id == food_id
        )
        if active_only:
            query = query.filter(KBFoodConditionCompatibility.status == 'active')
        return query.all()
    
    def get_by_condition_id(
        self,
        condition_id: str,
        compatibility: Optional[str] = None,
        active_only: bool = True
    ) -> List:
        """
        Get all compatibility records for a condition.
        
        Args:
            condition_id: Condition ID
            compatibility: Optional filter by compatibility type (safe, caution, avoid, contraindicated)
            active_only: If True, only return active records
            
        Returns:
            List of KBFoodConditionCompatibility instances
        """
        if KBFoodConditionCompatibility is None:
            raise ImportError("KBFoodConditionCompatibility model not yet created")
        query = self.db.query(KBFoodConditionCompatibility).filter(
            KBFoodConditionCompatibility.condition_id == condition_id
        )
        if compatibility:
            query = query.filter(
                KBFoodConditionCompatibility.compatibility == compatibility
            )
        if active_only:
            query = query.filter(KBFoodConditionCompatibility.status == 'active')
        return query.all()
    
    def get_safe_foods(
        self,
        condition_id: str,
        severity: Optional[str] = None,
        active_only: bool = True
    ) -> List[str]:
        """
        Get list of safe food IDs for a condition.
        
        Args:
            condition_id: Condition ID
            severity: Optional condition severity (mild, moderate, severe) for severity modifiers
            active_only: If True, only return active records
            
        Returns:
            List of food IDs that are safe for the condition
        """
        records = self.get_by_condition_id(condition_id, compatibility="safe", active_only=active_only)
        
        safe_foods = []
        for record in records:
            # Check severity modifier if provided
            if severity and record.severity_modifier:
                # If severity modifier exists, check if it changes compatibility
                if severity in record.severity_modifier:
                    actual_compatibility = record.severity_modifier[severity]
                    if actual_compatibility == "safe":
                        safe_foods.append(record.food_id)
                else:
                    # No severity modifier, use base compatibility
                    safe_foods.append(record.food_id)
            else:
                # No severity modifier, use base compatibility
                safe_foods.append(record.food_id)
        
        return safe_foods
    
    def get_unsafe_foods(
        self,
        condition_id: str,
        severity: Optional[str] = None,
        active_only: bool = True
    ) -> List[str]:
        """
        Get list of unsafe food IDs for a condition (avoid or contraindicated).
        
        Args:
            condition_id: Condition ID
            severity: Optional condition severity for severity modifiers
            active_only: If True, only return active records
            
        Returns:
            List of food IDs that should be avoided for the condition
        """
        avoid_records = self.get_by_condition_id(condition_id, compatibility="avoid", active_only=active_only)
        contraindicated_records = self.get_by_condition_id(condition_id, compatibility="contraindicated", active_only=active_only)
        
        unsafe_foods = []
        
        for record in avoid_records + contraindicated_records:
            # Check severity modifier if provided
            if severity and record.severity_modifier:
                if severity in record.severity_modifier:
                    actual_compatibility = record.severity_modifier[severity]
                    if actual_compatibility in ["avoid", "contraindicated"]:
                        unsafe_foods.append(record.food_id)
                else:
                    unsafe_foods.append(record.food_id)
            else:
                unsafe_foods.append(record.food_id)
        
        return unsafe_foods
    
    def get_caution_foods(
        self,
        condition_id: str,
        severity: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get list of caution foods with portion limits for a condition.
        
        Args:
            condition_id: Condition ID
            severity: Optional condition severity for severity modifiers
            active_only: If True, only return active records
            
        Returns:
            List of dictionaries with food_id and portion_limit information
        """
        records = self.get_by_condition_id(condition_id, compatibility="caution", active_only=active_only)
        
        caution_foods = []
        for record in records:
            # Check severity modifier if provided
            include = True
            if severity and record.severity_modifier:
                if severity in record.severity_modifier:
                    actual_compatibility = record.severity_modifier[severity]
                    if actual_compatibility not in ["caution", "safe"]:
                        include = False
            
            if include:
                caution_foods.append({
                    "food_id": record.food_id,
                    "portion_limit": record.portion_limit,
                    "preparation_notes": record.preparation_notes
                })
        
        return caution_foods
    
    def check_compatibility(
        self,
        food_id: str,
        condition_id: str,
        severity: Optional[str] = None,
        active_only: bool = True
    ) -> Dict[str, Any]:
        """
        Check compatibility of a food with a condition.
        
        Args:
            food_id: Food ID
            condition_id: Condition ID
            severity: Optional condition severity for severity modifiers
            active_only: If True, only check active records
            
        Returns:
            Dictionary with:
            - compatibility: safe, caution, avoid, contraindicated, or unknown
            - portion_limit: Portion limit if applicable
            - preparation_notes: Preparation notes if applicable
            - evidence: Evidence source if applicable
        """
        record = self.get_by_food_and_condition(food_id, condition_id, active_only=active_only)
        
        if not record:
            return {
                "compatibility": "unknown",
                "portion_limit": None,
                "preparation_notes": None,
                "evidence": None
            }
        
        # Check severity modifier if provided
        actual_compatibility = record.compatibility
        if severity and record.severity_modifier:
            if severity in record.severity_modifier:
                actual_compatibility = record.severity_modifier[severity]
        
        return {
            "compatibility": actual_compatibility,
            "portion_limit": record.portion_limit,
            "preparation_notes": record.preparation_notes,
            "evidence": record.evidence
        }
    
    def filter_foods_by_conditions(
        self,
        food_ids: List[str],
        condition_ids: List[str],
        severity_map: Optional[Dict[str, str]] = None,
        active_only: bool = True
    ) -> Dict[str, List[str]]:
        """
        Filter foods by multiple conditions.
        
        Args:
            food_ids: List of food IDs to filter
            condition_ids: List of condition IDs
            severity_map: Optional map of condition_id -> severity
            active_only: If True, only check active records
            
        Returns:
            Dictionary with:
            - safe: List of safe food IDs
            - caution: List of caution food IDs
            - avoid: List of avoid food IDs
            - contraindicated: List of contraindicated food IDs
        """
        result = {
            "safe": [],
            "caution": [],
            "avoid": [],
            "contraindicated": []
        }
        
        for food_id in food_ids:
            compatibilities = []
            for condition_id in condition_ids:
                severity = severity_map.get(condition_id) if severity_map else None
                compat = self.check_compatibility(food_id, condition_id, severity, active_only)
                compatibilities.append(compat["compatibility"])
            
            # Determine overall compatibility (most restrictive wins)
            if "contraindicated" in compatibilities:
                result["contraindicated"].append(food_id)
            elif "avoid" in compatibilities:
                result["avoid"].append(food_id)
            elif "caution" in compatibilities:
                result["caution"].append(food_id)
            elif all(c == "safe" for c in compatibilities):
                result["safe"].append(food_id)
            else:
                # Unknown or mixed - default to caution
                result["caution"].append(food_id)
        
        return result
    
    def update(self, compatibility_id: UUID, compatibility_data: dict):
        """
        Update KB food-condition compatibility record.
        
        Args:
            compatibility_id: Compatibility UUID
            compatibility_data: Dictionary with fields to update
            
        Returns:
            Updated KBFoodConditionCompatibility instance or None
        """
        compatibility = self.get_by_id(compatibility_id)
        if compatibility:
            for key, value in compatibility_data.items():
                setattr(compatibility, key, value)
            self.db.commit()
            self.db.refresh(compatibility)
        return compatibility
    
    def delete(self, compatibility_id: UUID) -> bool:
        """
        Delete KB food-condition compatibility record.
        
        Args:
            compatibility_id: Compatibility UUID
            
        Returns:
            True if deleted, False if not found
        """
        compatibility = self.get_by_id(compatibility_id)
        if compatibility:
            self.db.delete(compatibility)
            self.db.commit()
            return True
        return False


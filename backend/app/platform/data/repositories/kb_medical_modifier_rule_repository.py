"""
Knowledge Base Medical Modifier Rule Repository.
CRUD and query operations for KB medical modifier rules.
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc


from app.platform.data.models.kb_medical_modifier_rule import KBMedicalModifierRule


class KBMedicalModifierRuleRepository:
    """
    Repository for KB medical modifier rule operations.
    
    Provides CRUD and query methods for medical modifier rules.
    These rules define how medical conditions modify exchange allocation and meal structure.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(self, modifier_data: dict):
        """
        Create a new KB medical modifier rule.
        
        Args:
            modifier_data: Dictionary with modifier fields
            
        Returns:
            Created KBMedicalModifierRule instance
        """
        modifier = KBMedicalModifierRule(**modifier_data)
        self.db.add(modifier)
        self.db.commit()
        self.db.refresh(modifier)
        return modifier
    
    def get_by_id(self, modifier_id: UUID):
        """
        Get KB medical modifier rule by UUID.
        
        Args:
            modifier_id: Modifier UUID
            
        Returns:
            KBMedicalModifierRule instance or None
        """
        return self.db.query(KBMedicalModifierRule).filter(
            KBMedicalModifierRule.id == modifier_id
        ).first()
    
    def get_by_modifier_id(self, modifier_id: str, active_only: bool = True):
        """
        Get KB medical modifier rule by modifier_id (string identifier).
        
        Args:
            modifier_id: Modifier string identifier
            active_only: If True, only return active modifiers
            
        Returns:
            KBMedicalModifierRule instance or None
        """
        if KBMedicalModifierRule is None:
            raise ImportError("KBMedicalModifierRule model not yet created")
        query = self.db.query(KBMedicalModifierRule).filter(
            KBMedicalModifierRule.modifier_id == modifier_id
        )
        if active_only:
            query = query.filter(KBMedicalModifierRule.status == 'active')
        return query.first()
    
    def get_all(self, skip: int = 0, limit: int = 100, active_only: bool = True) -> List:
        """
        Get all KB medical modifier rules with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            active_only: If True, only return active modifiers
            
        Returns:
            List of KBMedicalModifierRule instances
        """
        if KBMedicalModifierRule is None:
            raise ImportError("KBMedicalModifierRule model not yet created")
        query = self.db.query(KBMedicalModifierRule)
        if active_only:
            query = query.filter(KBMedicalModifierRule.status == 'active')
        return query.order_by(desc(KBMedicalModifierRule.priority)).offset(skip).limit(limit).all()
    
    def get_by_condition(
        self,
        condition_id: str,
        category_id: Optional[str] = None,
        meal_name: Optional[str] = None,
        active_only: bool = True
    ) -> List:
        """
        Get medical modifier rules for a condition.
        
        Args:
            condition_id: Medical condition ID
            category_id: Optional exchange category ID to filter
            meal_name: Optional meal name to filter
            active_only: If True, only return active modifiers
            
        Returns:
            List of KBMedicalModifierRule instances, sorted by priority
        """
        if KBMedicalModifierRule is None:
            raise ImportError("KBMedicalModifierRule model not yet created")
        query = self.db.query(KBMedicalModifierRule).filter(
            KBMedicalModifierRule.condition_id == condition_id
        )
        
        if category_id:
            query = query.filter(
                (KBMedicalModifierRule.category_id == category_id) |
                (KBMedicalModifierRule.category_id.is_(None))
            )
        
        if meal_name:
            query = query.filter(
                (KBMedicalModifierRule.applies_to_meals.contains([meal_name])) |
                (KBMedicalModifierRule.applies_to_meals.is_(None))
            )
        
        if active_only:
            query = query.filter(KBMedicalModifierRule.status == 'active')
        
        return query.order_by(desc(KBMedicalModifierRule.priority)).all()
    
    def get_by_category(self, category_id: str, active_only: bool = True) -> List:
        """
        Get medical modifier rules for an exchange category.
        
        Args:
            category_id: Exchange category ID
            active_only: If True, only return active modifiers
            
        Returns:
            List of KBMedicalModifierRule instances
        """
        if KBMedicalModifierRule is None:
            raise ImportError("KBMedicalModifierRule model not yet created")
        query = self.db.query(KBMedicalModifierRule).filter(
            (KBMedicalModifierRule.category_id == category_id) |
            (KBMedicalModifierRule.applies_to_exchange_categories.contains([category_id]))
        )
        if active_only:
            query = query.filter(KBMedicalModifierRule.status == 'active')
        return query.order_by(desc(KBMedicalModifierRule.priority)).all()
    
    def get_by_meal(self, meal_name: str, active_only: bool = True) -> List:
        """
        Get medical modifier rules for a specific meal.
        
        Args:
            meal_name: Meal name (e.g., "breakfast", "lunch")
            active_only: If True, only return active modifiers
            
        Returns:
            List of KBMedicalModifierRule instances
        """
        if KBMedicalModifierRule is None:
            raise ImportError("KBMedicalModifierRule model not yet created")
        query = self.db.query(KBMedicalModifierRule).filter(
            (KBMedicalModifierRule.applies_to_meals.contains([meal_name])) |
            (KBMedicalModifierRule.applies_to_meals.is_(None))
        )
        if active_only:
            query = query.filter(KBMedicalModifierRule.status == 'active')
        return query.order_by(desc(KBMedicalModifierRule.priority)).all()
    
    def get_modifiers_for_conditions(
        self,
        condition_ids: List[str],
        category_id: Optional[str] = None,
        meal_name: Optional[str] = None,
        active_only: bool = True
    ) -> List:
        """
        Get all modifiers for multiple conditions.
        
        Args:
            condition_ids: List of condition IDs
            category_id: Optional exchange category ID to filter
            meal_name: Optional meal name to filter
            active_only: If True, only return active modifiers
            
        Returns:
            List of KBMedicalModifierRule instances, sorted by priority
        """
        if KBMedicalModifierRule is None:
            raise ImportError("KBMedicalModifierRule model not yet created")
        from sqlalchemy import or_
        
        conditions = [KBMedicalModifierRule.condition_id == cid for cid in condition_ids]
        query = self.db.query(KBMedicalModifierRule).filter(or_(*conditions))
        
        if category_id:
            query = query.filter(
                (KBMedicalModifierRule.category_id == category_id) |
                (KBMedicalModifierRule.category_id.is_(None))
            )
        
        if meal_name:
            query = query.filter(
                (KBMedicalModifierRule.applies_to_meals.contains([meal_name])) |
                (KBMedicalModifierRule.applies_to_meals.is_(None))
            )
        
        if active_only:
            query = query.filter(KBMedicalModifierRule.status == 'active')
        
        return query.order_by(desc(KBMedicalModifierRule.priority)).all()
    
    def apply_modifiers(
        self,
        modifiers: List,
        base_value: float,
        category_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Apply modifiers to a base value.
        
        Args:
            modifiers: List of KBMedicalModifierRule instances
            base_value: Base value to modify
            category_id: Optional category ID for filtering
            
        Returns:
            Dictionary with:
            - modified_value: Final value after applying modifiers
            - applied_modifiers: List of modifiers that were applied
            - modifications: List of modification details
        """
        if not modifiers:
            return {
                "modified_value": base_value,
                "applied_modifiers": [],
                "modifications": []
            }
        
        # Sort by priority (highest first)
        sorted_modifiers = sorted(modifiers, key=lambda m: m.priority, reverse=True)
        
        current_value = base_value
        applied_modifiers = []
        modifications = []
        
        for modifier in sorted_modifiers:
            # Check if modifier applies to this category
            if category_id:
                if modifier.category_id and modifier.category_id != category_id:
                    continue
                if modifier.applies_to_exchange_categories:
                    if category_id not in modifier.applies_to_exchange_categories:
                        continue
            
            modification_value = modifier.modification_value
            mod_type = modifier.modification_type
            
            if mod_type == "restrict":
                # Reduce value
                if "percent_change" in modification_value:
                    change = current_value * (modification_value["percent_change"] / 100)
                    current_value = max(0, current_value - abs(change))
                elif "absolute_change" in modification_value:
                    current_value = max(0, current_value - abs(modification_value["absolute_change"]))
            
            elif mod_type == "increase":
                # Increase value
                if "percent_change" in modification_value:
                    change = current_value * (modification_value["percent_change"] / 100)
                    current_value += abs(change)
                elif "absolute_change" in modification_value:
                    current_value += abs(modification_value["absolute_change"])
            
            elif mod_type == "replace":
                # Replace with specific value
                if "value" in modification_value:
                    current_value = modification_value["value"]
            
            applied_modifiers.append(modifier.modifier_id)
            modifications.append({
                "modifier_id": modifier.modifier_id,
                "type": mod_type,
                "value_before": base_value if not modifications else modifications[-1].get("value_after", base_value),
                "value_after": current_value,
                "change": current_value - (base_value if not modifications else modifications[-1].get("value_after", base_value))
            })
        
        return {
            "modified_value": current_value,
            "applied_modifiers": applied_modifiers,
            "modifications": modifications
        }
    
    def update(self, modifier_id: UUID, modifier_data: dict):
        """
        Update KB medical modifier rule.
        
        Args:
            modifier_id: Modifier UUID
            modifier_data: Dictionary with fields to update
            
        Returns:
            Updated KBMedicalModifierRule instance or None
        """
        modifier = self.get_by_id(modifier_id)
        if modifier:
            for key, value in modifier_data.items():
                setattr(modifier, key, value)
            self.db.commit()
            self.db.refresh(modifier)
        return modifier
    
    def update_by_modifier_id(self, modifier_id: str, modifier_data: dict):
        """
        Update KB medical modifier rule by modifier_id string.
        
        Args:
            modifier_id: Modifier string identifier
            modifier_data: Dictionary with fields to update
            
        Returns:
            Updated KBMedicalModifierRule instance or None
        """
        modifier = self.get_by_modifier_id(modifier_id, active_only=False)
        if modifier:
            for key, value in modifier_data.items():
                setattr(modifier, key, value)
            self.db.commit()
            self.db.refresh(modifier)
        return modifier
    
    def delete(self, modifier_id: UUID) -> bool:
        """
        Delete KB medical modifier rule.
        
        Args:
            modifier_id: Modifier UUID
            
        Returns:
            True if deleted, False if not found
        """
        modifier = self.get_by_id(modifier_id)
        if modifier:
            self.db.delete(modifier)
            self.db.commit()
            return True
        return False


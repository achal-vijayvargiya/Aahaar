"""
Knowledge Base MNT Rule Repository.
Enhanced CRUD and query operations for KB MNT rules.
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from app.platform.data.models.kb_mnt_rule import KBMNTRule


class KBMNTRuleRepository:
    """
    Repository for KB MNT rule operations.
    
    Provides CRUD and enhanced query methods for KB MNT rules.
    Includes retrieval logic for finding rules by diagnosis and priority.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(self, rule_data: dict) -> KBMNTRule:
        """
        Create a new KB MNT rule.
        
        Args:
            rule_data: Dictionary with rule fields
            
        Returns:
            Created KBMNTRule instance
        """
        rule = KBMNTRule(**rule_data)
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule
    
    def get_by_id(self, rule_id: UUID) -> Optional[KBMNTRule]:
        """
        Get KB MNT rule by UUID.
        
        Args:
            rule_id: Rule UUID
            
        Returns:
            KBMNTRule instance or None
        """
        return self.db.query(KBMNTRule).filter(
            KBMNTRule.id == rule_id
        ).first()
    
    def get_by_rule_id(self, rule_id: str, active_only: bool = True) -> Optional[KBMNTRule]:
        """
        Get KB MNT rule by rule_id (string identifier).
        
        Args:
            rule_id: Rule string identifier (e.g., "mnt_carb_restriction_diabetes")
            active_only: If True, only return active rules
            
        Returns:
            KBMNTRule instance or None
        """
        query = self.db.query(KBMNTRule).filter(
            KBMNTRule.rule_id == rule_id
        )
        if active_only:
            query = query.filter(KBMNTRule.status == 'active')
        return query.first()
    
    def get_all(self, skip: int = 0, limit: int = 100, active_only: bool = True) -> List[KBMNTRule]:
        """
        Get all KB MNT rules with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            active_only: If True, only return active rules
            
        Returns:
            List of KBMNTRule instances
        """
        query = self.db.query(KBMNTRule)
        if active_only:
            query = query.filter(KBMNTRule.status == 'active')
        return query.order_by(desc(KBMNTRule.priority_level)).offset(skip).limit(limit).all()
    
    def get_by_diagnosis(self, diagnosis_id: str, active_only: bool = True) -> List[KBMNTRule]:
        """
        Get MNT rules that apply to a specific diagnosis.
        
        Args:
            diagnosis_id: Diagnosis ID (medical condition or nutrition diagnosis)
            active_only: If True, only return active rules
            
        Returns:
            List of KBMNTRule instances, sorted by priority (highest first)
        """
        query = self.db.query(KBMNTRule).filter(
            KBMNTRule.applies_to_diagnoses.contains([diagnosis_id])
        )
        if active_only:
            query = query.filter(KBMNTRule.status == 'active')
        return query.order_by(desc(KBMNTRule.priority_level)).all()
    
    def get_by_priority(self, priority_level: int, active_only: bool = True) -> List[KBMNTRule]:
        """
        Get MNT rules by priority level.
        
        Args:
            priority_level: Priority level (1-4, where 4=critical)
            active_only: If True, only return active rules
            
        Returns:
            List of KBMNTRule instances
        """
        query = self.db.query(KBMNTRule).filter(
            KBMNTRule.priority_level == priority_level
        )
        if active_only:
            query = query.filter(KBMNTRule.status == 'active')
        return query.all()
    
    def get_by_priority_label(self, priority_label: str, active_only: bool = True) -> List[KBMNTRule]:
        """
        Get MNT rules by priority label.
        
        Args:
            priority_label: Priority label ("critical", "high", "medium", "low")
            active_only: If True, only return active rules
            
        Returns:
            List of KBMNTRule instances
        """
        query = self.db.query(KBMNTRule).filter(
            KBMNTRule.priority_label == priority_label
        )
        if active_only:
            query = query.filter(KBMNTRule.status == 'active')
        return query.order_by(desc(KBMNTRule.priority_level)).all()
    
    def get_rules_for_diagnoses(
        self,
        diagnosis_ids: List[str],
        active_only: bool = True
    ) -> List[KBMNTRule]:
        """
        Get all MNT rules that apply to any of the given diagnoses.
        
        Args:
            diagnosis_ids: List of diagnosis IDs
            active_only: If True, only return active rules
            
        Returns:
            List of KBMNTRule instances, sorted by priority (highest first)
        """
        query = self.db.query(KBMNTRule)
        
        # Filter rules that apply to any of the diagnoses
        conditions = []
        for diagnosis_id in diagnosis_ids:
            conditions.append(KBMNTRule.applies_to_diagnoses.contains([diagnosis_id]))
        
        if conditions:
            from sqlalchemy import or_
            query = query.filter(or_(*conditions))
        
        if active_only:
            query = query.filter(KBMNTRule.status == 'active')
        
        return query.order_by(desc(KBMNTRule.priority_level)).all()
    
    def resolve_conflicts(self, rules: List[KBMNTRule]) -> Dict[str, Any]:
        """
        Resolve conflicts between multiple MNT rules.
        
        Args:
            rules: List of KBMNTRule instances that may conflict
            
        Returns:
            Dictionary with:
            - merged_constraints: Merged macro/micro constraints
            - merged_exclusions: Merged food exclusions
            - rule_ids_used: List of rule IDs that were applied
            - conflicts: List of conflicts that were resolved
        """
        if not rules:
            return {
                "merged_constraints": {},
                "merged_exclusions": [],
                "rule_ids_used": [],
                "conflicts": []
            }
        
        # Sort by priority (highest first)
        sorted_rules = sorted(rules, key=lambda r: r.priority_level, reverse=True)
        
        merged_macro_constraints = {}
        merged_micro_constraints = {}
        merged_exclusions = set()
        rule_ids_used = []
        conflicts = []
        
        for rule in sorted_rules:
            rule_ids_used.append(rule.rule_id)
            
            # Merge macro constraints (highest priority wins)
            if rule.macro_constraints:
                for key, value in rule.macro_constraints.items():
                    if key not in merged_macro_constraints:
                        merged_macro_constraints[key] = value
                    else:
                        # Conflict detected - higher priority wins
                        conflicts.append({
                            "rule_id": rule.rule_id,
                            "constraint_type": "macro",
                            "constraint_key": key,
                            "resolution": "higher_priority_wins"
                        })
                        merged_macro_constraints[key] = value
            
            # Merge micro constraints
            if rule.micro_constraints:
                for key, value in rule.micro_constraints.items():
                    if key not in merged_micro_constraints:
                        merged_micro_constraints[key] = value
                    else:
                        conflicts.append({
                            "rule_id": rule.rule_id,
                            "constraint_type": "micro",
                            "constraint_key": key,
                            "resolution": "higher_priority_wins"
                        })
                        merged_micro_constraints[key] = value
            
            # Merge food exclusions (union)
            if rule.food_exclusions:
                merged_exclusions.update(rule.food_exclusions)
        
        return {
            "merged_constraints": {
                "macro": merged_macro_constraints,
                "micro": merged_micro_constraints
            },
            "merged_exclusions": list(merged_exclusions),
            "rule_ids_used": rule_ids_used,
            "conflicts": conflicts
        }
    
    def update(self, rule_id: UUID, rule_data: dict) -> Optional[KBMNTRule]:
        """
        Update KB MNT rule.
        
        Args:
            rule_id: Rule UUID
            rule_data: Dictionary with fields to update
            
        Returns:
            Updated KBMNTRule instance or None
        """
        rule = self.get_by_id(rule_id)
        if rule:
            for key, value in rule_data.items():
                setattr(rule, key, value)
            self.db.commit()
            self.db.refresh(rule)
        return rule
    
    def update_by_rule_id(self, rule_id: str, rule_data: dict) -> Optional[KBMNTRule]:
        """
        Update KB MNT rule by rule_id string.
        
        Args:
            rule_id: Rule string identifier
            rule_data: Dictionary with fields to update
            
        Returns:
            Updated KBMNTRule instance or None
        """
        rule = self.get_by_rule_id(rule_id, active_only=False)
        if rule:
            for key, value in rule_data.items():
                setattr(rule, key, value)
            self.db.commit()
            self.db.refresh(rule)
        return rule
    
    def delete(self, rule_id: UUID) -> bool:
        """
        Delete KB MNT rule.
        
        Args:
            rule_id: Rule UUID
            
        Returns:
            True if deleted, False if not found
        """
        rule = self.get_by_id(rule_id)
        if rule:
            self.db.delete(rule)
            self.db.commit()
            return True
        return False


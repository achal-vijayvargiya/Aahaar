"""
MNT (Medical Nutrition Therapy) Engine.
Enforces medical nutrition rules and constraints.
"""
from typing import Dict, List, Any, Optional
from uuid import UUID

from app.platform.core.context import DiagnosisContext, MNTContext
from app.platform.engines.mnt_engine.kb_mnt_rules import (
    get_mnt_rule,
    get_rules_for_diagnosis,
    get_priority_level
)


class MNTEngine:
    """
    MNT (Medical Nutrition Therapy) Engine.
    
    Responsibility:
    - Enforce medical nutrition therapy rules based on diagnoses
    - Select applicable MNT rules from knowledge base JSON file
    - Resolve conflicts between multiple rules
    - Apply priority handling for competing constraints
    
    Inputs:
    - Medical conditions
    - Nutrition diagnoses
    - Client profile
    
    Outputs:
    - Macro constraints (carbohydrates, proteins, fats)
    - Micro constraints (vitamins, minerals)
    - Food exclusions list
    - Rule IDs used (for explainability)
    
    Rules:
    - This engine CANNOT be bypassed
    - All rules must reference knowledge base MNT rule IDs
    - Conflicts must be resolved deterministically
    - Priority handling must be explicit
    - All rules loaded dynamically from KB JSON file
    """
    
    def __init__(self):
        """Initialize MNT engine."""
        pass
    
    def process_diagnoses(self, diagnosis_context: DiagnosisContext) -> MNTContext:
        """
        Process diagnoses and generate MNT constraints.
        
        Args:
            diagnosis_context: Diagnosis context with medical conditions and nutrition diagnoses
            
        Returns:
            MNTContext with macro constraints, micro constraints, and food exclusions
            
        Note:
            This method:
            1. Selects applicable MNT rules based on diagnoses
            2. Resolves conflicts between rules
            3. Applies priority handling
            4. Generates constraints that cannot be bypassed
            
        Raises:
            ValueError: If assessment_id is missing from diagnosis context
        """
        if not diagnosis_context.assessment_id:
            raise ValueError("assessment_id is required in DiagnosisContext")
        
        # Extract diagnoses
        medical_conditions = diagnosis_context.medical_conditions or []
        nutrition_diagnoses = diagnosis_context.nutrition_diagnoses or []
        
        # NEW: Filter out invalid/ineligible diagnoses (Bug 3.1)
        # Only apply MNT rules for valid diagnoses (severity_score > 0)
        valid_medical_conditions = [
            c for c in medical_conditions 
            if c.get("diagnosis_id") and c.get("severity_score", 0) > 0
        ]
        valid_nutrition_diagnoses = [
            d for d in nutrition_diagnoses 
            if d.get("diagnosis_id") and d.get("severity_score", 0) > 0
        ]
        
        # Step 1: Select applicable MNT rules ONLY for valid conditions
        rule_ids = self.select_mnt_rules(valid_medical_conditions, valid_nutrition_diagnoses)
        
        # Step 2: Resolve conflicts (sort by priority)
        resolved_rule_ids = self.resolve_conflicts(rule_ids)
        
        # Step 3: Generate constraints
        constraints = self.generate_constraints(resolved_rule_ids)
        
        # Create and return MNT context
        return MNTContext(
            assessment_id=diagnosis_context.assessment_id,
            macro_constraints=constraints.get("macro_constraints"),
            micro_constraints=constraints.get("micro_constraints"),
            food_exclusions=constraints.get("food_exclusions"),
            rule_ids_used=constraints.get("rule_ids_used", [])
        )
    
    def select_mnt_rules(
        self,
        medical_conditions: List[Dict[str, Any]],
        nutrition_diagnoses: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Select applicable MNT rules from knowledge base.
        
        Args:
            medical_conditions: List of medical conditions (each with diagnosis_id)
            nutrition_diagnoses: List of nutrition diagnoses (each with diagnosis_id)
            
        Returns:
            List of unique MNT rule IDs from knowledge base
            
        Note:
            Rule selection must be deterministic and reference KB rule IDs.
        """
        rule_ids = []
        
        # Check medical conditions - only process valid diagnoses (Bug 3.1)
        for condition in medical_conditions:
            diagnosis_id = condition.get("diagnosis_id")
            severity_score = condition.get("severity_score", 0)
            
            # Skip invalid or zero-severity diagnoses
            if not diagnosis_id or severity_score <= 0:
                continue
                
            applicable_rules = get_rules_for_diagnosis(diagnosis_id)
            rule_ids.extend(applicable_rules)
        
        # Check nutrition diagnoses - only process valid diagnoses
        for diagnosis in nutrition_diagnoses:
            diagnosis_id = diagnosis.get("diagnosis_id")
            severity_score = diagnosis.get("severity_score", 0)
            
            # Skip invalid or zero-severity diagnoses
            if not diagnosis_id or severity_score <= 0:
                continue
                
            applicable_rules = get_rules_for_diagnosis(diagnosis_id)
            rule_ids.extend(applicable_rules)
        
        # Return unique rule IDs (preserve order)
        seen = set()
        unique_rule_ids = []
        for rule_id in rule_ids:
            if rule_id not in seen:
                seen.add(rule_id)
                unique_rule_ids.append(rule_id)
        
        return unique_rule_ids
    
    def resolve_conflicts(self, rule_ids: List[str]) -> List[str]:
        """
        Resolve conflicts between multiple MNT rules.
        
        Args:
            rule_ids: List of applicable MNT rule IDs
            
        Returns:
            List of resolved rule IDs with conflicts handled
            
        Note:
            Conflict resolution must be deterministic.
            Priority handling must be explicit.
            Rules are sorted by priority (higher priority first).
            Duplicate rules are removed.
        """
        if not rule_ids:
            return []
        
        # Get rules and their priorities
        rules_with_priority = []
        for rule_id in rule_ids:
            rule = get_mnt_rule(rule_id)
            if rule:
                priority_level = rule.get("priority_level", 2)  # Default to medium
                rules_with_priority.append((rule_id, priority_level, rule))
        
        # Sort by priority (higher priority first)
        rules_with_priority.sort(key=lambda x: x[1], reverse=True)
        
        # Return rule IDs in priority order (duplicates already removed in select_mnt_rules)
        resolved_rule_ids = [rule_id for rule_id, _, _ in rules_with_priority]
        
        return resolved_rule_ids
    
    def generate_constraints(
        self,
        rule_ids: List[str],
        client_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate MNT constraints from rules.
        
        Args:
            rule_ids: List of resolved MNT rule IDs
            client_profile: Optional client profile data (not used yet, for future customization)
            
        Returns:
            Dictionary containing:
            - macro_constraints: Macro nutrient constraints (merged from all rules)
            - micro_constraints: Micronutrient constraints (merged from all rules)
            - food_exclusions: List of excluded foods (union of all rules)
            - rule_ids_used: List of rule IDs applied
            
        Note:
            Constraints generated here are mandatory and cannot be bypassed.
            When multiple rules apply, constraints are merged:
            - Macro constraints: Take most restrictive (lower max, higher min)
            - Micro constraints: Take most restrictive (lower max, higher min)
            - Food exclusions: Union of all exclusions
        """
        # Initialize merged constraints
        macro_constraints: Dict[str, Any] = {}
        micro_constraints: Dict[str, Any] = {}
        food_exclusions: List[str] = []
        valid_rule_ids: List[str] = []  # Track only valid rules
        
        # Apply each rule
        for rule_id in rule_ids:
            rule = get_mnt_rule(rule_id)
            if not rule:
                continue  # Skip invalid rule IDs
            
            valid_rule_ids.append(rule_id)  # Track valid rules only
            
            # Merge macro constraints (take most restrictive)
            if "macro_constraints" in rule and rule["macro_constraints"]:
                for key, value in rule["macro_constraints"].items():
                    if key not in macro_constraints:
                        macro_constraints[key] = value.copy()
                    else:
                        # Take more restrictive (lower max, higher min)
                        current = macro_constraints[key]
                        if "max" in value and "max" in current:
                            macro_constraints[key]["max"] = min(
                                value["max"],
                                current["max"]
                            )
                        elif "max" in value:
                            macro_constraints[key]["max"] = value["max"]
                        
                        if "min" in value and "min" in current:
                            macro_constraints[key]["min"] = max(
                                value["min"],
                                current["min"]
                            )
                        elif "min" in value:
                            macro_constraints[key]["min"] = value["min"]
                        
                        # Handle special cases like deficit_percent and surplus_percent
                        if "deficit_percent" in value:
                            # Take higher deficit (more restrictive)
                            if "deficit_percent" in current:
                                macro_constraints[key]["deficit_percent"] = max(
                                    value["deficit_percent"],
                                    current["deficit_percent"]
                                )
                            else:
                                macro_constraints[key]["deficit_percent"] = value["deficit_percent"]
                        
                        if "surplus_percent" in value:
                            # Take higher surplus (more restrictive for weight gain)
                            if "surplus_percent" in current:
                                macro_constraints[key]["surplus_percent"] = max(
                                    value["surplus_percent"],
                                    current["surplus_percent"]
                                )
                            else:
                                macro_constraints[key]["surplus_percent"] = value["surplus_percent"]
                        
                        # Preserve other fields like unit, note if they exist
                        if "unit" in value and "unit" not in macro_constraints[key]:
                            macro_constraints[key]["unit"] = value["unit"]
                        if "note" in value and "note" not in macro_constraints[key]:
                            macro_constraints[key]["note"] = value["note"]
            
            # Merge micro constraints (take most restrictive)
            if "micro_constraints" in rule and rule["micro_constraints"]:
                for key, value in rule["micro_constraints"].items():
                    if key not in micro_constraints:
                        micro_constraints[key] = value.copy()
                    else:
                        # Take more restrictive (lower max, higher min)
                        current = micro_constraints[key]
                        if "max" in value and "max" in current:
                            micro_constraints[key]["max"] = min(
                                value["max"],
                                current["max"]
                            )
                        elif "max" in value:
                            micro_constraints[key]["max"] = value["max"]
                        
                        if "min" in value and "min" in current:
                            micro_constraints[key]["min"] = max(
                                value["min"],
                                current["min"]
                            )
                        elif "min" in value:
                            micro_constraints[key]["min"] = value["min"]
                        
                        # Preserve other fields like unit, note if they exist
                        if "unit" in value and "unit" not in micro_constraints[key]:
                            micro_constraints[key]["unit"] = value["unit"]
                        if "note" in value and "note" not in micro_constraints[key]:
                            micro_constraints[key]["note"] = value["note"]
            
            # Union food exclusions
            if "food_exclusions" in rule and rule["food_exclusions"]:
                food_exclusions.extend(rule["food_exclusions"])
        
        # NEW: Normalize and deduplicate food exclusions (Bug 3.2)
        food_exclusions = self._normalize_and_deduplicate_exclusions(food_exclusions)
        
        return {
            "macro_constraints": macro_constraints,
            "micro_constraints": micro_constraints,
            "food_exclusions": food_exclusions,
            "rule_ids_used": valid_rule_ids  # Only return valid rule IDs
        }
    
    def _normalize_and_deduplicate_exclusions(self, exclusions: List[str]) -> List[str]:
        """
        Normalize and deduplicate food exclusion list (Bug 3.2).
        
        Args:
            exclusions: List of exclusion strings (may have duplicates or variations)
            
        Returns:
            Normalized and deduplicated list of exclusions
        """
        if not exclusions:
            return []
        
        # Normalization mapping: normalize variations to canonical form
        exclusion_normalization = {
            "refined_sugars": "refined_sugar",
            "processed_snacks": "processed_foods",
            "sweetened_beverages": "sugar_sweetened_beverages",
            # Add more normalization mappings as needed
        }
        
        # Normalize exclusions
        normalized_exclusions = set()
        for exclusion in exclusions:
            if not exclusion or not isinstance(exclusion, str):
                continue
            
            # Normalize to canonical form
            normalized = exclusion_normalization.get(exclusion, exclusion)
            normalized_exclusions.add(normalized)
        
        # Return sorted list for consistency
        return sorted(list(normalized_exclusions))


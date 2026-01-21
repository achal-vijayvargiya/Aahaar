"""
Tests for MNT Engine.

Unit tests for the MNT engine - testing rule-based constraint generation in isolation.
"""
import pytest
from uuid import uuid4

from app.platform.engines.mnt_engine.mnt_engine import MNTEngine
from app.platform.core.context import DiagnosisContext


class TestSelectMNTRules:
    """Test suite for select_mnt_rules method."""
    
    def test_select_rules_for_diabetes(self):
        """Test selecting rules for Type 2 Diabetes."""
        engine = MNTEngine()
        
        medical_conditions = [{"diagnosis_id": "type_2_diabetes", "severity_score": 7.0}]
        nutrition_diagnoses = []
        
        rule_ids = engine.select_mnt_rules(medical_conditions, nutrition_diagnoses)
        
        assert "mnt_carb_restriction_diabetes" in rule_ids
        assert len(rule_ids) == 1
    
    def test_select_rules_for_hypertension(self):
        """Test selecting rules for Hypertension."""
        engine = MNTEngine()
        
        medical_conditions = [{"diagnosis_id": "hypertension", "severity_score": 6.0}]
        nutrition_diagnoses = []
        
        rule_ids = engine.select_mnt_rules(medical_conditions, nutrition_diagnoses)
        
        assert "mnt_sodium_restriction_hypertension" in rule_ids
        assert len(rule_ids) == 1
    
    def test_select_rules_for_dyslipidemia(self):
        """Test selecting rules for Dyslipidemia."""
        engine = MNTEngine()
        
        medical_conditions = [{"diagnosis_id": "dyslipidemia", "severity_score": 5.0}]
        nutrition_diagnoses = []
        
        rule_ids = engine.select_mnt_rules(medical_conditions, nutrition_diagnoses)
        
        assert "mnt_fat_modification_dyslipidemia" in rule_ids
        assert len(rule_ids) == 1
    
    def test_select_rules_for_obesity(self):
        """Test selecting rules for Obesity."""
        engine = MNTEngine()
        
        medical_conditions = [{"diagnosis_id": "obesity", "severity_score": 6.0}]
        nutrition_diagnoses = []
        
        rule_ids = engine.select_mnt_rules(medical_conditions, nutrition_diagnoses)
        
        assert "mnt_calorie_restriction_obesity" in rule_ids
        assert len(rule_ids) == 1
    
    def test_select_rules_for_excess_carbs(self):
        """Test selecting rules for excess carbohydrate intake."""
        engine = MNTEngine()
        
        medical_conditions = []
        nutrition_diagnoses = [{"diagnosis_id": "excess_carbohydrate_intake", "severity_score": 7.5}]
        
        rule_ids = engine.select_mnt_rules(medical_conditions, nutrition_diagnoses)
        
        assert "mnt_carb_restriction_diabetes" in rule_ids
        assert len(rule_ids) == 1
    
    def test_select_rules_for_inadequate_fiber(self):
        """Test selecting rules for inadequate fiber intake."""
        engine = MNTEngine()
        
        medical_conditions = []
        nutrition_diagnoses = [{"diagnosis_id": "inadequate_fiber_intake", "severity_score": 6.0}]
        
        rule_ids = engine.select_mnt_rules(medical_conditions, nutrition_diagnoses)
        
        assert "mnt_fiber_increase" in rule_ids
        assert len(rule_ids) == 1
    
    def test_select_rules_for_inadequate_protein(self):
        """Test selecting rules for inadequate protein intake."""
        engine = MNTEngine()
        
        medical_conditions = []
        nutrition_diagnoses = [{"diagnosis_id": "inadequate_protein_intake", "severity_score": 5.0}]
        
        rule_ids = engine.select_mnt_rules(medical_conditions, nutrition_diagnoses)
        
        assert "mnt_protein_adequate" in rule_ids
        assert len(rule_ids) == 1
    
    def test_select_rules_multiple_conditions(self):
        """Test selecting rules for multiple conditions."""
        engine = MNTEngine()
        
        medical_conditions = [
            {"diagnosis_id": "type_2_diabetes", "severity_score": 7.0},
            {"diagnosis_id": "hypertension", "severity_score": 6.0},
            {"diagnosis_id": "obesity", "severity_score": 6.0}
        ]
        nutrition_diagnoses = [
            {"diagnosis_id": "excess_carbohydrate_intake", "severity_score": 7.5}
        ]
        
        rule_ids = engine.select_mnt_rules(medical_conditions, nutrition_diagnoses)
        
        assert "mnt_carb_restriction_diabetes" in rule_ids
        assert "mnt_sodium_restriction_hypertension" in rule_ids
        assert "mnt_calorie_restriction_obesity" in rule_ids
        # Should not duplicate carb restriction rule
        assert rule_ids.count("mnt_carb_restriction_diabetes") == 1
    
    def test_select_rules_no_duplicates(self):
        """Test that duplicate rules are not returned."""
        engine = MNTEngine()
        
        medical_conditions = [{"diagnosis_id": "type_2_diabetes", "severity_score": 7.0}]
        nutrition_diagnoses = [{"diagnosis_id": "excess_carbohydrate_intake", "severity_score": 7.5}]
        
        rule_ids = engine.select_mnt_rules(medical_conditions, nutrition_diagnoses)
        
        # Both diagnoses map to same rule, should only appear once
        assert rule_ids.count("mnt_carb_restriction_diabetes") == 1
    
    def test_select_rules_empty_input(self):
        """Test selecting rules with empty input."""
        engine = MNTEngine()
        
        rule_ids = engine.select_mnt_rules([], [])
        
        assert rule_ids == []
        assert len(rule_ids) == 0
    
    def test_select_rules_unknown_diagnosis(self):
        """Test selecting rules for unknown diagnosis."""
        engine = MNTEngine()
        
        medical_conditions = [{"diagnosis_id": "unknown_condition", "severity_score": 5.0}]
        nutrition_diagnoses = []
        
        rule_ids = engine.select_mnt_rules(medical_conditions, nutrition_diagnoses)
        
        # Unknown diagnosis should not map to any rule
        assert rule_ids == []
    
    def test_select_rules_missing_diagnosis_id(self):
        """Test handling of missing diagnosis_id in condition."""
        engine = MNTEngine()
        
        medical_conditions = [{"severity_score": 7.0}]  # Missing diagnosis_id
        nutrition_diagnoses = []
        
        rule_ids = engine.select_mnt_rules(medical_conditions, nutrition_diagnoses)
        
        # Should handle gracefully
        assert isinstance(rule_ids, list)
        assert len(rule_ids) == 0


class TestResolveConflicts:
    """Test suite for resolve_conflicts method."""
    
    def test_resolve_conflicts_single_rule(self):
        """Test resolving conflicts with single rule."""
        engine = MNTEngine()
        
        rule_ids = ["mnt_carb_restriction_diabetes"]
        resolved = engine.resolve_conflicts(rule_ids)
        
        assert len(resolved) == 1
        assert resolved[0] == "mnt_carb_restriction_diabetes"
    
    def test_resolve_conflicts_priority_sorting(self):
        """Test that rules are sorted by priority."""
        engine = MNTEngine()
        
        # Mix of high and medium priority rules
        rule_ids = [
            "mnt_calorie_restriction_obesity",  # medium priority
            "mnt_carb_restriction_diabetes",  # high priority
            "mnt_fiber_increase"  # medium priority
        ]
        resolved = engine.resolve_conflicts(rule_ids)
        
        # High priority rules should come first
        assert resolved[0] == "mnt_carb_restriction_diabetes"
        assert len(resolved) == 3
    
    def test_resolve_conflicts_empty_list(self):
        """Test resolving conflicts with empty list."""
        engine = MNTEngine()
        
        resolved = engine.resolve_conflicts([])
        
        assert resolved == []
    
    def test_resolve_conflicts_invalid_rule_id(self):
        """Test handling of invalid rule IDs."""
        engine = MNTEngine()
        
        rule_ids = ["invalid_rule_id", "mnt_carb_restriction_diabetes"]
        resolved = engine.resolve_conflicts(rule_ids)
        
        # Should only return valid rules
        assert len(resolved) == 1
        assert resolved[0] == "mnt_carb_restriction_diabetes"


class TestGenerateConstraints:
    """Test suite for generate_constraints method."""
    
    def test_generate_constraints_single_rule(self):
        """Test generating constraints from single rule."""
        engine = MNTEngine()
        
        rule_ids = ["mnt_carb_restriction_diabetes"]
        constraints = engine.generate_constraints(rule_ids)
        
        assert "macro_constraints" in constraints
        assert "micro_constraints" in constraints
        assert "food_exclusions" in constraints
        assert "rule_ids_used" in constraints
        
        assert constraints["macro_constraints"]["carbohydrates_percent"]["max"] == 45
        assert constraints["macro_constraints"]["fiber_g"]["min"] == 25
        assert "refined_sugar" in constraints["food_exclusions"]
        assert constraints["rule_ids_used"] == rule_ids
    
    def test_generate_constraints_hypertension(self):
        """Test generating constraints for hypertension rule."""
        engine = MNTEngine()
        
        rule_ids = ["mnt_sodium_restriction_hypertension"]
        constraints = engine.generate_constraints(rule_ids)
        
        assert constraints["micro_constraints"]["sodium_mg"]["max"] == 2300
        assert "processed_foods" in constraints["food_exclusions"]
        assert constraints["macro_constraints"] == {}
    
    def test_generate_constraints_dyslipidemia(self):
        """Test generating constraints for dyslipidemia rule."""
        engine = MNTEngine()
        
        rule_ids = ["mnt_fat_modification_dyslipidemia"]
        constraints = engine.generate_constraints(rule_ids)
        
        assert constraints["macro_constraints"]["saturated_fat_percent"]["max"] == 7
        assert constraints["macro_constraints"]["trans_fat_g"]["max"] == 0
        assert "trans_fats" in constraints["food_exclusions"]
    
    def test_generate_constraints_obesity(self):
        """Test generating constraints for obesity rule."""
        engine = MNTEngine()
        
        rule_ids = ["mnt_calorie_restriction_obesity"]
        constraints = engine.generate_constraints(rule_ids)
        
        assert constraints["macro_constraints"]["calories"]["deficit_percent"] == 20
        assert constraints["food_exclusions"] == []
    
    def test_generate_constraints_multiple_rules_merge(self):
        """Test merging constraints from multiple rules."""
        engine = MNTEngine()
        
        rule_ids = [
            "mnt_carb_restriction_diabetes",
            "mnt_sodium_restriction_hypertension"
        ]
        constraints = engine.generate_constraints(rule_ids)
        
        # Should have merged constraints
        assert "carbohydrates_percent" in constraints["macro_constraints"]
        assert "sodium_mg" in constraints["micro_constraints"]
        # Food exclusions should be union
        assert "refined_sugar" in constraints["food_exclusions"]
        assert "processed_foods" in constraints["food_exclusions"]
        assert len(constraints["rule_ids_used"]) == 2
    
    def test_generate_constraints_merge_most_restrictive(self):
        """Test that merging takes most restrictive constraints."""
        engine = MNTEngine()
        
        # Both diabetes and fiber rules have fiber constraints
        rule_ids = [
            "mnt_carb_restriction_diabetes",  # fiber_g min: 25
            "mnt_fiber_increase"  # fiber_g min: 25
        ]
        constraints = engine.generate_constraints(rule_ids)
        
        # Should take the higher min (both are 25, so should be 25)
        assert constraints["macro_constraints"]["fiber_g"]["min"] == 25
    
    def test_generate_constraints_merge_food_exclusions(self):
        """Test that food exclusions are merged (union)."""
        engine = MNTEngine()
        
        rule_ids = [
            "mnt_carb_restriction_diabetes",  # excludes: refined_sugar, white_flour, high_gi_foods
            "mnt_sodium_restriction_hypertension"  # excludes: processed_foods, high_sodium_foods
        ]
        constraints = engine.generate_constraints(rule_ids)
        
        # Should have all exclusions
        assert len(constraints["food_exclusions"]) >= 5
        assert "refined_sugar" in constraints["food_exclusions"]
        assert "processed_foods" in constraints["food_exclusions"]
        assert "high_sodium_foods" in constraints["food_exclusions"]
    
    def test_generate_constraints_empty_rule_ids(self):
        """Test generating constraints with empty rule IDs."""
        engine = MNTEngine()
        
        constraints = engine.generate_constraints([])
        
        assert constraints["macro_constraints"] == {}
        assert constraints["micro_constraints"] == {}
        assert constraints["food_exclusions"] == []
        assert constraints["rule_ids_used"] == []
    
    def test_generate_constraints_invalid_rule_id(self):
        """Test handling of invalid rule IDs."""
        engine = MNTEngine()
        
        rule_ids = ["invalid_rule_id", "mnt_carb_restriction_diabetes"]
        constraints = engine.generate_constraints(rule_ids)
        
        # Should only apply valid rules
        assert "mnt_carb_restriction_diabetes" in constraints["rule_ids_used"]
        assert "invalid_rule_id" not in constraints["rule_ids_used"]


class TestProcessDiagnoses:
    """Test suite for process_diagnoses method."""
    
    def test_process_diagnoses_complete(self):
        """Test processing diagnoses with complete data."""
        engine = MNTEngine()
        
        diagnosis_context = DiagnosisContext(
            assessment_id=uuid4(),
            medical_conditions=[
                {"diagnosis_id": "type_2_diabetes", "severity_score": 7.0, "evidence": {}},
                {"diagnosis_id": "hypertension", "severity_score": 6.0, "evidence": {}}
            ],
            nutrition_diagnoses=[
                {"diagnosis_id": "excess_carbohydrate_intake", "severity_score": 7.5, "evidence": {}}
            ]
        )
        
        mnt_context = engine.process_diagnoses(diagnosis_context)
        
        assert mnt_context.assessment_id == diagnosis_context.assessment_id
        assert len(mnt_context.rule_ids_used) > 0
        assert "mnt_carb_restriction_diabetes" in mnt_context.rule_ids_used
        assert "mnt_sodium_restriction_hypertension" in mnt_context.rule_ids_used
        assert mnt_context.macro_constraints is not None
        assert mnt_context.micro_constraints is not None
        assert mnt_context.food_exclusions is not None
    
    def test_process_diagnoses_missing_assessment_id(self):
        """Test that missing assessment_id raises error."""
        engine = MNTEngine()
        
        diagnosis_context = DiagnosisContext(
            assessment_id=None,  # Missing
            medical_conditions=[],
            nutrition_diagnoses=[]
        )
        
        with pytest.raises(ValueError, match="assessment_id is required"):
            engine.process_diagnoses(diagnosis_context)
    
    def test_process_diagnoses_empty_diagnoses(self):
        """Test processing with no diagnoses."""
        engine = MNTEngine()
        
        diagnosis_context = DiagnosisContext(
            assessment_id=uuid4(),
            medical_conditions=[],
            nutrition_diagnoses=[]
        )
        
        mnt_context = engine.process_diagnoses(diagnosis_context)
        
        assert mnt_context.assessment_id == diagnosis_context.assessment_id
        assert mnt_context.rule_ids_used == []
        assert mnt_context.macro_constraints == {}
        assert mnt_context.micro_constraints == {}
        assert mnt_context.food_exclusions == []
    
    def test_process_diagnoses_only_medical_conditions(self):
        """Test processing with only medical conditions."""
        engine = MNTEngine()
        
        diagnosis_context = DiagnosisContext(
            assessment_id=uuid4(),
            medical_conditions=[
                {"diagnosis_id": "type_2_diabetes", "severity_score": 7.0, "evidence": {}}
            ],
            nutrition_diagnoses=[]
        )
        
        mnt_context = engine.process_diagnoses(diagnosis_context)
        
        assert len(mnt_context.rule_ids_used) > 0
        assert "mnt_carb_restriction_diabetes" in mnt_context.rule_ids_used
    
    def test_process_diagnoses_only_nutrition_diagnoses(self):
        """Test processing with only nutrition diagnoses."""
        engine = MNTEngine()
        
        diagnosis_context = DiagnosisContext(
            assessment_id=uuid4(),
            medical_conditions=[],
            nutrition_diagnoses=[
                {"diagnosis_id": "inadequate_fiber_intake", "severity_score": 6.0, "evidence": {}}
            ]
        )
        
        mnt_context = engine.process_diagnoses(diagnosis_context)
        
        assert len(mnt_context.rule_ids_used) > 0
        assert "mnt_fiber_increase" in mnt_context.rule_ids_used
    
    def test_process_diagnoses_multiple_rules_merged(self):
        """Test that multiple rules are properly merged."""
        engine = MNTEngine()
        
        diagnosis_context = DiagnosisContext(
            assessment_id=uuid4(),
            medical_conditions=[
                {"diagnosis_id": "type_2_diabetes", "severity_score": 7.0, "evidence": {}},
                {"diagnosis_id": "hypertension", "severity_score": 6.0, "evidence": {}},
                {"diagnosis_id": "obesity", "severity_score": 6.0, "evidence": {}}
            ],
            nutrition_diagnoses=[
                {"diagnosis_id": "inadequate_fiber_intake", "severity_score": 6.0, "evidence": {}}
            ]
        )
        
        mnt_context = engine.process_diagnoses(diagnosis_context)
        
        # Should have multiple rules
        assert len(mnt_context.rule_ids_used) >= 3
        assert "mnt_carb_restriction_diabetes" in mnt_context.rule_ids_used
        assert "mnt_sodium_restriction_hypertension" in mnt_context.rule_ids_used
        assert "mnt_calorie_restriction_obesity" in mnt_context.rule_ids_used
        
        # Constraints should be merged
        assert len(mnt_context.macro_constraints) > 0
        assert len(mnt_context.food_exclusions) > 0
    
    def test_process_diagnoses_constraints_structure(self):
        """Test that generated constraints have correct structure."""
        engine = MNTEngine()
        
        diagnosis_context = DiagnosisContext(
            assessment_id=uuid4(),
            medical_conditions=[
                {"diagnosis_id": "type_2_diabetes", "severity_score": 7.0, "evidence": {}}
            ],
            nutrition_diagnoses=[]
        )
        
        mnt_context = engine.process_diagnoses(diagnosis_context)
        
        # Verify structure
        assert isinstance(mnt_context.macro_constraints, dict)
        assert isinstance(mnt_context.micro_constraints, dict)
        assert isinstance(mnt_context.food_exclusions, list)
        assert isinstance(mnt_context.rule_ids_used, list)
        
        # Verify constraints are not empty
        assert len(mnt_context.macro_constraints) > 0 or len(mnt_context.micro_constraints) > 0
        assert len(mnt_context.rule_ids_used) > 0


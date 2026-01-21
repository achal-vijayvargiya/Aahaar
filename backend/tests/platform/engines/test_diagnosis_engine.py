"""
Tests for Diagnosis Engine.

Unit tests for the diagnosis engine - testing rule-based logic in isolation.
"""
import pytest
from uuid import uuid4

from app.platform.engines.diagnosis_engine.diagnosis_engine import DiagnosisEngine
from app.platform.core.context import AssessmentContext


class TestIdentifyMedicalConditions:
    """Test suite for identify_medical_conditions method."""
    
    def test_type_2_diabetes_hba1c(self):
        """Test identifying Type 2 Diabetes based on HbA1c."""
        engine = DiagnosisEngine()
        
        labs = {"HbA1c": 7.5}
        conditions = engine.identify_medical_conditions(labs=labs)
        
        assert len(conditions) == 1
        assert conditions[0]["diagnosis_id"] == "type_2_diabetes"
        assert conditions[0]["severity_score"] > 0
        assert "HbA1c" in conditions[0]["evidence"]
        assert conditions[0]["evidence"]["HbA1c"] == 7.5
    
    def test_type_2_diabetes_fbs(self):
        """Test identifying Type 2 Diabetes based on FBS."""
        engine = DiagnosisEngine()
        
        labs = {"FBS": 140}
        conditions = engine.identify_medical_conditions(labs=labs)
        
        assert len(conditions) == 1
        assert conditions[0]["diagnosis_id"] == "type_2_diabetes"
        assert conditions[0]["severity_score"] > 0
        assert "FBS" in conditions[0]["evidence"]
    
    def test_type_2_diabetes_severity_mild(self):
        """Test diabetes severity calculation for mild case."""
        engine = DiagnosisEngine()
        
        labs = {"HbA1c": 6.8}
        conditions = engine.identify_medical_conditions(labs=labs)
        
        assert len(conditions) == 1
        assert conditions[0]["diagnosis_id"] == "type_2_diabetes"
        assert 5.0 <= conditions[0]["severity_score"] < 7.0  # Mild range
    
    def test_type_2_diabetes_severity_moderate(self):
        """Test diabetes severity calculation for moderate case."""
        engine = DiagnosisEngine()
        
        labs = {"HbA1c": 7.5}
        conditions = engine.identify_medical_conditions(labs=labs)
        
        assert len(conditions) == 1
        assert conditions[0]["diagnosis_id"] == "type_2_diabetes"
        assert 7.0 <= conditions[0]["severity_score"] < 8.0  # Moderate range
    
    def test_type_2_diabetes_severity_severe(self):
        """Test diabetes severity calculation for severe case."""
        engine = DiagnosisEngine()
        
        labs = {"HbA1c": 9.0}
        conditions = engine.identify_medical_conditions(labs=labs)
        
        assert len(conditions) == 1
        assert conditions[0]["diagnosis_id"] == "type_2_diabetes"
        assert conditions[0]["severity_score"] >= 7.0  # Severe range
    
    def test_prediabetes_hba1c(self):
        """Test identifying Prediabetes based on HbA1c."""
        engine = DiagnosisEngine()
        
        labs = {"HbA1c": 6.0}
        conditions = engine.identify_medical_conditions(labs=labs)
        
        assert len(conditions) == 1
        assert conditions[0]["diagnosis_id"] == "prediabetes"
        assert "HbA1c" in conditions[0]["evidence"]
    
    def test_prediabetes_fbs(self):
        """Test identifying Prediabetes based on FBS."""
        engine = DiagnosisEngine()
        
        labs = {"FBS": 110}
        conditions = engine.identify_medical_conditions(labs=labs)
        
        assert len(conditions) == 1
        assert conditions[0]["diagnosis_id"] == "prediabetes"
        assert "FBS" in conditions[0]["evidence"]
    
    def test_prediabetes_not_if_diabetes(self):
        """Test that prediabetes is not diagnosed if diabetes is present."""
        engine = DiagnosisEngine()
        
        labs = {"HbA1c": 7.5}  # Diabetes level
        conditions = engine.identify_medical_conditions(labs=labs)
        
        # Should only have diabetes, not prediabetes
        assert len(conditions) == 1
        assert conditions[0]["diagnosis_id"] == "type_2_diabetes"
        assert not any(c["diagnosis_id"] == "prediabetes" for c in conditions)
    
    def test_hypertension_systolic(self):
        """Test identifying Hypertension based on systolic BP."""
        engine = DiagnosisEngine()
        
        anthropometry = {"bp_systolic": 140, "bp_diastolic": 85}
        conditions = engine.identify_medical_conditions(anthropometry=anthropometry)
        
        assert len(conditions) == 1
        assert conditions[0]["diagnosis_id"] == "hypertension"
        assert "bp_systolic" in conditions[0]["evidence"]
    
    def test_hypertension_diastolic(self):
        """Test identifying Hypertension based on diastolic BP."""
        engine = DiagnosisEngine()
        
        anthropometry = {"bp_diastolic": 90}
        conditions = engine.identify_medical_conditions(anthropometry=anthropometry)
        
        assert len(conditions) == 1
        assert conditions[0]["diagnosis_id"] == "hypertension"
        assert "bp_diastolic" in conditions[0]["evidence"]
    
    def test_hypertension_severity_stage1(self):
        """Test hypertension severity for Stage 1."""
        engine = DiagnosisEngine()
        
        anthropometry = {"bp_systolic": 145, "bp_diastolic": 92}
        conditions = engine.identify_medical_conditions(anthropometry=anthropometry)
        
        assert len(conditions) == 1
        assert conditions[0]["diagnosis_id"] == "hypertension"
        assert 6.0 <= conditions[0]["severity_score"] < 7.0  # Stage 1
    
    def test_hypertension_severity_stage2(self):
        """Test hypertension severity for Stage 2."""
        engine = DiagnosisEngine()
        
        anthropometry = {"bp_systolic": 165, "bp_diastolic": 105}
        conditions = engine.identify_medical_conditions(anthropometry=anthropometry)
        
        assert len(conditions) == 1
        assert conditions[0]["diagnosis_id"] == "hypertension"
        assert 7.0 <= conditions[0]["severity_score"] < 9.0  # Stage 2
    
    def test_hypertension_severity_stage3(self):
        """Test hypertension severity for Stage 3."""
        engine = DiagnosisEngine()
        
        anthropometry = {"bp_systolic": 185, "bp_diastolic": 125}
        conditions = engine.identify_medical_conditions(anthropometry=anthropometry)
        
        assert len(conditions) == 1
        assert conditions[0]["diagnosis_id"] == "hypertension"
        assert conditions[0]["severity_score"] >= 9.0  # Stage 3
    
    def test_dyslipidemia_cholesterol(self):
        """Test identifying Dyslipidemia based on cholesterol."""
        engine = DiagnosisEngine()
        
        labs = {"cholesterol": 220}
        conditions = engine.identify_medical_conditions(labs=labs)
        
        assert len(conditions) == 1
        assert conditions[0]["diagnosis_id"] == "dyslipidemia"
        assert "cholesterol" in conditions[0]["evidence"]
    
    def test_dyslipidemia_triglycerides(self):
        """Test identifying Dyslipidemia based on triglycerides."""
        engine = DiagnosisEngine()
        
        labs = {"triglycerides": 180}
        conditions = engine.identify_medical_conditions(labs=labs)
        
        assert len(conditions) == 1
        assert conditions[0]["diagnosis_id"] == "dyslipidemia"
        assert "triglycerides" in conditions[0]["evidence"]
    
    def test_obesity(self):
        """Test identifying Obesity based on BMI."""
        engine = DiagnosisEngine()
        
        anthropometry = {"bmi": 32}
        conditions = engine.identify_medical_conditions(anthropometry=anthropometry)
        
        assert len(conditions) == 1
        assert conditions[0]["diagnosis_id"] == "obesity"
        assert "bmi" in conditions[0]["evidence"]
        assert conditions[0]["evidence"]["bmi"] == 32
    
    def test_obesity_severity_class1(self):
        """Test obesity severity for Class 1."""
        engine = DiagnosisEngine()
        
        anthropometry = {"bmi": 32}
        conditions = engine.identify_medical_conditions(anthropometry=anthropometry)
        
        assert len(conditions) == 1
        assert conditions[0]["diagnosis_id"] == "obesity"
        assert 6.0 <= conditions[0]["severity_score"] < 7.5  # Class 1
    
    def test_obesity_severity_class2(self):
        """Test obesity severity for Class 2."""
        engine = DiagnosisEngine()
        
        anthropometry = {"bmi": 37}
        conditions = engine.identify_medical_conditions(anthropometry=anthropometry)
        
        assert len(conditions) == 1
        assert conditions[0]["diagnosis_id"] == "obesity"
        assert 7.5 <= conditions[0]["severity_score"] < 9.0  # Class 2
    
    def test_obesity_severity_class3(self):
        """Test obesity severity for Class 3."""
        engine = DiagnosisEngine()
        
        anthropometry = {"bmi": 42}
        conditions = engine.identify_medical_conditions(anthropometry=anthropometry)
        
        assert len(conditions) == 1
        assert conditions[0]["diagnosis_id"] == "obesity"
        assert conditions[0]["severity_score"] >= 9.0  # Class 3
    
    def test_overweight(self):
        """Test identifying Overweight based on BMI."""
        engine = DiagnosisEngine()
        
        anthropometry = {"bmi": 27}
        conditions = engine.identify_medical_conditions(anthropometry=anthropometry)
        
        assert len(conditions) == 1
        assert conditions[0]["diagnosis_id"] == "overweight"
        assert "bmi" in conditions[0]["evidence"]
    
    def test_overweight_not_if_obese(self):
        """Test that overweight is not diagnosed if obese."""
        engine = DiagnosisEngine()
        
        anthropometry = {"bmi": 32}  # Obese level
        conditions = engine.identify_medical_conditions(anthropometry=anthropometry)
        
        # Should only have obesity, not overweight
        assert len(conditions) == 1
        assert conditions[0]["diagnosis_id"] == "obesity"
        assert not any(c["diagnosis_id"] == "overweight" for c in conditions)
    
    def test_multiple_conditions(self):
        """Test identifying multiple conditions at once."""
        engine = DiagnosisEngine()
        
        labs = {"HbA1c": 7.5, "cholesterol": 220}
        anthropometry = {"bmi": 32, "bp_systolic": 140}
        conditions = engine.identify_medical_conditions(labs=labs, anthropometry=anthropometry)
        
        assert len(conditions) >= 3
        diagnosis_ids = [c["diagnosis_id"] for c in conditions]
        assert "type_2_diabetes" in diagnosis_ids
        assert "dyslipidemia" in diagnosis_ids
        assert "obesity" in diagnosis_ids
        assert "hypertension" in diagnosis_ids
    
    def test_no_conditions_with_normal_values(self):
        """Test that no conditions are identified with normal values."""
        engine = DiagnosisEngine()
        
        labs = {"HbA1c": 5.0, "cholesterol": 180}
        anthropometry = {"bmi": 22, "bp_systolic": 120}
        conditions = engine.identify_medical_conditions(labs=labs, anthropometry=anthropometry)
        
        assert len(conditions) == 0
    
    def test_missing_data_handling(self):
        """Test that missing data doesn't cause errors."""
        engine = DiagnosisEngine()
        
        conditions = engine.identify_medical_conditions()
        
        assert isinstance(conditions, list)
        assert len(conditions) == 0
    
    def test_edge_case_boundary_values(self):
        """Test boundary values for conditions."""
        engine = DiagnosisEngine()
        
        # Test exact threshold values
        labs = {"HbA1c": 6.5}  # Exactly at diabetes threshold
        conditions = engine.identify_medical_conditions(labs=labs)
        
        assert len(conditions) == 1
        assert conditions[0]["diagnosis_id"] == "type_2_diabetes"
    
    def test_invalid_data_types(self):
        """Test handling of invalid data types."""
        engine = DiagnosisEngine()
        
        labs = {"HbA1c": "invalid"}
        conditions = engine.identify_medical_conditions(labs=labs)
        
        # Should handle gracefully without crashing
        assert isinstance(conditions, list)


class TestIdentifyNutritionDiagnoses:
    """Test suite for identify_nutrition_diagnoses method."""
    
    def test_excess_carbohydrate_intake(self):
        """Test identifying excess carbohydrate intake."""
        engine = DiagnosisEngine()
        
        labs = {"HbA1c": 7.5}
        diet_history = {"carb_intake_percent": 60}
        diagnoses = engine.identify_nutrition_diagnoses(labs=labs, diet_history=diet_history)
        
        assert len(diagnoses) == 1
        assert diagnoses[0]["diagnosis_id"] == "excess_carbohydrate_intake"
        assert "HbA1c" in diagnoses[0]["evidence"]
        assert "carb_intake_percent" in diagnoses[0]["evidence"]
    
    def test_excess_carb_not_without_diabetes(self):
        """Test that excess carbs not diagnosed without diabetes."""
        engine = DiagnosisEngine()
        
        labs = {"HbA1c": 6.0}  # Not diabetic
        diet_history = {"carb_intake_percent": 60}
        diagnoses = engine.identify_nutrition_diagnoses(labs=labs, diet_history=diet_history)
        
        # Should not diagnose excess carbs if HbA1c <= 7.0
        assert not any(d["diagnosis_id"] == "excess_carbohydrate_intake" for d in diagnoses)
    
    def test_inadequate_fiber_intake(self):
        """Test identifying inadequate fiber intake."""
        engine = DiagnosisEngine()
        
        diet_history = {"fiber_grams": 15}
        diagnoses = engine.identify_nutrition_diagnoses(diet_history=diet_history)
        
        assert len(diagnoses) == 1
        assert diagnoses[0]["diagnosis_id"] == "inadequate_fiber_intake"
        assert "fiber_grams" in diagnoses[0]["evidence"]
        assert diagnoses[0]["evidence"]["fiber_grams"] == 15
    
    def test_excessive_calorie_intake(self):
        """Test identifying excessive calorie intake."""
        engine = DiagnosisEngine()
        
        anthropometry = {"bmi": 28}
        diet_history = {"calorie_excess": True}
        diagnoses = engine.identify_nutrition_diagnoses(anthropometry=anthropometry, diet_history=diet_history)
        
        assert len(diagnoses) == 1
        assert diagnoses[0]["diagnosis_id"] == "excessive_calorie_intake"
        assert "bmi" in diagnoses[0]["evidence"]
    
    def test_inadequate_protein_intake(self):
        """Test identifying inadequate protein intake."""
        engine = DiagnosisEngine()
        
        anthropometry = {"weight_kg": 70}
        diet_history = {"protein_grams": 40}  # 40/70 = 0.57 g/kg (below 0.8 threshold)
        diagnoses = engine.identify_nutrition_diagnoses(anthropometry=anthropometry, diet_history=diet_history)
        
        assert len(diagnoses) == 1
        assert diagnoses[0]["diagnosis_id"] == "inadequate_protein_intake"
        assert "protein_per_kg" in diagnoses[0]["evidence"]
        assert diagnoses[0]["evidence"]["protein_per_kg"] < 0.8
    
    def test_multiple_nutrition_diagnoses(self):
        """Test identifying multiple nutrition diagnoses."""
        engine = DiagnosisEngine()
        
        labs = {"HbA1c": 8.0}
        anthropometry = {"bmi": 28, "weight_kg": 70}
        diet_history = {
            "carb_intake_percent": 60,
            "fiber_grams": 15,
            "protein_grams": 40,
            "calorie_excess": True
        }
        diagnoses = engine.identify_nutrition_diagnoses(
            labs=labs,
            anthropometry=anthropometry,
            diet_history=diet_history
        )
        
        assert len(diagnoses) >= 3
        diagnosis_ids = [d["diagnosis_id"] for d in diagnoses]
        assert "excess_carbohydrate_intake" in diagnosis_ids
        assert "inadequate_fiber_intake" in diagnosis_ids
        assert "inadequate_protein_intake" in diagnosis_ids
        assert "excessive_calorie_intake" in diagnosis_ids
    
    def test_no_nutrition_diagnoses_with_adequate_intake(self):
        """Test that no diagnoses are made with adequate intake."""
        engine = DiagnosisEngine()
        
        labs = {"HbA1c": 5.5}
        anthropometry = {"bmi": 22, "weight_kg": 70}
        diet_history = {
            "carb_intake_percent": 45,
            "fiber_grams": 30,
            "protein_grams": 70,  # 70/70 = 1.0 g/kg (adequate)
            "calorie_excess": False
        }
        diagnoses = engine.identify_nutrition_diagnoses(
            labs=labs,
            anthropometry=anthropometry,
            diet_history=diet_history
        )
        
        assert len(diagnoses) == 0
    
    def test_missing_data_handling(self):
        """Test that missing data doesn't cause errors."""
        engine = DiagnosisEngine()
        
        diagnoses = engine.identify_nutrition_diagnoses()
        
        assert isinstance(diagnoses, list)
        assert len(diagnoses) == 0


class TestProcessAssessment:
    """Test suite for process_assessment method."""
    
    def test_process_assessment_complete(self):
        """Test processing a complete assessment."""
        engine = DiagnosisEngine()
        
        assessment_context = AssessmentContext(
            client_id=uuid4(),
            assessment_id=uuid4(),
            assessment_snapshot={
                "client_context": {
                    "age": 45,
                    "gender": "Male",
                    "height_cm": 170,
                    "weight_kg": 85,
                    "bmi": 29.4
                },
                "clinical_data": {
                    "labs": {
                        "HbA1c": 7.5,
                        "cholesterol": 220
                    },
                    "vitals": {
                        "bp_systolic": 140,
                        "bp_diastolic": 90
                    }
                },
                "diet_data": {
                    "diet_history": {
                        "carb_intake_percent": 60,
                        "fiber_grams": 15
                    }
                }
            }
        )
        
        diagnosis_context = engine.process_assessment(assessment_context)
        
        assert diagnosis_context.assessment_id == assessment_context.assessment_id
        assert len(diagnosis_context.medical_conditions) > 0
        assert len(diagnosis_context.nutrition_diagnoses) > 0
        
        # Verify medical conditions
        medical_ids = [c["diagnosis_id"] for c in diagnosis_context.medical_conditions]
        assert "type_2_diabetes" in medical_ids
        assert "dyslipidemia" in medical_ids
        assert "hypertension" in medical_ids
        
        # Verify nutrition diagnoses
        nutrition_ids = [d["diagnosis_id"] for d in diagnosis_context.nutrition_diagnoses]
        assert "excess_carbohydrate_intake" in nutrition_ids
        assert "inadequate_fiber_intake" in nutrition_ids
    
    def test_process_assessment_missing_assessment_id(self):
        """Test that missing assessment_id raises error."""
        engine = DiagnosisEngine()
        
        assessment_context = AssessmentContext(
            client_id=uuid4(),
            assessment_id=None,  # Missing
            assessment_snapshot={}
        )
        
        with pytest.raises(ValueError, match="assessment_id is required"):
            engine.process_assessment(assessment_context)
    
    def test_process_assessment_empty_snapshot(self):
        """Test processing assessment with empty snapshot."""
        engine = DiagnosisEngine()
        
        assessment_context = AssessmentContext(
            client_id=uuid4(),
            assessment_id=uuid4(),
            assessment_snapshot={}
        )
        
        diagnosis_context = engine.process_assessment(assessment_context)
        
        assert diagnosis_context.assessment_id == assessment_context.assessment_id
        assert len(diagnosis_context.medical_conditions) == 0
        assert len(diagnosis_context.nutrition_diagnoses) == 0
    
    def test_process_assessment_nested_structure(self):
        """Test processing assessment with nested data structure."""
        engine = DiagnosisEngine()
        
        assessment_context = AssessmentContext(
            client_id=uuid4(),
            assessment_id=uuid4(),
            assessment_snapshot={
                "clinical_data": {
                    "labs": {"HbA1c": 7.5},
                    "vitals": {"bp_systolic": 140}
                },
                "client_context": {"bmi": 32}
            }
        )
        
        diagnosis_context = engine.process_assessment(assessment_context)
        
        assert len(diagnosis_context.medical_conditions) > 0
    
    def test_process_assessment_flat_structure(self):
        """Test processing assessment with flat data structure."""
        engine = DiagnosisEngine()
        
        assessment_context = AssessmentContext(
            client_id=uuid4(),
            assessment_id=uuid4(),
            assessment_snapshot={
                "labs": {"HbA1c": 7.5},
                "bmi": 32
            }
        )
        
        diagnosis_context = engine.process_assessment(assessment_context)
        
        assert len(diagnosis_context.medical_conditions) > 0


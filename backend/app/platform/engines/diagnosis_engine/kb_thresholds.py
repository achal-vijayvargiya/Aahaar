"""
Knowledge Base Thresholds for Diagnosis Engine.

Simple hardcoded KB thresholds for rule-based diagnosis.
Can be refactored to use database KB later.
"""
from typing import Dict, Any


# Medical Condition Thresholds
MEDICAL_THRESHOLDS: Dict[str, Dict[str, Any]] = {
    "type_2_diabetes": {
        "HbA1c": {"min": 6.5, "severity_mild": 7.0, "severity_moderate": 8.0},
        "FBS": {"min": 126},
        "description": "Type 2 Diabetes Mellitus"
    },
    "prediabetes": {
        "HbA1c": {"min": 5.7, "max": 6.4},
        "FBS": {"min": 100, "max": 125},
        "description": "Prediabetes"
    },
    "hypertension": {
        "bp_systolic": {"min": 130},
        "bp_diastolic": {"min": 80},
        "description": "Hypertension"
    },
    "dyslipidemia": {
        "cholesterol": {"min": 200},
        "triglycerides": {"min": 150},
        "description": "Dyslipidemia"
    },
    "obesity": {
        "bmi": {"min": 30, "severity_mild": 35, "severity_moderate": 40},
        "description": "Obesity"
    },
    "overweight": {
        "bmi": {"min": 25, "max": 29.9},
        "description": "Overweight"
    }
}


# Nutrition Diagnosis Thresholds
NUTRITION_THRESHOLDS: Dict[str, Dict[str, Any]] = {
    "excess_carbohydrate_intake": {
        "HbA1c_threshold": 7.0,
        "carb_intake_percent_min": 50,
        "description": "Excess Carbohydrate Intake"
    },
    "inadequate_fiber_intake": {
        "fiber_grams_max": 25,  # Less than 25g per day
        "description": "Inadequate Fiber Intake"
    },
    "excessive_calorie_intake": {
        "bmi_min": 25,
        "calorie_excess": True,
        "description": "Excessive Calorie Intake"
    },
    "inadequate_protein_intake": {
        "protein_grams_per_kg_max": 0.8,  # Less than 0.8g per kg body weight
        "description": "Inadequate Protein Intake"
    }
}


def get_medical_threshold(condition_id: str) -> Dict[str, Any]:
    """Get threshold values for a medical condition."""
    return MEDICAL_THRESHOLDS.get(condition_id, {})


def get_nutrition_threshold(diagnosis_id: str) -> Dict[str, Any]:
    """Get threshold values for a nutrition diagnosis."""
    return NUTRITION_THRESHOLDS.get(diagnosis_id, {})


"""
Import Knowledge Base data from hardcoded sources.

Run from backend directory:
    python scripts/import_kb_data.py
"""
import sys
import importlib.util
from pathlib import Path

# Ensure we're in the backend directory
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal
from app.platform.data.repositories.kb_medical_condition_repository import KBMedicalConditionRepository
from app.platform.data.repositories.kb_nutrition_diagnosis_repository import KBNutritionDiagnosisRepository
from app.platform.data.repositories.kb_mnt_rule_repository import KBMNTRuleRepository
from app.platform.data.repositories.kb_lab_threshold_repository import KBLabThresholdRepository

# Import hardcoded data directly (avoid circular imports)
spec = importlib.util.spec_from_file_location(
    "kb_mnt_rules",
    backend_dir / "app" / "platform" / "engines" / "mnt_engine" / "kb_mnt_rules.py"
)
kb_mnt_rules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kb_mnt_rules)

MNT_RULES = kb_mnt_rules.MNT_RULES
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def import_medical_conditions(db):
    """Import medical conditions from hardcoded thresholds."""
    repo = KBMedicalConditionRepository(db)
    
    conditions_data = [
        {
            "condition_id": "type_2_diabetes",
            "display_name": "Type 2 Diabetes",
            "category": "metabolic",
            "description": "Chronic hyperglycemia due to insulin resistance and/or insulin deficiency",
            "critical_labs": ["HbA1c", "FBS", "PPBS"],
            "severity_thresholds": {
                "HbA1c": {
                    "mild": {"min": 6.5, "max": 7.0, "unit": "%"},
                    "moderate": {"min": 7.0, "max": 8.0, "unit": "%"},
                    "severe": {"min": 8.0, "max": None, "unit": "%"}
                },
                "FBS": {
                    "mild": {"min": 126, "max": 140, "unit": "mg/dL"},
                    "moderate": {"min": 140, "max": 180, "unit": "mg/dL"},
                    "severe": {"min": 180, "max": None, "unit": "mg/dL"}
                }
            },
            "associated_risks": ["insulin_resistance", "cardiovascular_disease", "nephropathy"],
            "nutrition_focus_areas": ["carbohydrate_control", "glycemic_control", "fiber_intake"],
            "red_flags": ["hypoglycemia", "very_high_glucose", "ketoacidosis"],
            "source": "American Diabetes Association",
            "source_reference": "ADA Standards of Medical Care in Diabetes 2024",
            "version": "1.0",
            "status": "active"
        },
        {
            "condition_id": "prediabetes",
            "display_name": "Prediabetes",
            "category": "metabolic",
            "description": "Blood glucose levels higher than normal but not yet diabetes",
            "critical_labs": ["HbA1c", "FBS"],
            "severity_thresholds": {
                "HbA1c": {
                    "mild": {"min": 5.7, "max": 6.4, "unit": "%"}
                },
                "FBS": {
                    "mild": {"min": 100, "max": 125, "unit": "mg/dL"}
                }
            },
            "associated_risks": ["progression_to_diabetes"],
            "nutrition_focus_areas": ["carbohydrate_control", "weight_management"],
            "red_flags": [],
            "source": "American Diabetes Association",
            "source_reference": "ADA Standards of Medical Care in Diabetes 2024",
            "version": "1.0",
            "status": "active"
        },
        {
            "condition_id": "hypertension",
            "display_name": "Hypertension",
            "category": "cardiovascular",
            "description": "High blood pressure",
            "critical_labs": [],
            "severity_thresholds": {
                "bp_systolic": {
                    "mild": {"min": 130, "max": 139, "unit": "mmHg"},
                    "moderate": {"min": 140, "max": 159, "unit": "mmHg"},
                    "severe": {"min": 160, "max": None, "unit": "mmHg"}
                },
                "bp_diastolic": {
                    "mild": {"min": 80, "max": 89, "unit": "mmHg"},
                    "moderate": {"min": 90, "max": 99, "unit": "mmHg"},
                    "severe": {"min": 100, "max": None, "unit": "mmHg"}
                }
            },
            "associated_risks": ["cardiovascular_disease", "stroke", "kidney_disease"],
            "nutrition_focus_areas": ["sodium_restriction", "potassium_intake", "weight_management"],
            "red_flags": ["very_high_bp", "hypertensive_crisis"],
            "source": "American Heart Association",
            "source_reference": "AHA/ACC Hypertension Guidelines 2017",
            "version": "1.0",
            "status": "active"
        },
        {
            "condition_id": "dyslipidemia",
            "display_name": "Dyslipidemia",
            "category": "cardiovascular",
            "description": "Abnormal lipid levels in blood",
            "critical_labs": ["cholesterol", "triglycerides", "LDL", "HDL"],
            "severity_thresholds": {
                "cholesterol": {
                    "mild": {"min": 200, "max": 239, "unit": "mg/dL"},
                    "moderate": {"min": 240, "max": None, "unit": "mg/dL"}
                },
                "triglycerides": {
                    "mild": {"min": 150, "max": 199, "unit": "mg/dL"},
                    "moderate": {"min": 200, "max": None, "unit": "mg/dL"}
                }
            },
            "associated_risks": ["cardiovascular_disease", "atherosclerosis"],
            "nutrition_focus_areas": ["fat_modification", "fiber_intake"],
            "red_flags": [],
            "source": "American Heart Association",
            "source_reference": "AHA Cholesterol Guidelines",
            "version": "1.0",
            "status": "active"
        },
        {
            "condition_id": "obesity",
            "display_name": "Obesity",
            "category": "metabolic",
            "description": "Excessive body fat accumulation",
            "critical_labs": [],
            "severity_thresholds": {
                "bmi": {
                    "mild": {"min": 30, "max": 34.9, "unit": "kg/m²"},
                    "moderate": {"min": 35, "max": 39.9, "unit": "kg/m²"},
                    "severe": {"min": 40, "max": None, "unit": "kg/m²"}
                }
            },
            "associated_risks": ["diabetes", "cardiovascular_disease", "sleep_apnea"],
            "nutrition_focus_areas": ["calorie_restriction", "weight_management"],
            "red_flags": [],
            "source": "WHO",
            "source_reference": "WHO Obesity Classification",
            "version": "1.0",
            "status": "active"
        },
        {
            "condition_id": "overweight",
            "display_name": "Overweight",
            "category": "metabolic",
            "description": "Excess body weight",
            "critical_labs": [],
            "severity_thresholds": {
                "bmi": {
                    "mild": {"min": 25, "max": 29.9, "unit": "kg/m²"}
                }
            },
            "associated_risks": ["obesity", "diabetes"],
            "nutrition_focus_areas": ["weight_management"],
            "red_flags": [],
            "source": "WHO",
            "source_reference": "WHO BMI Classification",
            "version": "1.0",
            "status": "active"
        }
    ]
    
    imported = 0
    updated = 0
    
    for condition_data in conditions_data:
        existing = repo.get_by_condition_id(condition_data["condition_id"])
        if existing:
            logger.info(f"Updating {condition_data['condition_id']}")
            repo.update_by_condition_id(condition_data["condition_id"], condition_data)
            updated += 1
        else:
            logger.info(f"Creating {condition_data['condition_id']}")
            repo.create(condition_data)
            imported += 1
    
    logger.info(f"Medical Conditions: {imported} imported, {updated} updated")
    return imported + updated


def import_nutrition_diagnoses(db):
    """Import nutrition diagnoses from hardcoded thresholds."""
    repo = KBNutritionDiagnosisRepository(db)
    
    diagnoses_data = [
        {
            "diagnosis_id": "excess_carbohydrate_intake",
            "problem_statement": "Excessive carbohydrate intake leading to poor glycemic control",
            "trigger_conditions": ["type_2_diabetes", "prediabetes"],
            "trigger_labs": {
                "HbA1c": {"min": 7.0, "unit": "%"}
            },
            "trigger_diet_history": {
                "carb_intake_percent": {"min": 50, "unit": "%"}
            },
            "severity_logic": "distance_from_threshold",
            "evidence_types": ["lab", "diet_history"],
            "affected_domains": ["macros", "food_selection", "meal_timing"],
            "linked_conditions": ["type_2_diabetes", "prediabetes"],
            "source": "Academy of Nutrition and Dietetics",
            "source_reference": "eNCPT 2024",
            "version": "1.0",
            "status": "active"
        },
        {
            "diagnosis_id": "inadequate_fiber_intake",
            "problem_statement": "Inadequate dietary fiber intake",
            "trigger_conditions": [],
            "trigger_diet_history": {
                "fiber_grams": {"max": 25, "unit": "g"}
            },
            "severity_logic": "absolute_value",
            "evidence_types": ["diet_history"],
            "affected_domains": ["macros", "food_selection"],
            "linked_conditions": [],
            "source": "Academy of Nutrition and Dietetics",
            "source_reference": "eNCPT 2024",
            "version": "1.0",
            "status": "active"
        },
        {
            "diagnosis_id": "excessive_calorie_intake",
            "problem_statement": "Excessive calorie intake leading to weight gain",
            "trigger_conditions": ["obesity", "overweight"],
            "trigger_anthropometry": {
                "bmi": {"min": 25, "unit": "kg/m²"}
            },
            "trigger_diet_history": {
                "calorie_excess": {"value": True}
            },
            "severity_logic": "distance_from_threshold",
            "evidence_types": ["anthropometry", "diet_history"],
            "affected_domains": ["macros"],
            "linked_conditions": ["obesity", "overweight"],
            "source": "Academy of Nutrition and Dietetics",
            "source_reference": "eNCPT 2024",
            "version": "1.0",
            "status": "active"
        },
        {
            "diagnosis_id": "inadequate_protein_intake",
            "problem_statement": "Inadequate protein intake for body weight",
            "trigger_conditions": [],
            "trigger_diet_history": {
                "protein_grams_per_kg": {"max": 0.8, "unit": "g/kg"}
            },
            "severity_logic": "absolute_value",
            "evidence_types": ["diet_history", "anthropometry"],
            "affected_domains": ["macros", "food_selection"],
            "linked_conditions": [],
            "source": "Academy of Nutrition and Dietetics",
            "source_reference": "eNCPT 2024",
            "version": "1.0",
            "status": "active"
        }
    ]
    
    imported = 0
    updated = 0
    
    for diagnosis_data in diagnoses_data:
        existing = repo.get_by_diagnosis_id(diagnosis_data["diagnosis_id"])
        if existing:
            logger.info(f"Updating {diagnosis_data['diagnosis_id']}")
            repo.update_by_diagnosis_id(diagnosis_data["diagnosis_id"], diagnosis_data)
            updated += 1
        else:
            logger.info(f"Creating {diagnosis_data['diagnosis_id']}")
            repo.create(diagnosis_data)
            imported += 1
    
    logger.info(f"Nutrition Diagnoses: {imported} imported, {updated} updated")
    return imported + updated


def import_mnt_rules(db):
    """Import MNT rules from hardcoded rules."""
    repo = KBMNTRuleRepository(db)
    
    imported = 0
    updated = 0
    
    for rule_id, rule_data in MNT_RULES.items():
        existing = repo.get_by_rule_id(rule_id)
        
        mnt_rule_data = {
            "rule_id": rule_data["rule_id"],
            "applies_to_diagnoses": rule_data["applies_to_diagnoses"],
            "priority_level": rule_data["priority_level"],
            "priority_label": rule_data["priority"],
            "macro_constraints": rule_data.get("macro_constraints", {}),
            "micro_constraints": rule_data.get("micro_constraints", {}),
            "food_exclusions": rule_data.get("food_exclusions", []),
            "food_inclusions": rule_data.get("food_inclusions", []),
            "meal_distribution": rule_data.get("meal_distribution", {}),
            "override_allowed": False,
            "conflict_resolution": "higher_priority_wins",
            "evidence_level": "B",  # Default, should be updated
            "source": "Clinical Guidelines",
            "source_reference": "MNT Guidelines",
            "version": "1.0",
            "status": "active"
        }
        
        if existing:
            logger.info(f"Updating {rule_id}")
            repo.update_by_rule_id(rule_id, mnt_rule_data)
            updated += 1
        else:
            logger.info(f"Creating {rule_id}")
            repo.create(mnt_rule_data)
            imported += 1
    
    logger.info(f"MNT Rules: {imported} imported, {updated} updated")
    return imported + updated


def import_lab_thresholds(db):
    """Import lab thresholds from hardcoded data."""
    repo = KBLabThresholdRepository(db)
    
    thresholds_data = [
        {
            "lab_name": "HbA1c",
            "display_name": "Hemoglobin A1c",
            "normal_range": {"min": 4.0, "max": 5.6, "unit": "%"},
            "abnormal_ranges": {
                "mild": {"min": 5.7, "max": 6.4, "unit": "%"},
                "moderate": {"min": 6.5, "max": 6.9, "unit": "%"},
                "severe": {"min": 7.0, "max": None, "unit": "%"}
            },
            "units": ["%"],
            "conversion_factors": {"%": 1.0},
            "source": "American Diabetes Association",
            "source_reference": "ADA Standards 2024",
            "version": "1.0",
            "status": "active"
        },
        {
            "lab_name": "FBS",
            "display_name": "Fasting Blood Sugar",
            "normal_range": {"min": 70, "max": 99, "unit": "mg/dL"},
            "abnormal_ranges": {
                "mild": {"min": 100, "max": 125, "unit": "mg/dL"},
                "moderate": {"min": 126, "max": None, "unit": "mg/dL"}
            },
            "units": ["mg/dL", "mmol/L"],
            "conversion_factors": {"mg/dL": 1.0, "mmol/L": 0.0555},
            "source": "American Diabetes Association",
            "source_reference": "ADA Standards 2024",
            "version": "1.0",
            "status": "active"
        },
        {
            "lab_name": "cholesterol",
            "display_name": "Total Cholesterol",
            "normal_range": {"min": 0, "max": 199, "unit": "mg/dL"},
            "abnormal_ranges": {
                "mild": {"min": 200, "max": 239, "unit": "mg/dL"},
                "moderate": {"min": 240, "max": None, "unit": "mg/dL"}
            },
            "units": ["mg/dL", "mmol/L"],
            "conversion_factors": {"mg/dL": 1.0, "mmol/L": 0.0259},
            "source": "American Heart Association",
            "source_reference": "AHA Cholesterol Guidelines",
            "version": "1.0",
            "status": "active"
        },
        {
            "lab_name": "triglycerides",
            "display_name": "Triglycerides",
            "normal_range": {"min": 0, "max": 149, "unit": "mg/dL"},
            "abnormal_ranges": {
                "mild": {"min": 150, "max": 199, "unit": "mg/dL"},
                "moderate": {"min": 200, "max": None, "unit": "mg/dL"}
            },
            "units": ["mg/dL", "mmol/L"],
            "conversion_factors": {"mg/dL": 1.0, "mmol/L": 0.0113},
            "source": "American Heart Association",
            "source_reference": "AHA Lipid Guidelines",
            "version": "1.0",
            "status": "active"
        },
        {
            "lab_name": "bmi",
            "display_name": "Body Mass Index",
            "normal_range": {"min": 18.5, "max": 24.9, "unit": "kg/m²"},
            "abnormal_ranges": {
                "mild": {"min": 25, "max": 29.9, "unit": "kg/m²"},
                "moderate": {"min": 30, "max": 34.9, "unit": "kg/m²"},
                "severe": {"min": 35, "max": None, "unit": "kg/m²"}
            },
            "units": ["kg/m²"],
            "conversion_factors": {"kg/m²": 1.0},
            "source": "WHO",
            "source_reference": "WHO BMI Classification",
            "version": "1.0",
            "status": "active"
        }
    ]
    
    imported = 0
    updated = 0
    
    for threshold_data in thresholds_data:
        existing = repo.get_by_lab_name(threshold_data["lab_name"])
        if existing:
            logger.info(f"Updating {threshold_data['lab_name']}")
            repo.update_by_lab_name(threshold_data["lab_name"], threshold_data)
            updated += 1
        else:
            logger.info(f"Creating {threshold_data['lab_name']}")
            repo.create(threshold_data)
            imported += 1
    
    logger.info(f"Lab Thresholds: {imported} imported, {updated} updated")
    return imported + updated


def main():
    """Main import function."""
    db = SessionLocal()
    
    try:
        logger.info("=" * 70)
        logger.info("IMPORTING KNOWLEDGE BASE FROM HARDCODED DATA")
        logger.info("=" * 70)
        
        total = 0
        total += import_medical_conditions(db)
        total += import_nutrition_diagnoses(db)
        total += import_mnt_rules(db)
        total += import_lab_thresholds(db)
        
        logger.info("=" * 70)
        logger.info(f"✓ Successfully imported {total} KB entries")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"Error during import: {str(e)}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()


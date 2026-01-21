"""
Manual Knowledge Base Data Import Script.

Allows manual entry of KB data via JSON files or direct Python dictionaries.
Use this for:
- Small batches of data
- Expert-validated data
- Testing and development

Usage:
    python -m app.platform.data.scripts.import_kb_manual --kb medical_conditions --file data/medical_conditions.json
    python -m app.platform.data.scripts.import_kb_manual --kb mnt_rules --data '{"rule_id": "test", ...}'
"""
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.database import SessionLocal
from app.platform.data.repositories.kb_medical_condition_repository import KBMedicalConditionRepository
from app.platform.data.repositories.kb_nutrition_diagnosis_repository import KBNutritionDiagnosisRepository
from app.platform.data.repositories.kb_mnt_rule_repository import KBMNTRuleRepository
from app.platform.data.repositories.kb_lab_threshold_repository import KBLabThresholdRepository
from app.platform.data.repositories.kb_medical_modifier_rule_repository import KBMedicalModifierRuleRepository
from app.platform.data.repositories.kb_food_condition_compatibility_repository import KBFoodConditionCompatibilityRepository
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def import_from_json_file(db, kb_type: str, file_path: str, update_existing: bool = False):
    """
    Import KB data from JSON file.
    
    Args:
        db: Database session
        kb_type: KB type (medical_conditions, nutrition_diagnoses, mnt_rules, etc.)
        file_path: Path to JSON file
        update_existing: If True, update existing records; if False, skip
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle both single object and array
    if isinstance(data, dict):
        data = [data]
    elif not isinstance(data, list):
        raise ValueError("JSON must contain an object or array of objects")
    
    return import_data(db, kb_type, data, update_existing)


def import_data(db, kb_type: str, data_list: List[Dict[str, Any]], update_existing: bool = False):
    """
    Import KB data from list of dictionaries.
    
    Args:
        db: Database session
        kb_type: KB type
        data_list: List of data dictionaries
        update_existing: If True, update existing records
    """
    repos = {
        "medical_conditions": KBMedicalConditionRepository(db),
        "nutrition_diagnoses": KBNutritionDiagnosisRepository(db),
        "mnt_rules": KBMNTRuleRepository(db),
        "lab_thresholds": KBLabThresholdRepository(db),
        "medical_modifier_rules": KBMedicalModifierRuleRepository(db),
        "food_condition_compatibility": KBFoodConditionCompatibilityRepository(db),
    }
    
    if kb_type not in repos:
        raise ValueError(f"Unknown KB type: {kb_type}. Available: {list(repos.keys())}")
    
    repo = repos[kb_type]
    imported = 0
    updated = 0
    skipped = 0
    errors = []
    
    for item_data in data_list:
        try:
            # Get identifier based on KB type
            identifier = get_identifier(kb_type, item_data)
            
            # Check if exists
            existing = get_existing_record(repo, kb_type, identifier)
            
            if existing:
                if update_existing:
                    logger.info(f"Updating {kb_type}: {identifier}")
                    update_record(repo, kb_type, existing, item_data)
                    updated += 1
                else:
                    logger.info(f"Skipping existing {kb_type}: {identifier}")
                    skipped += 1
            else:
                logger.info(f"Creating {kb_type}: {identifier}")
                repo.create(item_data)
                imported += 1
                
        except Exception as e:
            error_msg = f"Error importing {kb_type} item: {str(e)}"
            logger.error(error_msg)
            errors.append({"item": item_data, "error": error_msg})
    
    logger.info(f"\n{kb_type.upper()} Import Summary:")
    logger.info(f"  Imported: {imported}")
    logger.info(f"  Updated: {updated}")
    logger.info(f"  Skipped: {skipped}")
    if errors:
        logger.warning(f"  Errors: {len(errors)}")
        for error in errors[:5]:  # Show first 5 errors
            logger.warning(f"    - {error['error']}")
    
    return {
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "errors": len(errors)
    }


def get_identifier(kb_type: str, data: Dict[str, Any]) -> str:
    """Get identifier field name for KB type."""
    identifier_map = {
        "medical_conditions": "condition_id",
        "nutrition_diagnoses": "diagnosis_id",
        "mnt_rules": "rule_id",
        "lab_thresholds": "lab_name",
        "medical_modifier_rules": "modifier_id",
        "food_condition_compatibility": f"{data.get('food_id')}:{data.get('condition_id')}",
    }
    field = identifier_map.get(kb_type)
    if kb_type == "food_condition_compatibility":
        return field
    return data.get(field, "unknown")


def get_existing_record(repo, kb_type: str, identifier: str):
    """Get existing record by identifier."""
    methods = {
        "medical_conditions": lambda: repo.get_by_condition_id(identifier),
        "nutrition_diagnoses": lambda: repo.get_by_diagnosis_id(identifier),
        "mnt_rules": lambda: repo.get_by_rule_id(identifier),
        "lab_thresholds": lambda: repo.get_by_lab_name(identifier),
        "medical_modifier_rules": lambda: repo.get_by_modifier_id(identifier),
        "food_condition_compatibility": lambda: None,  # Special handling needed
    }
    method = methods.get(kb_type)
    if method:
        return method()
    return None


def update_record(repo, kb_type: str, existing, data: Dict[str, Any]):
    """Update existing record."""
    identifier = get_identifier(kb_type, data)
    update_methods = {
        "medical_conditions": lambda: repo.update_by_condition_id(identifier, data),
        "nutrition_diagnoses": lambda: repo.update_by_diagnosis_id(identifier, data),
        "mnt_rules": lambda: repo.update_by_rule_id(identifier, data),
        "lab_thresholds": lambda: repo.update_by_lab_name(identifier, data),
        "medical_modifier_rules": lambda: repo.update_by_modifier_id(identifier, data),
        "food_condition_compatibility": lambda: repo.update(existing.id, data),
    }
    method = update_methods.get(kb_type)
    if method:
        return method()
    return repo.update(existing.id, data)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Manual KB data import')
    parser.add_argument(
        '--kb',
        type=str,
        required=True,
        choices=['medical_conditions', 'nutrition_diagnoses', 'mnt_rules', 
                 'lab_thresholds', 'medical_modifier_rules', 'food_condition_compatibility'],
        help='KB type to import'
    )
    parser.add_argument(
        '--file',
        type=str,
        help='JSON file path'
    )
    parser.add_argument(
        '--data',
        type=str,
        help='JSON data string (single object or array)'
    )
    parser.add_argument(
        '--update',
        action='store_true',
        help='Update existing records instead of skipping'
    )
    
    args = parser.parse_args()
    
    if not args.file and not args.data:
        parser.error("Either --file or --data must be provided")
    
    db = SessionLocal()
    
    try:
        if args.file:
            result = import_from_json_file(db, args.kb, args.file, args.update)
        else:
            data = json.loads(args.data)
            if isinstance(data, dict):
                data = [data]
            result = import_data(db, args.kb, data, args.update)
        
        logger.info(f"\n✓ Import completed: {result}")
        
    except Exception as e:
        logger.error(f"Error during import: {str(e)}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()


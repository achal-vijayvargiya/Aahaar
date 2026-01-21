"""
Validate Medical Conditions JSON file before import.

Checks:
- JSON structure is valid
- Required fields are present
- Thresholds are logical
- No duplicate condition_ids
- Units are correct

Usage:
    python scripts/validate_medical_conditions_json.py
"""
import sys
import json
from pathlib import Path
from typing import Dict, List, Any

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

def validate_json_structure(data: List[Dict[str, Any]]) -> List[str]:
    """Validate JSON structure and required fields."""
    errors = []
    required_fields = [
        "condition_id",
        "display_name",
        "category",
        "severity_thresholds"
    ]
    
    condition_ids = set()
    
    for idx, condition in enumerate(data, 1):
        # Check required fields
        for field in required_fields:
            if field not in condition:
                errors.append(f"Condition #{idx}: Missing required field '{field}'")
        
        # Check condition_id is unique
        condition_id = condition.get("condition_id")
        if condition_id:
            if condition_id in condition_ids:
                errors.append(f"Condition #{idx}: Duplicate condition_id '{condition_id}'")
            condition_ids.add(condition_id)
        
        # Check severity_thresholds structure
        thresholds = condition.get("severity_thresholds", {})
        if not thresholds:
            errors.append(f"Condition #{idx} ({condition_id}): No severity_thresholds defined")
        else:
            for metric_name, metric_thresholds in thresholds.items():
                if not isinstance(metric_thresholds, dict):
                    errors.append(f"Condition #{idx} ({condition_id}): Invalid threshold structure for '{metric_name}'")
                    continue
                
                # Check severity levels
                for severity_level in ["mild", "moderate", "severe"]:
                    if severity_level in metric_thresholds:
                        severity_data = metric_thresholds[severity_level]
                        if not isinstance(severity_data, dict):
                            errors.append(f"Condition #{idx} ({condition_id}): Invalid {severity_level} threshold for '{metric_name}'")
                            continue
                        
                        # Check min/max
                        if "min" not in severity_data and "max" not in severity_data:
                            errors.append(f"Condition #{idx} ({condition_id}): {severity_level} threshold for '{metric_name}' missing both min and max")
                        
                        # Check unit
                        if "unit" not in severity_data:
                            errors.append(f"Condition #{idx} ({condition_id}): {severity_level} threshold for '{metric_name}' missing unit")
    
    return errors


def validate_threshold_logic(data: List[Dict[str, Any]]) -> List[str]:
    """Validate threshold logic (mild < moderate < severe)."""
    errors = []
    
    for idx, condition in enumerate(data, 1):
        condition_id = condition.get("condition_id", f"#{idx}")
        thresholds = condition.get("severity_thresholds", {})
        
        for metric_name, metric_thresholds in thresholds.items():
            # Get severity levels present
            severities = []
            if "mild" in metric_thresholds:
                severities.append(("mild", metric_thresholds["mild"]))
            if "moderate" in metric_thresholds:
                severities.append(("moderate", metric_thresholds["moderate"]))
            if "severe" in metric_thresholds:
                severities.append(("severe", metric_thresholds["severe"]))
            
            # Check ordering
            for i in range(len(severities) - 1):
                current_severity, current_data = severities[i]
                next_severity, next_data = severities[i + 1]
                
                current_max = current_data.get("max")
                next_min = next_data.get("min")
                
                if current_max is not None and next_min is not None:
                    # Allow small overlap (0.1) for rounding
                    if current_max > next_min + 0.1:
                        errors.append(
                            f"Condition {condition_id}: {metric_name} - "
                            f"{current_severity}.max ({current_max}) > {next_severity}.min ({next_min})"
                        )
    
    return errors


def validate_units(data: List[Dict[str, Any]]) -> List[str]:
    """Validate units are correct."""
    errors = []
    warnings = []
    
    # Expected units for common metrics
    expected_units = {
        "HbA1c": "%",
        "FBS": "mg/dL",
        "PPBS": "mg/dL",
        "OGTT_1h": "mg/dL",
        "OGTT_2h": "mg/dL",
        "bmi": "kg/m²",
        "bp_systolic": "mmHg",
        "bp_diastolic": "mmHg",
        "cholesterol": "mg/dL",
        "triglycerides": "mg/dL",
        "hdl": "mg/dL",
        "ldl": "mg/dL",
        "waist_circumference": "cm"
    }
    
    for idx, condition in enumerate(data, 1):
        condition_id = condition.get("condition_id", f"#{idx}")
        thresholds = condition.get("severity_thresholds", {})
        
        for metric_name, metric_thresholds in thresholds.items():
            # Check if we know expected unit
            if metric_name in expected_units:
                expected_unit = expected_units[metric_name]
                
                # Check all severity levels
                for severity_level in ["mild", "moderate", "severe"]:
                    if severity_level in metric_thresholds:
                        actual_unit = metric_thresholds[severity_level].get("unit")
                        if actual_unit != expected_unit:
                            errors.append(
                                f"Condition {condition_id}: {metric_name} - "
                                f"Expected unit '{expected_unit}', got '{actual_unit}'"
                            )
            else:
                warnings.append(
                    f"Condition {condition_id}: Unknown metric '{metric_name}' - "
                    f"cannot validate unit"
                )
    
    return errors, warnings


def validate_critical_labs(data: List[Dict[str, Any]]) -> List[str]:
    """Validate critical_labs matches thresholds."""
    warnings = []
    
    for idx, condition in enumerate(data, 1):
        condition_id = condition.get("condition_id", f"#{idx}")
        critical_labs = condition.get("critical_labs", [])
        thresholds = condition.get("severity_thresholds", {})
        
        # Check if thresholds have metrics not in critical_labs
        threshold_metrics = set(thresholds.keys())
        critical_labs_set = set(critical_labs)
        
        # BMI-based conditions may have empty critical_labs
        bmi_metrics = {"bmi", "bp_systolic", "bp_diastolic", "waist_circumference"}
        non_lab_metrics = threshold_metrics & bmi_metrics
        
        # Lab metrics should be in critical_labs
        lab_metrics = threshold_metrics - bmi_metrics
        missing_in_critical = lab_metrics - critical_labs_set
        
        if missing_in_critical:
            warnings.append(
                f"Condition {condition_id}: Metrics {missing_in_critical} in thresholds "
                f"but not in critical_labs"
            )
    
    return warnings


def main():
    """Main validation function."""
    json_file = backend_dir / "Resource" / "Solution Docs" / "KB_Docs" / "medical_conditions_kb_complete.json"
    
    if not json_file.exists():
        print(f"❌ JSON file not found: {json_file}")
        return 1
    
    print("=" * 70)
    print("MEDICAL CONDITIONS KB - JSON VALIDATION")
    print("=" * 70)
    print(f"\nValidating: {json_file}\n")
    
    # Load JSON
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ JSON is valid")
        print(f"✅ Found {len(data)} conditions\n")
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return 1
    
    # Validate structure
    print("Validating structure...")
    structure_errors = validate_json_structure(data)
    if structure_errors:
        print(f"❌ Found {len(structure_errors)} structure errors:")
        for error in structure_errors:
            print(f"  - {error}")
    else:
        print("✅ Structure is valid")
    
    # Validate threshold logic
    print("\nValidating threshold logic...")
    logic_errors = validate_threshold_logic(data)
    if logic_errors:
        print(f"❌ Found {len(logic_errors)} threshold logic errors:")
        for error in logic_errors:
            print(f"  - {error}")
    else:
        print("✅ Threshold logic is valid")
    
    # Validate units
    print("\nValidating units...")
    unit_errors, unit_warnings = validate_units(data)
    if unit_errors:
        print(f"❌ Found {len(unit_errors)} unit errors:")
        for error in unit_errors:
            print(f"  - {error}")
    else:
        print("✅ Units are valid")
    
    if unit_warnings:
        print(f"⚠️  Found {len(unit_warnings)} unit warnings:")
        for warning in unit_warnings[:5]:  # Show first 5
            print(f"  - {warning}")
        if len(unit_warnings) > 5:
            print(f"  ... and {len(unit_warnings) - 5} more")
    
    # Validate critical_labs
    print("\nValidating critical_labs...")
    critical_labs_warnings = validate_critical_labs(data)
    if critical_labs_warnings:
        print(f"⚠️  Found {len(critical_labs_warnings)} warnings:")
        for warning in critical_labs_warnings:
            print(f"  - {warning}")
    else:
        print("✅ critical_labs are consistent")
    
    # Summary
    print("\n" + "=" * 70)
    total_errors = len(structure_errors) + len(logic_errors) + len(unit_errors)
    if total_errors == 0:
        print("✅ VALIDATION PASSED - Ready for import!")
        print("=" * 70)
        return 0
    else:
        print(f"❌ VALIDATION FAILED - {total_errors} errors found")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())


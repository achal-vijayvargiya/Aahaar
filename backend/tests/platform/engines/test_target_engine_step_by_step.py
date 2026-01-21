"""
Step-by-step test for Target Engine calculations.

This test file provides detailed step-by-step verification of all calculation formulas
used in the Target Engine, showing intermediate values and final results.

Can use real client profiles from the database or synthetic test data.

Usage:
    # Run all tests (uses real DB clients if available):
    pytest tests/platform/engines/test_target_engine_step_by_step.py -v -s
    
    # Run only the real client profile test:
    pytest tests/platform/engines/test_target_engine_step_by_step.py::TestTargetEngineStepByStep::test_real_client_profiles_from_db -v -s
    
    # Run with specific logging level:
    pytest tests/platform/engines/test_target_engine_step_by_step.py -v -s --log-cli-level=DEBUG
"""
import logging
from uuid import uuid4
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

import pytest

from app.platform.engines.target_engine.target_engine import TargetEngine
from app.platform.core.context import MNTContext
from app.platform.data.models.platform_client import PlatformClient
from app.platform.data.models.platform_assessment import PlatformAssessment
from app.platform.data.repositories.platform_client_repository import PlatformClientRepository

# Configure logging to see debug output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def make_mnt_context(
    macro_constraints=None,
    micro_constraints=None,
    food_exclusions=None,
    rule_ids=None,
):
    """Helper to create MNT context."""
    return MNTContext(
        assessment_id=uuid4(),
        macro_constraints=macro_constraints or {},
        micro_constraints=micro_constraints or {},
        food_exclusions=food_exclusions or [],
        rule_ids_used=rule_ids or [],
    )


def get_client_profile_from_db(
    db: Session,
    client_id: Optional[str] = None,
    limit: int = 2
) -> List[Dict[str, Any]]:
    """
    Fetch client profiles from the database.
    
    Args:
        db: Database session
        client_id: Optional specific client ID to fetch
        limit: Maximum number of clients to fetch (default: 2)
        
    Returns:
        List of client profile dictionaries ready for target engine
    """
    client_repo = PlatformClientRepository(db)
    profiles = []
    
    if client_id:
        # Fetch specific client
        try:
            from uuid import UUID
            client = client_repo.get_by_id(UUID(client_id))
            if client:
                clients = [client]
            else:
                print(f"[WARNING] Client {client_id} not found in database")
                return []
        except Exception as e:
            print(f"[WARNING] Error fetching client {client_id}: {e}")
            return []
    else:
        # Fetch all clients (up to limit)
        clients = client_repo.get_all(skip=0, limit=limit)
    
    if not clients:
        print("[WARNING] No clients found in database")
        return []
    
    # For each client, get their latest assessment to extract full profile
    for client in clients:
        # Get latest assessment for this client
        latest_assessment = (
            db.query(PlatformAssessment)
            .filter(PlatformAssessment.client_id == client.id)
            .order_by(PlatformAssessment.created_at.desc())
            .first()
        )
        
        # Build client profile from client data and assessment snapshot
        profile: Dict[str, Any] = {
            "weight_kg": client.weight_kg,
            "height_cm": client.height_cm,
            "age": client.age,
            "gender": client.gender,
        }
        
        # Extract additional data from assessment snapshot if available
        if latest_assessment and latest_assessment.assessment_snapshot:
            snapshot = latest_assessment.assessment_snapshot
            client_context = snapshot.get("client_context", {})
            clinical_data = snapshot.get("clinical_data", {})
            anthropometry = clinical_data.get("anthropometry", {})
            
            # Override with assessment data if available
            profile["age"] = client_context.get("age") or profile.get("age")
            profile["gender"] = client_context.get("gender") or profile.get("gender")
            profile["height_cm"] = client_context.get("height_cm") or anthropometry.get("height_cm") or profile.get("height_cm")
            profile["weight_kg"] = client_context.get("weight_kg") or anthropometry.get("weight_kg") or profile.get("weight_kg")
            profile["activity_level"] = client_context.get("activity_level")
            
            # Extract goals from assessment snapshot
            goals = snapshot.get("goals", {})
            if goals:
                profile["goals"] = goals
            
            # Extract medical conditions if needed
            medical_history = clinical_data.get("medical_history", {})
            if medical_history:
                conditions = medical_history.get("conditions", [])
                if conditions:
                    profile["medical_conditions"] = conditions
        
        # Add metadata for tracking
        profile["_client_id"] = str(client.id)
        profile["_client_name"] = client.name
        profile["_assessment_id"] = str(latest_assessment.id) if latest_assessment else None
        
        profiles.append(profile)
    
    return profiles


class TestTargetEngineStepByStep:
    """Step-by-step tests showing calculation formulas and intermediate values."""

    def test_real_client_profiles_from_db(self, platform_db: Session):
        """
        Test target calculations using real client profiles from the database.
        
        This test fetches up to 2 client profiles from the database and runs
        target calculations on them, showing step-by-step results.
        """
        # Fetch real client profiles from database
        client_profiles = get_client_profile_from_db(platform_db, limit=2)
        
        if not client_profiles:
            pytest.skip("No client profiles found in database. Create clients first.")
        
        engine = TargetEngine()
        
        print("\n" + "="*80)
        print(f"TEST: Real Client Profiles from Database ({len(client_profiles)} clients)")
        print("="*80)
        
        for idx, profile in enumerate(client_profiles, 1):
            client_name = profile.pop("_client_name", "Unknown")
            client_id = profile.pop("_client_id", "Unknown")
            assessment_id = profile.pop("_assessment_id", None)
            
            print(f"\n--- Client {idx}: {client_name} (ID: {client_id}) ---")
            print(f"Profile Data:")
            print(f"  Age: {profile.get('age')}")
            print(f"  Gender: {profile.get('gender')}")
            print(f"  Height: {profile.get('height_cm')} cm")
            print(f"  Weight: {profile.get('weight_kg')} kg")
            print(f"  Activity Level: {profile.get('activity_level', 'Not specified')}")
            print(f"  Goals: {profile.get('goals', {})}")
            
            # Create MNT context (empty for now, can be enhanced to fetch from DB)
            mnt = make_mnt_context()
            
            # Get activity level from profile or use default
            activity_level = profile.get("activity_level") or "moderately_active"
            
            # Calculate calories
            print(f"\n{'='*80}")
            print(f"[Calorie Calculation]")
            print(f"{'='*80}")
            calories_result = engine.calculate_calories(profile, mnt, activity_level=activity_level)
            
            print(f"\n--- IBW-Based Calculation (Primary Method) ---")
            print(f"  IBW: {calories_result.get('ibw')} kg")
            print(f"  IBW Calories (base): {calories_result.get('ibw_calories')} kcal")
            
            print(f"\n--- BMR/TDEE Calculation (Fallback Method) ---")
            print(f"  BMR: {calories_result.get('bmr')} kcal")
            print(f"  TDEE: {calories_result.get('tdee')} kcal")
            print(f"  (Note: BMR formula details shown in logs above)")
            
            print(f"\n--- Final Result ---")
            print(f"  Final Calories Target: {calories_result.get('calories_target')} kcal")
            print(f"  Calculation Source: {calories_result.get('calculation_source')}")
            print(f"\n  Note: Check logs above for detailed formula calculations:")
            print(f"    - Which BMR formula was selected from KB")
            print(f"    - Step-by-step BMR calculation")
            print(f"    - Activity multiplier used for TDEE")
            print(f"    - IBW activity factor mapping")
            
            # Calculate macros
            print(f"\n[Macro Calculation]")
            macros = engine.calculate_macros(
                calories_result.get('calories_target'),
                profile,
                mnt
            )
            
            print(f"  Carbohydrates: {macros['carbohydrates']['g']:.2f} g ({macros['carbohydrates']['percent']:.2f}%)")
            print(f"  Proteins: {macros['proteins']['g']:.2f} g ({macros['proteins']['percent']:.2f}%)")
            print(f"  Fats: {macros['fats']['g']:.2f} g ({macros['fats']['percent']:.2f}%)")
            
            # Calculate key micros
            print(f"\n[Micro Calculation]")
            key_micros = engine.calculate_key_micros(profile, mnt)
            print(f"  Key Micros: {len(key_micros)} nutrients calculated")
            
            # Full target calculation
            print(f"\n[Full Target Calculation]")
            full_result = engine.calculate_targets(profile, mnt, activity_level=activity_level)
            
            print(f"  Final Calories: {full_result.calories_target:.2f} kcal")
            print(f"  Source: {full_result.calculation_source}")
            print(f"  Macros: Carbs={full_result.macros['carbohydrates']['g']:.2f}g, "
                  f"Protein={full_result.macros['proteins']['g']:.2f}g, "
                  f"Fat={full_result.macros['fats']['g']:.2f}g")
            
            # Verify calculations are valid
            assert full_result.calories_target is not None
            assert full_result.calories_target > 0
            assert full_result.macros is not None
            assert full_result.key_micros is not None
            
            # Verify macro totals match calories
            total_macro_cal = (
                full_result.macros['proteins']['g'] * 4 +
                full_result.macros['fats']['g'] * 9 +
                full_result.macros['carbohydrates']['g'] * 4
            )
            assert abs(total_macro_cal - full_result.calories_target) < 1.0, \
                f"Macro calories ({total_macro_cal:.2f}) don't match target ({full_result.calories_target:.2f})"
            
            print(f"\n[PASS] Client {idx} calculations verified!")
        
        print("\n" + "="*80)
        print(f"[PASS] All {len(client_profiles)} client profiles tested successfully!")
        print("="*80)

    def test_female_weight_loss_ibw_calculation(self):
        """
        Test IBW-based calorie calculation for a female with weight loss goal.
        
        Scenario:
        - Female, 35 years old
        - Height: 165 cm
        - Weight: 75 kg
        - Activity: Moderately active
        - Goal: Weight loss (20% deficit)
        
        Expected calculations:
        1. IBW = Height - 100 = 165 - 100 = 65 kg
        2. IBW Calories = IBW × Activity Factor = 65 × 25 = 1,625 kcal
        3. Weight loss deficit (20%) = 1,625 × 0.8 = 1,300 kcal
        4. Minimum safe calories for female = 1,200 kcal
        5. Final target = max(1,300, 1,200) = 1,300 kcal
        """
        engine = TargetEngine()
        mnt = make_mnt_context()
        
        profile = {
            "weight_kg": 75,
            "height_cm": 165,
            "age": 35,
            "gender": "female",
            "goals": {
                "primary_goal": "weight_loss",
                "deficit_percent": 20.0
            }
        }
        
        print("\n" + "="*80)
        print("TEST: Female Weight Loss - IBW Calculation")
        print("="*80)
        print(f"Input Profile: {profile}")
        print(f"Activity Level: moderately_active")
        
        result = engine.calculate_calories(profile, mnt, activity_level="moderately_active")
        
        print("\n--- Calculation Results ---")
        print(f"IBW: {result.get('ibw')} kg")
        print(f"IBW Calories (base): {result.get('ibw_calories')} kcal")
        print(f"BMR: {result.get('bmr')} kcal")
        print(f"TDEE: {result.get('tdee')} kcal")
        print(f"Final Calories Target: {result.get('calories_target')} kcal")
        print(f"Calculation Source: {result.get('calculation_source')}")
        
        # Verify step-by-step
        expected_ibw = 165 - 100  # 65 kg
        expected_ibw_calories = expected_ibw * 25  # 1,625 kcal (moderately_active = 25 kcal/kg IBW)
        expected_after_deficit = expected_ibw_calories * 0.8  # 1,300 kcal (20% deficit)
        expected_final = max(expected_after_deficit, 1200.0)  # Minimum safe for female
        
        print("\n--- Expected Calculations ---")
        print(f"Step 1 - IBW: {profile['height_cm']} - 100 = {expected_ibw} kg")
        print(f"Step 2 - IBW Calories: {expected_ibw} × 25 (moderately_active) = {expected_ibw_calories} kcal")
        print(f"Step 3 - Weight Loss Deficit: {expected_ibw_calories} × (1 - 20/100) = {expected_after_deficit} kcal")
        print(f"Step 4 - Minimum Safe Check: max({expected_after_deficit}, 1200) = {expected_final} kcal")
        
        assert result.get('ibw') == pytest.approx(expected_ibw, rel=0.01)
        assert result.get('ibw_calories') == pytest.approx(expected_ibw_calories, rel=0.01)
        assert result.get('calories_target') == pytest.approx(expected_final, rel=0.01)
        assert result.get('calculation_source') in ["ibw_based_deficit", "custom_minimum"]
        
        print("\n[PASS] All assertions passed!")
        print("="*80)

    def test_female_weight_loss_tall_client(self):
        """
        Test for a tall female client to check if values are too high.
        
        Scenario:
        - Female, 30 years old
        - Height: 180 cm (tall)
        - Weight: 80 kg
        - Activity: Very active
        - Goal: Weight loss (20% deficit)
        
        Expected calculations:
        1. IBW = 180 - 100 = 80 kg
        2. IBW Calories = 80 × 30 = 2,400 kcal (very_active = 30 kcal/kg IBW)
        3. Weight loss deficit (20%) = 2,400 × 0.8 = 1,920 kcal
        4. Minimum safe = 1,200 kcal
        5. Final = 1,920 kcal (above minimum)
        """
        engine = TargetEngine()
        mnt = make_mnt_context()
        
        profile = {
            "weight_kg": 80,
            "height_cm": 180,
            "age": 30,
            "gender": "female",
            "goals": {
                "primary_goal": "weight_loss",
                "deficit_percent": 20.0
            }
        }
        
        print("\n" + "="*80)
        print("TEST: Tall Female Weight Loss - Checking for High Values")
        print("="*80)
        print(f"Input Profile: {profile}")
        print(f"Activity Level: very_active")
        
        result = engine.calculate_calories(profile, mnt, activity_level="very_active")
        
        print("\n--- Calculation Results ---")
        print(f"IBW: {result.get('ibw')} kg")
        print(f"IBW Calories (base): {result.get('ibw_calories')} kcal")
        print(f"Final Calories Target: {result.get('calories_target')} kcal")
        print(f"Calculation Source: {result.get('calculation_source')}")
        
        # Verify calculations
        expected_ibw = 180 - 100  # 80 kg
        expected_ibw_calories = expected_ibw * 30  # 2,400 kcal
        expected_after_deficit = expected_ibw_calories * 0.8  # 1,920 kcal
        
        print("\n--- Expected Calculations ---")
        print(f"Step 1 - IBW: {profile['height_cm']} - 100 = {expected_ibw} kg")
        print(f"Step 2 - IBW Calories: {expected_ibw} × 30 (very_active) = {expected_ibw_calories} kcal")
        print(f"Step 3 - Weight Loss Deficit: {expected_ibw_calories} × 0.8 = {expected_after_deficit} kcal")
        print(f"\n[WARNING] NOTE: This is a high value ({expected_after_deficit} kcal) for weight loss!")
        print("   Consider if activity factor mapping is correct.")
        
        assert result.get('ibw') == pytest.approx(expected_ibw, rel=0.01)
        assert result.get('ibw_calories') == pytest.approx(expected_ibw_calories, rel=0.01)
        assert result.get('calories_target') == pytest.approx(expected_after_deficit, rel=0.01)
        
        print("\n[PASS] All assertions passed!")
        print("="*80)

    def test_macro_calculation_step_by_step(self):
        """
        Test macro calculation step-by-step.
        
        Scenario:
        - Calories target: 1,500 kcal
        - Height: 165 cm (IBW = 65 kg)
        - Default protein: 0.8g per kg IBW
        
        Expected calculations:
        1. Protein: 65 × 0.8 = 52 g = 208 kcal (13.87%)
        2. Fat: 1,500 × 20% = 300 kcal = 33.33 g (20%)
        3. Carbs: 1,500 - 208 - 300 = 992 kcal = 248 g (66.13%)
        """
        engine = TargetEngine()
        mnt = make_mnt_context()
        
        profile = {
            "height_cm": 165,
            "goals": {}
        }
        
        calories_target = 1500.0
        
        print("\n" + "="*80)
        print("TEST: Macro Calculation Step-by-Step")
        print("="*80)
        print(f"Calories Target: {calories_target} kcal")
        print(f"Height: {profile['height_cm']} cm")
        
        result = engine.calculate_macros(calories_target, profile, mnt)
        
        print("\n--- Macro Calculation Results ---")
        print(f"Carbohydrates: {result['carbohydrates']['g']:.2f} g ({result['carbohydrates']['percent']:.2f}%)")
        print(f"Proteins: {result['proteins']['g']:.2f} g ({result['proteins']['percent']:.2f}%)")
        print(f"Fats: {result['fats']['g']:.2f} g ({result['fats']['percent']:.2f}%)")
        
        # Expected calculations
        ibw = 165 - 100  # 65 kg
        protein_g = ibw * 0.8  # 52 g
        protein_kcal = protein_g * 4.0  # 208 kcal
        protein_pct = (protein_kcal / calories_target) * 100.0  # 13.87%
        
        fat_pct = 20.0
        fat_kcal = calories_target * fat_pct / 100.0  # 300 kcal
        fat_g = fat_kcal / 9.0  # 33.33 g
        
        carb_kcal = calories_target - protein_kcal - fat_kcal  # 992 kcal
        carb_g = carb_kcal / 4.0  # 248 g
        carb_pct = (carb_kcal / calories_target) * 100.0  # 66.13%
        
        print("\n--- Expected Calculations ---")
        print(f"Step 1 - IBW: {profile['height_cm']} - 100 = {ibw} kg")
        print(f"Step 2 - Protein: {ibw} × 0.8 = {protein_g} g = {protein_kcal} kcal ({protein_pct:.2f}%)")
        print(f"Step 3 - Fat: {calories_target} × {fat_pct}% = {fat_kcal} kcal = {fat_g:.2f} g ({fat_pct}%)")
        print(f"Step 4 - Carbs (remainder): {calories_target} - {protein_kcal} - {fat_kcal} = {carb_kcal} kcal = {carb_g} g ({carb_pct:.2f}%)")
        print(f"Step 5 - Verification: {protein_kcal} + {fat_kcal} + {carb_kcal} = {protein_kcal + fat_kcal + carb_kcal} kcal")
        
        assert result['proteins']['g'] == pytest.approx(protein_g, rel=0.01)
        assert result['proteins']['percent'] == pytest.approx(protein_pct, rel=0.01)
        assert result['fats']['g'] == pytest.approx(fat_g, rel=0.01)
        assert result['fats']['percent'] == pytest.approx(fat_pct, rel=0.01)
        assert result['carbohydrates']['g'] == pytest.approx(carb_g, rel=0.01)
        assert result['carbohydrates']['percent'] == pytest.approx(carb_pct, rel=0.01)
        
        # Verify total calories
        total_cal = (result['proteins']['g'] * 4) + (result['fats']['g'] * 9) + (result['carbohydrates']['g'] * 4)
        assert total_cal == pytest.approx(calories_target, rel=0.01)
        
        print("\n[PASS] All assertions passed!")
        print("="*80)

    def test_full_target_calculation_female_weight_loss(self):
        """
        Full end-to-end test for female weight loss scenario.
        
        This test shows the complete calculation flow including:
        - Calorie calculation (IBW-based with deficit)
        - Macro calculation (IBW-based protein, fixed fat %)
        - Micro calculation (gender/age specific)
        """
        engine = TargetEngine()
        mnt = make_mnt_context()
        
        profile = {
            "weight_kg": 70,
            "height_cm": 160,
            "age": 28,
            "gender": "female",
            "goals": {
                "primary_goal": "weight_loss",
                "deficit_percent": 20.0
            }
        }
        
        print("\n" + "="*80)
        print("TEST: Full Target Calculation - Female Weight Loss")
        print("="*80)
        print(f"Input Profile: {profile}")
        print(f"Activity Level: moderately_active")
        
        result = engine.calculate_targets(profile, mnt, activity_level="moderately_active")
        
        print("\n--- Final Results ---")
        print(f"Calories Target: {result.calories_target:.2f} kcal")
        print(f"Calculation Source: {result.calculation_source}")
        print(f"\nMacros:")
        print(f"  Carbohydrates: {result.macros['carbohydrates']['g']:.2f} g ({result.macros['carbohydrates']['percent']:.2f}%)")
        print(f"  Proteins: {result.macros['proteins']['g']:.2f} g ({result.macros['proteins']['percent']:.2f}%)")
        print(f"  Fats: {result.macros['fats']['g']:.2f} g ({result.macros['fats']['percent']:.2f}%)")
        print(f"\nKey Micros: {len(result.key_micros)} nutrients calculated")
        
        # Verify calories
        expected_ibw = 160 - 100  # 60 kg
        expected_base = expected_ibw * 25  # 1,500 kcal
        expected_final = expected_base * 0.8  # 1,200 kcal (20% deficit)
        expected_final = max(expected_final, 1200.0)  # Minimum safe
        
        print("\n--- Expected Calorie Calculation ---")
        print(f"IBW: {profile['height_cm']} - 100 = {expected_ibw} kg")
        print(f"Base Calories: {expected_ibw} × 25 = {expected_base} kcal")
        print(f"After Deficit: {expected_base} × 0.8 = {expected_base * 0.8} kcal")
        print(f"Final (with minimum): max({expected_base * 0.8}, 1200) = {expected_final} kcal")
        
        assert result.calories_target == pytest.approx(expected_final, rel=0.01)
        assert result.macros is not None
        assert result.key_micros is not None
        
        # Verify macro totals
        total_macro_cal = (
            result.macros['proteins']['g'] * 4 +
            result.macros['fats']['g'] * 9 +
            result.macros['carbohydrates']['g'] * 4
        )
        assert total_macro_cal == pytest.approx(result.calories_target, rel=0.01)
        
        print(f"\n[PASS] Macro total verification: {total_macro_cal:.2f} kcal = {result.calories_target:.2f} kcal")
        print("[PASS] All assertions passed!")
        print("="*80)

    def test_activity_level_mapping(self):
        """
        Test that activity levels are correctly mapped to IBW factors.
        
        This test verifies the mapping logic in _get_ibw_activity_factor.
        """
        engine = TargetEngine()
        
        test_cases = [
            ("sedentary", 20.0),
            ("sedentary_lifestyle", 20.0),
            ("lightly_active", 25.0),
            ("moderately_active", 25.0),
            ("moderate_active", 25.0),
            ("moderate", 25.0),
            ("very_active", 30.0),
            ("highly_active", 30.0),
            ("extremely_active", 30.0),
            (None, 20.0),  # Default to sedentary
        ]
        
        print("\n" + "="*80)
        print("TEST: Activity Level Mapping to IBW Factors")
        print("="*80)
        
        for activity_level, expected_factor in test_cases:
            factor = engine._get_ibw_activity_factor(activity_level)
            print(f"Activity: '{activity_level}' → Factor: {factor} kcal/kg IBW (expected: {expected_factor})")
            assert factor == expected_factor
        
        print("\n[PASS] All activity level mappings correct!")
        print("="*80)

    def test_bmr_calculation_formula(self):
        """
        Test BMR calculation using the default formula.
        
        This verifies the BMR formula is correctly applied.
        """
        engine = TargetEngine()
        
        profile = {
            "weight_kg": 70,
            "height_cm": 175,
            "age": 30,
            "gender": "male"
        }
        
        print("\n" + "="*80)
        print("TEST: BMR Calculation Formula")
        print("="*80)
        print(f"Profile: {profile}")
        
        bmr = engine._calculate_bmr(
            profile["weight_kg"],
            profile["height_cm"],
            profile["age"],
            profile["gender"]
        )
        
        print(f"\nCalculated BMR: {bmr:.2f} kcal")
        print("\nNote: BMR formula coefficients are loaded from KB.")
        print("The actual formula depends on which formula is marked as default.")
        
        assert bmr is not None
        assert bmr > 0
        
        print("\n[PASS] BMR calculation successful!")
        print("="*80)

    def test_mnt_constraints_override(self):
        """
        Test that MNT constraints properly override goal-based calculations.
        """
        engine = TargetEngine()
        
        profile = {
            "weight_kg": 70,
            "height_cm": 165,
            "age": 35,
            "gender": "female",
            "goals": {
                "primary_goal": "weight_loss",
                "deficit_percent": 20.0
            }
        }
        
        # MNT constraint with different deficit
        mnt = make_mnt_context(
            macro_constraints={
                "calories": {
                    "deficit_percent": 30.0,  # MNT override: 30% deficit
                    "min": 1200
                }
            }
        )
        
        print("\n" + "="*80)
        print("TEST: MNT Constraints Override")
        print("="*80)
        print(f"Profile: {profile}")
        print(f"MNT Deficit: 30% (should override goal-based 20%)")
        
        result = engine.calculate_calories(profile, mnt, activity_level="moderately_active")
        
        print(f"\nBase IBW Calories: {result.get('ibw_calories')} kcal")
        print(f"Goal-based deficit (20%): Would be {result.get('ibw_calories') * 0.8:.2f} kcal")
        print(f"MNT deficit (30%): Should be {result.get('ibw_calories') * 0.7:.2f} kcal")
        print(f"Final Target: {result.get('calories_target')} kcal")
        print(f"Calculation Source: {result.get('calculation_source')}")
        
        # MNT should override, so 30% deficit should be applied
        expected_base = result.get('ibw_calories')
        expected_after_mnt = expected_base * 0.7  # 30% deficit
        expected_final = max(expected_after_mnt, 1200.0)  # Minimum
        
        assert result.get('calories_target') == pytest.approx(expected_final, rel=0.01)
        assert result.get('calculation_source') == "custom_mnt_override"
        
        print("\n[PASS] MNT override working correctly!")
        print("="*80)

"""
End-to-End Pipeline Testing Script for Client Verification
Generates comprehensive test outputs for all engines across multiple user profiles.

Usage:
    cd backend
    python scripts/e2e_pipeline_test.py

Output:
    - e2e_test_outputs/e2e_pipeline_results_TIMESTAMP.json (Full technical details)
    - e2e_test_outputs/e2e_pipeline_summary_TIMESTAMP.md (Client-friendly summary)
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

# Add backend to path
BACKEND_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal
from app.platform.core.orchestration.ncp_orchestrator import NCPOrchestrator
from app.platform.data.repositories.platform_client_repository import PlatformClientRepository
from app.platform.data.repositories.platform_assessment_repository import PlatformAssessmentRepository


class E2EPipelineTester:
    """End-to-end pipeline tester with comprehensive output generation."""
    
    def __init__(self, db: Session):
        self.db = db
        self.results: List[Dict[str, Any]] = []
        self.client_repo = PlatformClientRepository(db)
        self.assessment_repo = PlatformAssessmentRepository(db)
    
    def create_test_user(self, profile: Dict[str, Any]) -> UUID:
        """Create a test client with the given profile."""
        # Calculate age from date_of_birth if provided
        age = profile.get("age")
        if not age and profile.get("date_of_birth"):
            from datetime import datetime
            try:
                dob = datetime.strptime(profile["date_of_birth"], "%Y-%m-%d")
                age = (datetime.now() - dob).days // 365
            except:
                age = None
        
        client_data = {
            "name": profile.get("name", f"Test User {uuid4().hex[:8]}"),
            "age": age or profile.get("age"),
            "gender": profile.get("gender", "male"),
        }
        
        # Add optional fields if provided in assessment snapshot
        assessment_snapshot = profile.get("assessment_snapshot", {})
        client_context = assessment_snapshot.get("client_context", {})
        if client_context.get("height_cm"):
            client_data["height_cm"] = client_context["height_cm"]
        if client_context.get("weight_kg"):
            client_data["weight_kg"] = client_context["weight_kg"]
        # Ensure wake_time and sleep_time are always set (required by meal structure engine)
        client_data["wake_time"] = client_context.get("wake_time", "07:00")
        client_data["sleep_time"] = client_context.get("sleep_time", "22:00")
        if client_context.get("work_schedule"):
            work_schedule = client_context["work_schedule"]
            if isinstance(work_schedule, dict):
                if work_schedule.get("start"):
                    client_data["work_schedule_start"] = work_schedule["start"]
                if work_schedule.get("end"):
                    client_data["work_schedule_end"] = work_schedule["end"]
        
        client = self.client_repo.create(client_data)
        return client.id
    
    def create_assessment(self, client_id: UUID, assessment_snapshot: Dict[str, Any]) -> UUID:
        """Create an assessment for the client."""
        assessment_data = {
            "client_id": client_id,
            "assessment_snapshot": assessment_snapshot,
            "assessment_status": "completed",
        }
        
        assessment = self.assessment_repo.create(assessment_data)
        return assessment.id
    
    def serialize_context(self, context) -> Dict[str, Any]:
        """Serialize a context object to dict for JSON output."""
        if context is None:
            return None
        elif hasattr(context, '__dict__'):
            result = {}
            for k, v in context.__dict__.items():
                if k.startswith('_'):
                    continue
                result[k] = self._serialize_value(v)
            return result
        elif isinstance(context, dict):
            return {k: self._serialize_value(v) for k, v in context.items()}
        elif isinstance(context, (list, tuple)):
            return [self._serialize_value(item) for item in context]
        else:
            return str(context)
    
    def _serialize_value(self, value) -> Any:
        """Recursively serialize a value for JSON output."""
        if value is None:
            return None
        elif isinstance(value, (str, int, float, bool)):
            return value
        elif isinstance(value, UUID):
            return str(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, (list, tuple)):
            return [self._serialize_value(item) for item in value]
        elif isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        elif hasattr(value, '__dict__'):
            return self.serialize_context(value)
        else:
            return str(value)
    
    def run_pipeline_for_user(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Run complete pipeline for a single user profile."""
        print(f"\n{'='*80}")
        print(f"Testing Profile: {profile.get('name', 'Unknown')}")
        print(f"Description: {profile.get('description', 'N/A')}")
        print(f"{'='*80}")
        
        # Create client
        client_id = self.create_test_user(profile)
        print(f"✓ Created client: {client_id}")
        
        # Create assessment
        assessment_snapshot = profile.get("assessment_snapshot", {})
        assessment_id = self.create_assessment(client_id, assessment_snapshot)
        print(f"✓ Created assessment: {assessment_id}")
        
        # Initialize orchestrator
        enable_ayurveda = profile.get("enable_ayurveda", True)
        orchestrator = NCPOrchestrator(
            db=self.db,
            client_id=client_id,
            enable_ayurveda=enable_ayurveda
        )
        
        # Execute full pipeline
        try:
            print(f"✓ Starting pipeline execution...")
            pipeline_result = orchestrator.execute_full_pipeline(
                assessment_id=assessment_id,
                client_preferences=profile.get("client_preferences"),
                enable_ayurveda=enable_ayurveda
            )
            print(f"✓ Pipeline completed successfully")
            
            # Serialize all contexts for output
            result = {
                "test_profile": {
                    "name": profile.get("name"),
                    "description": profile.get("description"),
                    "scenario_type": profile.get("scenario_type"),
                },
                "client_id": str(client_id),
                "assessment_id": str(assessment_id),
                "pipeline_execution": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "success": True,
                },
                "stage_outputs": {
                    "1_assessment": self.serialize_context(pipeline_result.get("assessment")),
                    "2_diagnosis": self.serialize_context(pipeline_result.get("diagnosis")),
                    "3_mnt": self.serialize_context(pipeline_result.get("mnt")),
                    "4_target": self.serialize_context(pipeline_result.get("target")),
                    "5_meal_structure": self.serialize_context(pipeline_result.get("meal_structure")),
                    "6_exchange": self.serialize_context(pipeline_result.get("exchange")),
                    "7_ayurveda": self.serialize_context(pipeline_result.get("ayurveda")),
                    "8_intervention": self.serialize_context(pipeline_result.get("intervention")),
                    "9_recipe": self.serialize_context(pipeline_result.get("recipe")),
                },
                "inputs": {
                    "assessment_snapshot": assessment_snapshot,
                    "client_preferences": profile.get("client_preferences"),
                    "enable_ayurveda": enable_ayurveda,
                }
            }
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"✗ Pipeline failed: {str(e)}")
            print(f"  Error details: {error_trace}")
            
            result = {
                "test_profile": {
                    "name": profile.get("name"),
                    "description": profile.get("description"),
                    "scenario_type": profile.get("scenario_type"),
                },
                "client_id": str(client_id),
                "assessment_id": str(assessment_id),
                "pipeline_execution": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "error_traceback": error_trace,
                },
                "inputs": {
                    "assessment_snapshot": assessment_snapshot,
                    "client_preferences": profile.get("client_preferences"),
                    "enable_ayurveda": enable_ayurveda,
                }
            }
        
        return result
    
    def generate_test_profiles(self) -> List[Dict[str, Any]]:
        """Generate test profiles covering different scenarios."""
        profiles = []
        
        # Single simple test profile to start with
        profiles.append({
            "name": "T2D Weight Loss",
            "description": "45-year-old male with Type 2 Diabetes, overweight, goal: weight loss",
            "scenario_type": "diabetes_weight_loss",
            "gender": "male",
            "date_of_birth": "1978-05-15",
            "enable_ayurveda": True,
            "assessment_snapshot": {
                "client_context": {
                    "age": 45,
                    "gender": "male",
                    "height_cm": 170,
                    "weight_kg": 90,
                    "activity_level": "moderately_active",
                    "wake_time": "07:00",
                    "sleep_time": "22:00",
                },
                "clinical_data": {
                    "labs": {
                        "HbA1c": 7.8,
                        "FBS": 145,
                        "cholesterol": 220,
                        "triglycerides": 185,
                    },
                    "anthropometry": {
                        "bmi": 31.1,
                        "waist_circumference": 98,
                    },
                    "medical_history": {
                        "conditions": ["type_2_diabetes"],
                        "severity": {"type_2_diabetes": "moderate"},
                    },
                },
                "goals": {
                    "primary_goal": "weight_loss",
                    "secondary_goals": ["blood_sugar_control"],
                    "timeframe": "6_months",
                },
                "diet_data": {
                    "dietary_preferences": ["vegetarian"],
                },
                "ayurveda_data": {
                    "ayurveda_assessment": {
                        # Sample questionnaire answers for proper assessment
                        # Section 0: Client Context
                        "0.1_location_climate": "B",  # Moderate
                        "0.2_daily_physical_activity": "C",  # Moderate to Intense
                        
                        # Section 1: Physical Constitution (Prakriti)
                        "1.1_body_structure": "C",  # Broad/heavy - Kapha
                        "1.2_weight_pattern": "C",  # Gains easily - Kapha
                        "1.3_skin": "C",  # Thick, oily - Kapha
                        "1.4_hair": "C",  # Thick, oily - Kapha
                        "1.5_sweating": "C",  # Low but sticky - Kapha
                        
                        # Section 2: Appetite & Digestion (Agni)
                        "2.1_hunger_pattern": "C",  # Mild, delayed - Kapha/Manda Agni
                        "2.2_appetite_strength": "C",  # Can skip meals - Kapha
                        
                        # Section 3: Current Symptoms (Vikriti)
                        "3.1_current_complaints": ["weight_gain", "lethargy"],  # Kapha imbalance
                        "3.2_digestive_issues": "C",  # Slow digestion - Kapha
                        
                        # Section 4: Energy & Sleep
                        "4.1_energy_level": "C",  # Low - Kapha
                        "4.2_sleep_quality": "B",  # Deep - Kapha
                        
                        # Add more answers as needed - these are minimum required
                    }
                },
            },
            "client_preferences": {
                "dislikes": ["bitter_gourd"],
            },
        })
        
        # TODO: Add more test profiles here once the first one works
        # Uncomment and add profiles as needed
        
        return profiles
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all test profiles and collect results."""
        profiles = self.generate_test_profiles()
        
        print(f"\n{'#'*80}")
        print(f"Starting E2E Pipeline Testing")
        print(f"Total Test Profiles: {len(profiles)}")
        print(f"{'#'*80}")
        
        results = []
        for idx, profile in enumerate(profiles, 1):
            print(f"\n[{idx}/{len(profiles)}] Processing: {profile.get('name')}")
            try:
                result = self.run_pipeline_for_user(profile)
                results.append(result)
            except Exception as e:
                print(f"✗ Unexpected error processing profile: {str(e)}")
                import traceback
                traceback.print_exc()
                results.append({
                    "test_profile": {
                        "name": profile.get("name"),
                        "description": profile.get("description"),
                        "scenario_type": profile.get("scenario_type"),
                    },
                    "pipeline_execution": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "success": False,
                        "error": f"Unexpected error: {str(e)}",
                        "error_type": type(e).__name__,
                    },
                })
        
        return {
            "test_run_metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "total_profiles": len(profiles),
                "successful": sum(1 for r in results if r.get("pipeline_execution", {}).get("success", False)),
                "failed": sum(1 for r in results if not r.get("pipeline_execution", {}).get("success", True)),
            },
            "test_results": results,
        }
    
    def format_user_friendly_meal_plan(self, recipe_context: Dict[str, Any], meal_structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format meal plan for end-user consumption.
        Removes technical details and keeps only user-relevant information.
        """
        user_plan = {
            "plan_overview": {
                "duration_days": 7,
                "start_date": None,
                "meals_per_day": [],
                "meal_timings": {}
            },
            "daily_meal_plans": {}
        }
        
        # Extract meal timings from meal_structure
        timing_windows = meal_structure.get("timing_windows", {})
        for meal_name, windows in timing_windows.items():
            if windows and len(windows) >= 2:
                user_plan["plan_overview"]["meal_timings"][meal_name] = {
                    "recommended_time": windows[0],  # First window start time
                    "time_range": f"{windows[0]} - {windows[-1]}" if len(windows) > 1 else windows[0]
                }
            user_plan["plan_overview"]["meals_per_day"].append(meal_name)
        
        # Extract 7-day plan from recipe_context
        # The RecipeContext stores the full seven_day_plan structure in meals_with_recipes
        seven_day_plan_data = recipe_context.get("meals_with_recipes", {})
        
        # Check if it's the 7-day plan structure from MealPlanGenerator
        if isinstance(seven_day_plan_data, dict):
            # MealPlanGenerator returns structure with "days" key containing day_1, day_2, etc.
            if "days" in seven_day_plan_data:
                days_data = seven_day_plan_data["days"]
                # Also extract start_date if available
                if "start_date" in seven_day_plan_data:
                    user_plan["plan_overview"]["start_date"] = seven_day_plan_data["start_date"]
            elif any(k.startswith("day_") for k in seven_day_plan_data.keys()):
                # Direct days structure
                days_data = seven_day_plan_data
            else:
                # Single day structure - convert
                days_data = {"day_1": {"meals": seven_day_plan_data, "day_number": 1, "date": "", "day_name": ""}}
        else:
            days_data = {"day_1": {"meals": {}, "day_number": 1, "date": "", "day_name": ""}}
        
        # Format each day
        for day_key, day_data in days_data.items():
            if not isinstance(day_data, dict):
                continue
                
            day_number = day_data.get("day_number") or int(day_key.split("_")[-1]) if day_key.startswith("day_") else 1
            day_date = day_data.get("date", "")
            day_name = day_data.get("day_name", "")
            
            meals = day_data.get("meals", {})
            
            formatted_day = {
                "day": day_number,
                "date": day_date,
                "day_name": day_name,
                "meals": {}
            }
            
            # Format each meal
            for meal_name, meal_data in meals.items():
                if not isinstance(meal_data, dict):
                    continue
                    
                timing = user_plan["plan_overview"]["meal_timings"].get(meal_name, {})
                
                formatted_meal = {
                    "meal_name": meal_name,
                    "recommended_time": timing.get("recommended_time", ""),
                    "recipes": []
                }
                
                # Extract recipes
                recipes = meal_data.get("recipes", [])
                for recipe in recipes:
                    if not isinstance(recipe, dict):
                        continue
                    
                    # User-friendly recipe info
                    user_recipe = {
                        "recipe_name": recipe.get("recipe_name", "Recipe"),
                        "ingredients": [],
                        "portion": {},
                        "cooking_method": recipe.get("cooking_rules", {}).get("cooking_method", "standard"),
                        "spice_level": recipe.get("cooking_rules", {}).get("spice_level", "moderate"),
                        "oil_quantity": recipe.get("cooking_rules", {}).get("oil_quantity_g"),
                        "instructions": recipe.get("instructions", [])
                    }
                    
                    # Extract ingredient info
                    base_food = recipe.get("base_food", {})
                    if base_food:
                        user_recipe["ingredients"].append({
                            "name": base_food.get("display_name", ""),
                            "amount": f"{recipe.get('portion_g', 0):.1f}g"
                        })
                    
                    # Portion info (user-friendly)
                    portion_g = recipe.get("portion_g", 0)
                    if portion_g > 0:
                        user_recipe["portion"] = {
                            "grams": round(portion_g, 1),
                            "exchanges": recipe.get("exchanges", 0)
                        }
                    
                    # Remove empty fields
                    if not user_recipe["oil_quantity"]:
                        user_recipe.pop("oil_quantity", None)
                    if not user_recipe["instructions"]:
                        user_recipe.pop("instructions", None)
                    
                    formatted_meal["recipes"].append(user_recipe)
                
                formatted_day["meals"][meal_name] = formatted_meal
            
            user_plan["daily_meal_plans"][day_key] = formatted_day
        
        # Set start date if not already set and available from first day
        if not user_plan["plan_overview"]["start_date"] and days_data.get("day_1", {}).get("date"):
            user_plan["plan_overview"]["start_date"] = days_data.get("day_1", {}).get("date")
        
        return user_plan
    
    def save_results(self, results: Dict[str, Any], output_dir: Path = None):
        """Save results to JSON file with formatted output."""
        if output_dir is None:
            output_dir = BACKEND_ROOT / "e2e_test_outputs"
        
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed JSON
        json_file = output_dir / f"e2e_pipeline_results_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str, ensure_ascii=False)
        
        print(f"\n✓ Results saved to: {json_file}")
        
        # Generate client-friendly summary
        summary_file = output_dir / f"e2e_pipeline_summary_{timestamp}.md"
        self.generate_markdown_summary(results, summary_file)
        
        print(f"✓ Summary saved to: {summary_file}")
        
        # Generate user-friendly meal plan JSON for successful tests
        user_friendly_file = output_dir / f"user_meal_plan_{timestamp}.json"
        user_plans = {}
        
        for test_result in results.get("test_results", []):
            if not test_result.get("pipeline_execution", {}).get("success"):
                continue
                
            profile_name = test_result.get("test_profile", {}).get("name", "Unknown")
            recipe_context = test_result.get("stage_outputs", {}).get("9_recipe", {})
            meal_structure = test_result.get("stage_outputs", {}).get("5_meal_structure", {})
            
            if recipe_context and meal_structure:
                user_plan = self.format_user_friendly_meal_plan(recipe_context, meal_structure)
                user_plans[profile_name] = {
                    "client_id": test_result.get("client_id"),
                    "assessment_id": test_result.get("assessment_id"),
                    "plan_id": recipe_context.get("plan_id"),
                    "meal_plan": user_plan
                }
        
        if user_plans:
            with open(user_friendly_file, "w", encoding="utf-8") as f:
                json.dump(user_plans, f, indent=2, default=str, ensure_ascii=False)
            print(f"✓ User-friendly meal plan saved to: {user_friendly_file}")
        
        return json_file, summary_file, user_friendly_file if user_plans else None
    
    def generate_markdown_summary(self, results: Dict[str, Any], output_file: Path):
        """Generate a client-friendly markdown summary."""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# End-to-End Pipeline Test Results\n\n")
            f.write(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
            f.write("---\n\n")
            
            metadata = results["test_run_metadata"]
            f.write(f"## Test Run Summary\n\n")
            f.write(f"- **Total Profiles Tested:** {metadata['total_profiles']}\n")
            f.write(f"- **Successful:** {metadata['successful']} ✅\n")
            f.write(f"- **Failed:** {metadata['failed']} ❌\n\n")
            f.write("---\n\n")
            
            for idx, test_result in enumerate(results["test_results"], 1):
                profile = test_result.get("test_profile", {})
                execution = test_result.get("pipeline_execution", {})
                
                f.write(f"## Test {idx}: {profile.get('name', 'Unknown')}\n\n")
                f.write(f"**Description:** {profile.get('description', 'N/A')}\n\n")
                f.write(f"**Scenario Type:** {profile.get('scenario_type', 'N/A')}\n\n")
                f.write(f"**Status:** {'✅ SUCCESS' if execution.get('success') else '❌ FAILED'}\n\n")
                
                if test_result.get("client_id"):
                    f.write(f"**Client ID:** `{test_result.get('client_id')}`\n\n")
                if test_result.get("assessment_id"):
                    f.write(f"**Assessment ID:** `{test_result.get('assessment_id')}`\n\n")
                
                if not execution.get("success"):
                    f.write("### Error Details\n\n")
                    f.write(f"**Error Type:** `{execution.get('error_type', 'Unknown')}`\n\n")
                    f.write(f"**Error Message:**\n```\n{execution.get('error', 'Unknown error')}\n```\n\n")
                    if execution.get("error_traceback"):
                        f.write("**Full Traceback:**\n```\n")
                        f.write(execution.get("error_traceback"))
                        f.write("\n```\n\n")
                else:
                    f.write("### Engine Outputs (Sequential)\n\n")
                    stages = test_result.get("stage_outputs", {})
                    stage_labels = {
                        "1_assessment": "Assessment Stage",
                        "2_diagnosis": "Diagnosis Stage",
                        "3_mnt": "MNT (Medical Nutrition Therapy) Stage",
                        "4_target": "Target Calculation Stage",
                        "5_meal_structure": "Meal Structure Stage",
                        "6_exchange": "Exchange System Stage",
                        "7_ayurveda": "Ayurveda Advisory Stage",
                        "8_intervention": "Intervention (Food Lists) Stage",
                        "9_recipe": "Recipe Generation Stage",
                    }
                    
                    for stage_name in sorted(stages.keys()):
                        stage_label = stage_labels.get(stage_name, stage_name.replace('_', ' ').title())
                        f.write(f"#### {stage_label}\n\n")
                        stage_data = stages[stage_name]
                        
                        if stage_data is None:
                            f.write("*No data available*\n\n")
                        else:
                            f.write("```json\n")
                            f.write(json.dumps(stage_data, indent=2, default=str, ensure_ascii=False))
                            f.write("\n```\n\n")
                    
                    # Show inputs for reference
                    if test_result.get("inputs"):
                        f.write("### Input Data\n\n")
                        f.write("```json\n")
                        f.write(json.dumps(test_result.get("inputs"), indent=2, default=str, ensure_ascii=False))
                        f.write("\n```\n\n")
                
                f.write("---\n\n")
            
            # Add footer
            f.write("\n## Notes\n\n")
            f.write("- This report shows the complete end-to-end pipeline execution for each test profile.\n")
            f.write("- Each stage output represents the data passed between engines.\n")
            f.write("- Full technical details are available in the corresponding JSON file.\n")
            f.write(f"- Generated by E2E Pipeline Test Script\n")


def main():
    """Main entry point."""
    print("\n" + "="*80)
    print("E2E Pipeline Testing Script")
    print("="*80)
    
    # Initialize database connection
    db = SessionLocal()
    
    try:
        tester = E2EPipelineTester(db)
        results = tester.run_all_tests()
        save_result = tester.save_results(results)
        
        json_file = save_result[0]
        summary_file = save_result[1]
        user_plan_file = save_result[2] if len(save_result) > 2 and save_result[2] else None
        
        print(f"\n{'#'*80}")
        print("Testing Complete!")
        print(f"{'#'*80}")
        print(f"\nOutput Files:")
        print(f"  - JSON Results: {json_file}")
        print(f"  - Markdown Summary: {summary_file}")
        if user_plan_file:
            print(f"  - User-Friendly Meal Plan: {user_plan_file}")
        print(f"\nMetadata:")
        metadata = results["test_run_metadata"]
        print(f"  - Total Profiles: {metadata['total_profiles']}")
        print(f"  - Successful: {metadata['successful']}")
        print(f"  - Failed: {metadata['failed']}")
        print(f"\n")
        
    except Exception as e:
        print(f"\n✗ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()


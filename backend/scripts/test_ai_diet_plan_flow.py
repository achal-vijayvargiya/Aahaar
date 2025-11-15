"""
Test script for AI-powered diet plan generation flow.

This script demonstrates:
1. Step 1: Retrieve foods using AI agent
2. Step 2: Generate complete meal plan
3. Parsing of AI response
4. Saving to database

Run this after setting up your OpenRouter API key.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.client import Client
from app.models.health_profile import HealthProfile
from app.models.user import User
from app.utils.diet_plan_agent import DietPlanAgent
from app.utils.diet_plan_parser import DietPlanParser
from app.config import settings
from app.utils.logger import logger


def test_ai_diet_plan_generation():
    """
    Test the complete AI diet plan generation flow.
    """
    db: Session = SessionLocal()
    
    try:
        # Get a test client (first client in database)
        client = db.query(Client).first()
        if not client:
            print("❌ No clients found in database. Please create a client first.")
            return
        
        client_name = f"{client.first_name} {client.last_name}"
        print(f"✅ Using client: {client_name} (ID: {client.id})")
        
        # Get health profile
        health_profile = db.query(HealthProfile).filter(
            HealthProfile.client_id == client.id
        ).first()
        
        if not health_profile:
            print("❌ No health profile found. Please create a health profile first.")
            return
        
        print(f"✅ Health profile found")
        print(f"   - Weight: {health_profile.weight}kg")
        print(f"   - Height: {health_profile.height}cm")
        print(f"   - Age: {health_profile.age}")
        print(f"   - Goals: {health_profile.goals}")
        
        # Check API key
        if not settings.OPENROUTER_API_KEY or settings.OPENROUTER_API_KEY == "sk-or-v1-placeholder-get-from-openrouter-ai":
            print("❌ OpenRouter API key not configured. Please set OPENROUTER_API_KEY in .env file.")
            return
        
        print("✅ OpenRouter API key configured")
        print()
        
        # Initialize agent
        print("🤖 Initializing AI agent...")
        agent = DietPlanAgent(
            db=db,
            openrouter_api_key=settings.OPENROUTER_API_KEY,
            model=settings.DIET_PLAN_MODEL,
            temperature=settings.DIET_PLAN_TEMPERATURE
        )
        print("✅ Agent initialized")
        print()
        
        # Step 1: Retrieve foods
        print("=" * 80)
        print("STEP 1: RETRIEVE FOODS")
        print("=" * 80)
        
        profile_dict = {
            "weight": health_profile.weight,
            "height": health_profile.height,
            "age": health_profile.age,
            "activity_level": health_profile.activity_level or "moderately_active",
            "goals": health_profile.goals or "general wellness",
            "diet_type": health_profile.diet_type or "veg",
            "allergies": health_profile.allergies or "None"
        }
        
        preferences = {
            "prefer_satvik": True,
            "regional_foods": "Pan-Indian",
            "variety": "moderate"
        }
        
        step1_result = agent.generate_plan_step1_retrieve_foods(
            client_id=client.id,
            health_profile=profile_dict,
            preferences=preferences
        )
        
        if step1_result.get("status") == "error":
            print(f"❌ Error in Step 1: {step1_result.get('message')}")
            return
        
        print("✅ Step 1 completed!")
        print(f"   Status: {step1_result.get('status')}")
        print()
        print("AI Response (first 500 chars):")
        print("-" * 80)
        response_text = step1_result.get('response', '')
        print(response_text[:500])
        print("..." if len(response_text) > 500 else "")
        print()
        
        # Step 2: Generate meal plan
        print("=" * 80)
        print("STEP 2: GENERATE MEAL PLAN")
        print("=" * 80)
        
        step2_result = agent.generate_plan_step2_create_plan(
            client_id=client.id,
            user_feedback="confirm",
            modifications=None,
            duration_days=7
        )
        
        if step2_result.get("status") == "error":
            print(f"❌ Error in Step 2: {step2_result.get('message')}")
            return
        
        print("✅ Step 2 completed!")
        print(f"   Status: {step2_result.get('status')}")
        print()
        
        # Parse the response
        print("=" * 80)
        print("PARSING AI RESPONSE")
        print("=" * 80)
        
        parser = DietPlanParser()
        ai_response_text = step2_result.get("response", "")
        
        print(f"📄 AI Response length: {len(ai_response_text)} characters")
        print()
        print("Sample of AI response (first 1000 chars):")
        print("-" * 80)
        print(ai_response_text[:1000])
        print("..." if len(ai_response_text) > 1000 else "")
        print()
        
        parsed_data = parser.parse_diet_plan(ai_response_text)
        
        print("✅ Parsing completed!")
        print(f"   Total meals parsed: {parsed_data['total_meals']}")
        
        if parsed_data['meals']:
            print()
            print("📋 Sample meals (first 3):")
            for i, meal in enumerate(parsed_data['meals'][:3], 1):
                print(f"\n   Meal {i}:")
                print(f"   - Day: {meal.get('day_number')}")
                print(f"   - Time: {meal.get('meal_time')}")
                print(f"   - Type: {meal.get('meal_type')}")
                print(f"   - Dish: {meal.get('food_dish')}")
                print(f"   - Portion: {meal.get('portion')}")
                print(f"   - Calories: {meal.get('calories')}")
                print(f"   - Protein: {meal.get('protein_g')}g")
        
        # Validate meals
        print()
        print("=" * 80)
        print("VALIDATING PARSED MEALS")
        print("=" * 80)
        
        validation = parser.validate_meals(parsed_data["meals"])
        
        print(f"✅ Valid: {validation['valid']}")
        print(f"   Total meals: {validation['total_meals']}")
        print(f"   Days covered: {validation['days_covered']}")
        
        if validation['errors']:
            print("\n⚠️ Errors:")
            for error in validation['errors']:
                print(f"   - {error}")
        
        if validation['warnings']:
            print("\n⚠️ Warnings:")
            for warning in validation['warnings']:
                print(f"   - {warning}")
        
        print()
        print("=" * 80)
        print("✅ TEST COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print()
        print("The diet plan can now be saved to the database using the parsed data.")
        print("Use POST /diet-plans/generate-ai/step2 endpoint to generate and save in one go.")
        
    except Exception as e:
        logger.error(f"Error in test: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 80)
    print("AI-POWERED DIET PLAN GENERATION TEST")
    print("=" * 80)
    print()
    
    test_ai_diet_plan_generation()


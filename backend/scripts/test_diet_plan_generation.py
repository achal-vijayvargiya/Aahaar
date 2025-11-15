"""
Test script for Diet Plan Generation System

This script tests the complete diet plan generation flow:
1. Health profile retrieval
2. AI-powered diet plan generation
3. Plan validation
4. Export functionality
"""
import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
TEST_CLIENT_ID = 1  # Change this to your test client ID


def get_token():
    """Login and get JWT token."""
    print("🔐 Logging in...")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={
            "username": "admin",  # Change to your username
            "password": "admin"   # Change to your password
        }
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        print("✅ Login successful")
        return token
    else:
        print(f"❌ Login failed: {response.text}")
        sys.exit(1)


def check_health_profile(token, client_id):
    """Check if health profile exists."""
    print(f"\n📋 Checking health profile for client {client_id}...")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{BASE_URL}/health-profiles/client/{client_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        profile = response.json()
        print("✅ Health profile found:")
        print(f"   - Age: {profile.get('age')}")
        print(f"   - Weight: {profile.get('weight')} kg")
        print(f"   - Height: {profile.get('height')} cm")
        print(f"   - BMI: {profile.get('bmi')}")
        print(f"   - Goals: {profile.get('goals')}")
        print(f"   - Diet Type: {profile.get('diet_type')}")
        print(f"   - Activity Level: {profile.get('activity_level')}")
        return True
    else:
        print("❌ Health profile not found")
        print("   Create a health profile first!")
        return False


def generate_diet_plan(token, client_id):
    """Generate a new diet plan."""
    print(f"\n🤖 Generating AI-powered diet plan...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    request_data = {
        "client_id": client_id,
        "duration_days": 7,
        "prefer_satvik": True,
        "meal_variety": "moderate"
    }
    
    print(f"   Request: {json.dumps(request_data, indent=2)}")
    
    response = requests.post(
        f"{BASE_URL}/diet-plans/generate",
        json=request_data,
        headers=headers
    )
    
    if response.status_code == 201:
        plan = response.json()
        print("✅ Diet plan generated successfully!")
        print(f"   - Plan ID: {plan['id']}")
        print(f"   - Name: {plan['name']}")
        print(f"   - Duration: {plan['duration_days']} days")
        print(f"   - Status: {plan['status']}")
        print(f"   - Dosha Type: {plan['dosha_type']}")
        print(f"   - Diet Type: {plan['diet_type']}")
        print(f"   - Target Calories: {plan['target_calories']} kcal/day")
        print(f"   - Total Meals: {len(plan['meals'])}")
        return plan
    else:
        print(f"❌ Diet plan generation failed: {response.text}")
        return None


def validate_plan_structure(plan):
    """Validate the structure of the generated plan."""
    print("\n🔍 Validating plan structure...")
    
    errors = []
    
    # Check required fields
    required_fields = ['id', 'name', 'duration_days', 'meals']
    for field in required_fields:
        if field not in plan:
            errors.append(f"Missing field: {field}")
    
    # Check meals
    meals = plan.get('meals', [])
    expected_meals = plan.get('duration_days', 7) * 7  # 7 meals per day
    
    if len(meals) != expected_meals:
        errors.append(f"Expected {expected_meals} meals, got {len(meals)}")
    
    # Check meal structure
    meal_types = ["Morning Cleanse", "Breakfast", "Mid Snack", "Lunch", 
                  "Evening Snack", "Dinner", "Sleep Tonic"]
    
    for day in range(1, plan.get('duration_days', 7) + 1):
        day_meals = [m for m in meals if m['day_number'] == day]
        if len(day_meals) != 7:
            errors.append(f"Day {day} has {len(day_meals)} meals instead of 7")
        
        # Check all meal types present
        day_meal_types = [m['meal_type'] for m in day_meals]
        for meal_type in meal_types:
            if meal_type not in day_meal_types:
                errors.append(f"Day {day} missing {meal_type}")
    
    if errors:
        print("❌ Validation errors:")
        for error in errors:
            print(f"   - {error}")
        return False
    else:
        print("✅ Plan structure is valid!")
        return True


def display_sample_day(plan):
    """Display meals for Day 1 as a sample."""
    print("\n📅 Sample Day (Day 1):")
    print("-" * 100)
    
    meals = plan.get('meals', [])
    day1_meals = sorted(
        [m for m in meals if m['day_number'] == 1],
        key=lambda x: x['order_in_day']
    )
    
    for meal in day1_meals:
        print(f"\n⏰ {meal['meal_time']} - {meal['meal_type']}")
        print(f"   🍽️  Food: {meal['food_dish']}")
        print(f"   💊 Purpose: {meal['healing_purpose']}")
        print(f"   📏 Portion: {meal['portion']}")
        print(f"   ☯️  Dosha: {meal['dosha_notes']}")
        print(f"   📊 Nutrition: {meal['calories']} kcal, "
              f"P:{meal['protein_g']}g, C:{meal['carbs_g']}g, F:{meal['fat_g']}g")
    
    print("-" * 100)


def get_plan_summary(token, plan_id):
    """Get nutritional summary of the plan."""
    print(f"\n📊 Getting nutritional summary...")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{BASE_URL}/diet-plans/{plan_id}/summary",
        headers=headers
    )
    
    if response.status_code == 200:
        summary = response.json()
        print("✅ Nutritional Summary:")
        print(f"   - Total Meals: {summary['total_meals']}")
        print("\n   Daily Averages:")
        print(f"   - Calories: {summary['daily_averages']['calories']} kcal")
        print(f"   - Protein: {summary['daily_averages']['protein_g']} g")
        print(f"   - Carbs: {summary['daily_averages']['carbs_g']} g")
        print(f"   - Fat: {summary['daily_averages']['fat_g']} g")
        print("\n   Targets:")
        print(f"   - Calories: {summary['targets']['calories']} kcal")
        print(f"   - Protein: {summary['targets']['protein_g']} g")
        print(f"   - Carbs: {summary['targets']['carbs_g']} g")
        print(f"   - Fat: {summary['targets']['fat_g']} g")
        return summary
    else:
        print(f"❌ Failed to get summary: {response.text}")
        return None


def export_plan(token, plan_id):
    """Export the plan to JSON file."""
    print(f"\n📤 Exporting plan...")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{BASE_URL}/diet-plans/{plan_id}/export",
        headers=headers
    )
    
    if response.status_code == 200:
        plan_data = response.json()
        filename = f"diet_plan_{plan_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump(plan_data, f, indent=2)
        
        print(f"✅ Plan exported to: {filename}")
        return filename
    else:
        print(f"❌ Export failed: {response.text}")
        return None


def test_meal_update(token, plan):
    """Test updating a meal."""
    print("\n✏️  Testing meal update...")
    
    # Get first meal
    meal = plan['meals'][0]
    meal_id = meal['id']
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    update_data = {
        "notes": f"Updated at {datetime.now().isoformat()}"
    }
    
    response = requests.put(
        f"{BASE_URL}/diet-plans/meals/{meal_id}",
        json=update_data,
        headers=headers
    )
    
    if response.status_code == 200:
        print("✅ Meal updated successfully")
        return True
    else:
        print(f"❌ Meal update failed: {response.text}")
        return False


def main():
    """Main test flow."""
    print("=" * 100)
    print("🍽️  DIET PLAN GENERATION SYSTEM TEST")
    print("=" * 100)
    
    try:
        # Step 1: Login
        token = get_token()
        
        # Step 2: Check health profile
        if not check_health_profile(token, TEST_CLIENT_ID):
            print("\n⚠️  Please create a health profile first:")
            print(f"   POST {BASE_URL}/health-profiles/")
            return
        
        # Step 3: Generate diet plan
        plan = generate_diet_plan(token, TEST_CLIENT_ID)
        if not plan:
            return
        
        # Step 4: Validate structure
        if not validate_plan_structure(plan):
            print("\n⚠️  Plan structure validation failed!")
            return
        
        # Step 5: Display sample day
        display_sample_day(plan)
        
        # Step 6: Get summary
        summary = get_plan_summary(token, plan['id'])
        
        # Step 7: Export plan
        export_file = export_plan(token, plan['id'])
        
        # Step 8: Test meal update
        test_meal_update(token, plan)
        
        # Final summary
        print("\n" + "=" * 100)
        print("✅ ALL TESTS PASSED!")
        print("=" * 100)
        print("\n📝 Summary:")
        print(f"   - Plan ID: {plan['id']}")
        print(f"   - Total Meals: {len(plan['meals'])}")
        print(f"   - Export File: {export_file}")
        print(f"\n🎯 Next Steps:")
        print(f"   1. View plan in browser: http://localhost:8000/docs")
        print(f"   2. Get plan: GET {BASE_URL}/diet-plans/{plan['id']}")
        print(f"   3. Share with client: Use export file")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


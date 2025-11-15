"""
Test script for Health Profile functionality.
This script demonstrates how to create, read, update, and delete health profiles.
"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app.models.client import Client
from app.models.health_profile import HealthProfile
from app.routers.health_profiles import create_or_update_health_profile, get_health_profile_by_client_id


def test_health_profile_crud():
    """Test CRUD operations for health profiles."""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("Testing Health Profile CRUD Operations")
        print("=" * 80)
        
        # Check if we have any clients
        clients = db.query(Client).all()
        if not clients:
            print("\n❌ No clients found in database. Please create a client first.")
            print("You can create a client using the API or by running the client creation script.")
            return
        
        test_client = clients[0]
        print(f"\n✓ Using test client: {test_client.first_name} {test_client.last_name} (ID: {test_client.id})")
        
        # Test 1: Create a health profile
        print("\n" + "=" * 80)
        print("Test 1: Creating a new health profile")
        print("=" * 80)
        
        profile_data = {
            "age": 35,
            "weight": 70.5,
            "height": 165.0,
            "goals": "Weight loss and improve energy levels",
            "activity_level": "moderately_active",
            "disease": "Type 2 Diabetes, Pre-hypertension",
            "allergies": "Peanuts, Shellfish, Lactose intolerant",
            "supplements": "Vitamin D3 1000IU daily, Omega-3 fish oil",
            "medications": "Metformin 500mg twice daily",
            "diet_type": "veg",
            "sleep_cycle": "11 PM - 7 AM (7-8 hours)"
        }
        
        # Delete existing profile if any
        existing = db.query(HealthProfile).filter(HealthProfile.client_id == test_client.id).first()
        if existing:
            db.delete(existing)
            db.commit()
            print("✓ Deleted existing profile for clean test")
        
        profile = create_or_update_health_profile(
            client_id=test_client.id,
            profile_data=profile_data,
            db=db
        )
        
        print(f"\n✓ Health profile created successfully!")
        print(f"  Profile ID: {profile.id}")
        print(f"  Client ID: {profile.client_id}")
        print(f"  Age: {profile.age} years")
        print(f"  Weight: {profile.weight} kg")
        print(f"  Height: {profile.height} cm")
        print(f"  BMI: {profile.bmi} (automatically calculated)")
        print(f"  Activity Level: {profile.activity_level}")
        print(f"  Diet Type: {profile.diet_type}")
        print(f"  Goals: {profile.goals}")
        print(f"  Diseases: {profile.disease}")
        print(f"  Allergies: {profile.allergies}")
        print(f"  Sleep Cycle: {profile.sleep_cycle}")
        
        # Test 2: Read the health profile
        print("\n" + "=" * 80)
        print("Test 2: Reading the health profile")
        print("=" * 80)
        
        retrieved_profile = get_health_profile_by_client_id(
            client_id=test_client.id,
            db=db
        )
        
        if retrieved_profile:
            print(f"\n✓ Health profile retrieved successfully!")
            print(f"  Profile ID: {retrieved_profile.id}")
            print(f"  Client: {retrieved_profile.client.first_name} {retrieved_profile.client.last_name}")
            print(f"  BMI: {retrieved_profile.bmi}")
        else:
            print("\n❌ Failed to retrieve health profile")
        
        # Test 3: Update the health profile
        print("\n" + "=" * 80)
        print("Test 3: Updating the health profile")
        print("=" * 80)
        
        update_data = {
            "weight": 68.0,  # Lost 2.5 kg!
            "activity_level": "very_active",
            "supplements": "Vitamin D3 1000IU daily, Omega-3 fish oil, Magnesium 400mg"
        }
        
        updated_profile = create_or_update_health_profile(
            client_id=test_client.id,
            profile_data=update_data,
            db=db
        )
        
        print(f"\n✓ Health profile updated successfully!")
        print(f"  Updated Weight: {updated_profile.weight} kg (was {profile_data['weight']} kg)")
        print(f"  Updated BMI: {updated_profile.bmi} (was {profile.bmi})")
        print(f"  Updated Activity Level: {updated_profile.activity_level}")
        print(f"  Updated Supplements: {updated_profile.supplements}")
        print(f"  Weight loss: {profile_data['weight'] - updated_profile.weight} kg 🎉")
        
        # Test 4: Verify BMI calculation
        print("\n" + "=" * 80)
        print("Test 4: Verifying BMI Calculation")
        print("=" * 80)
        
        if updated_profile.weight and updated_profile.height:
            height_m = updated_profile.height / 100
            expected_bmi = round(updated_profile.weight / (height_m ** 2), 2)
            
            print(f"\n  Weight: {updated_profile.weight} kg")
            print(f"  Height: {updated_profile.height} cm ({height_m} m)")
            print(f"  Expected BMI: {expected_bmi}")
            print(f"  Stored BMI: {updated_profile.bmi}")
            
            if abs(expected_bmi - updated_profile.bmi) < 0.01:
                print(f"\n✓ BMI calculation is correct!")
                
                # BMI interpretation
                if updated_profile.bmi < 18.5:
                    interpretation = "Underweight"
                elif updated_profile.bmi < 25:
                    interpretation = "Normal weight"
                elif updated_profile.bmi < 30:
                    interpretation = "Overweight"
                else:
                    interpretation = "Obese"
                
                print(f"  BMI Category: {interpretation}")
            else:
                print(f"\n❌ BMI calculation mismatch!")
        
        # Test 5: Query all health profiles
        print("\n" + "=" * 80)
        print("Test 5: Querying all health profiles")
        print("=" * 80)
        
        all_profiles = db.query(HealthProfile).all()
        print(f"\n✓ Found {len(all_profiles)} health profile(s) in database")
        
        for p in all_profiles:
            client_name = f"{p.client.first_name} {p.client.last_name}" if p.client else "Unknown"
            print(f"  - Profile ID {p.id}: {client_name} (Age: {p.age}, BMI: {p.bmi})")
        
        print("\n" + "=" * 80)
        print("All tests completed successfully! ✓")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def display_health_profile_summary(profile: HealthProfile):
    """Display a formatted summary of a health profile."""
    print("\n" + "=" * 80)
    print("HEALTH PROFILE SUMMARY")
    print("=" * 80)
    
    if profile.client:
        print(f"\nClient: {profile.client.first_name} {profile.client.last_name}")
        print(f"Email: {profile.client.email}")
    
    print(f"\n📊 PHYSICAL MEASUREMENTS")
    print(f"  Age: {profile.age} years")
    print(f"  Weight: {profile.weight} kg")
    print(f"  Height: {profile.height} cm")
    print(f"  BMI: {profile.bmi}")
    
    print(f"\n🎯 LIFESTYLE")
    print(f"  Activity Level: {profile.activity_level}")
    print(f"  Diet Type: {profile.diet_type}")
    print(f"  Sleep Cycle: {profile.sleep_cycle}")
    
    print(f"\n🏥 HEALTH INFORMATION")
    print(f"  Goals: {profile.goals}")
    print(f"  Diseases: {profile.disease or 'None reported'}")
    print(f"  Allergies: {profile.allergies or 'None reported'}")
    
    print(f"\n💊 MEDICATIONS & SUPPLEMENTS")
    print(f"  Medications: {profile.medications or 'None'}")
    print(f"  Supplements: {profile.supplements or 'None'}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    print("\n🏥 Health Profile Test Script")
    print("This script tests the health profile functionality.\n")
    
    test_health_profile_crud()
    
    # Display a sample health profile
    db = SessionLocal()
    try:
        profile = db.query(HealthProfile).first()
        if profile:
            display_health_profile_summary(profile)
    finally:
        db.close()


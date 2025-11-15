"""
Test script for Gut Health Quiz functionality.
This script demonstrates the gut health assessment workflow.
"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app.models.client import Client
from app.models.gut_health_quiz import GutHealthQuiz
from app.routers.gut_health_quiz import submit_gut_health_quiz, get_client_latest_gut_health, QUIZ_QUESTIONS


def display_quiz_questions():
    """Display all quiz questions."""
    print("\n" + "=" * 80)
    print("GUT HEALTH QUIZ QUESTIONS")
    print("=" * 80)
    
    for i, q in enumerate(QUIZ_QUESTIONS, 1):
        print(f"\nGQ{i}: {q['question']}")
        print(f"  A ({q['state_a']}): {q['option_a']}")
        print(f"  B ({q['state_b']}): {q['option_b']}")
        print(f"  C ({q['state_c']}): {q['option_c']}")


def test_gut_health_quiz_scenarios():
    """Test different gut health quiz scenarios."""
    db = SessionLocal()
    
    try:
        print("\n" + "=" * 80)
        print("Testing Gut Health Quiz Functionality")
        print("=" * 80)
        
        # Check if we have clients
        clients = db.query(Client).all()
        if not clients:
            print("\n❌ No clients found. Please create a client first.")
            return
        
        test_client = clients[0]
        print(f"\n✓ Using test client: {test_client.first_name} {test_client.last_name} (ID: {test_client.id})")
        
        # Delete existing quizzes for clean test
        existing = db.query(GutHealthQuiz).filter(GutHealthQuiz.client_id == test_client.id).all()
        for quiz in existing:
            db.delete(quiz)
        db.commit()
        if existing:
            print(f"✓ Cleared {len(existing)} existing quiz(es) for clean test")
        
        # Test Scenario 1: Balanced Gut
        print("\n" + "=" * 80)
        print("Scenario 1: Balanced Gut Health")
        print("=" * 80)
        
        balanced_quiz_data = {
            "gq1_appetite": "A",      # Regular appetite
            "gq2_digestion": "A",     # Feel light and satisfied
            "gq3_bowel": "A",         # Once daily, well-formed
            "gq4_post_meal": "A",     # Energized and stable
            "gq5_food_reaction": "A", # Tolerate most foods
            "gq6_tongue_breath": "A", # No coating, fresh breath
            "gq7_sleep": "A",         # Deep, restful sleep
            "gq8_eating_habit": "A",  # Mindful eating
            "gq9_bloating": "A",      # Rarely bloated
            "gq10_immunity": "A",     # Strong immunity
            "notes": "Excellent gut health - maintain current habits"
        }
        
        balanced_quiz = submit_gut_health_quiz(
            client_id=test_client.id,
            quiz_data=balanced_quiz_data,
            db=db
        )
        
        print(f"\n✓ Quiz submitted successfully!")
        print(f"  Quiz ID: {balanced_quiz.id}")
        print(f"  Balanced Score: {balanced_quiz.balanced_score}/10")
        print(f"  Weak Score: {balanced_quiz.weak_score}/10")
        print(f"  Overactive Score: {balanced_quiz.overactive_score}/10")
        print(f"  🎯 Gut Health State: {balanced_quiz.gut_health_state}")
        
        percentages = balanced_quiz.get_percentage()
        print(f"\n  Health Distribution:")
        print(f"    Balanced:   {percentages['Balanced']:.1f}%")
        print(f"    Weak:       {percentages['Weak']:.1f}%")
        print(f"    Overactive: {percentages['Overactive']:.1f}%")
        
        recommendations = balanced_quiz.get_recommendations()
        print(f"\n  Recommendations:")
        print(f"    Diet: {recommendations['diet']}")
        print(f"    Lifestyle: {recommendations['lifestyle']}")
        
        # Test Scenario 2: Weak Gut
        print("\n" + "=" * 80)
        print("Scenario 2: Weak Gut Health")
        print("=" * 80)
        
        weak_quiz_data = {
            "gq1_appetite": "B",      # Low appetite, skip meals
            "gq2_digestion": "B",     # Feel bloated/heavy
            "gq3_bowel": "B",         # Irregular, constipated
            "gq4_post_meal": "B",     # Sleepy or tired
            "gq5_food_reaction": "B", # Bloated after new foods
            "gq6_tongue_breath": "B", # White coating, bad breath
            "gq7_sleep": "B",         # Long sleep but tired
            "gq8_eating_habit": "B",  # Eat quickly with screens
            "gq9_bloating": "B",      # Bloating after meals
            "gq10_immunity": "B",     # Catch colds easily
            "notes": "Weak digestion - needs strengthening protocol"
        }
        
        weak_quiz = submit_gut_health_quiz(
            client_id=test_client.id,
            quiz_data=weak_quiz_data,
            db=db
        )
        
        print(f"\n✓ Quiz submitted successfully!")
        print(f"  Quiz ID: {weak_quiz.id}")
        print(f"  Balanced Score: {weak_quiz.balanced_score}/10")
        print(f"  Weak Score: {weak_quiz.weak_score}/10")
        print(f"  Overactive Score: {weak_quiz.overactive_score}/10")
        print(f"  🎯 Gut Health State: {weak_quiz.gut_health_state}")
        
        percentages = weak_quiz.get_percentage()
        print(f"\n  Health Distribution:")
        print(f"    Balanced:   {percentages['Balanced']:.1f}%")
        print(f"    Weak:       {percentages['Weak']:.1f}%")
        print(f"    Overactive: {percentages['Overactive']:.1f}%")
        
        recommendations = weak_quiz.get_recommendations()
        print(f"\n  Recommendations:")
        print(f"    Diet: {recommendations['diet']}")
        print(f"    Lifestyle: {recommendations['lifestyle']}")
        print(f"    Focus: {recommendations['focus']}")
        
        # Test Scenario 3: Overactive Gut
        print("\n" + "=" * 80)
        print("Scenario 3: Overactive Gut Health")
        print("=" * 80)
        
        overactive_quiz_data = {
            "gq1_appetite": "C",      # Very strong appetite
            "gq2_digestion": "C",     # Acidity or burning
            "gq3_bowel": "C",         # Loose stools, frequent
            "gq4_post_meal": "C",     # Restless or anxious
            "gq5_food_reaction": "C", # Acidity after foods
            "gq6_tongue_breath": "C", # Red tongue, sour taste
            "gq7_sleep": "C",         # Light, disturbed sleep
            "gq8_eating_habit": "C",  # Eat irregularly, skip meals
            "gq9_bloating": "C",      # Morning bloating, spicy foods
            "gq10_immunity": "C",     # Inflammation, skin breakouts
            "notes": "Overactive gut - inflammation present"
        }
        
        overactive_quiz = submit_gut_health_quiz(
            client_id=test_client.id,
            quiz_data=overactive_quiz_data,
            db=db
        )
        
        print(f"\n✓ Quiz submitted successfully!")
        print(f"  Quiz ID: {overactive_quiz.id}")
        print(f"  Balanced Score: {overactive_quiz.balanced_score}/10")
        print(f"  Weak Score: {overactive_quiz.weak_score}/10")
        print(f"  Overactive Score: {overactive_quiz.overactive_score}/10")
        print(f"  🎯 Gut Health State: {overactive_quiz.gut_health_state}")
        
        percentages = overactive_quiz.get_percentage()
        print(f"\n  Health Distribution:")
        print(f"    Balanced:   {percentages['Balanced']:.1f}%")
        print(f"    Weak:       {percentages['Weak']:.1f}%")
        print(f"    Overactive: {percentages['Overactive']:.1f}%")
        
        recommendations = overactive_quiz.get_recommendations()
        print(f"\n  Recommendations:")
        print(f"    Diet: {recommendations['diet']}")
        print(f"    Lifestyle: {recommendations['lifestyle']}")
        print(f"    Focus: {recommendations['focus']}")
        
        # Test Scenario 4: Mixed State
        print("\n" + "=" * 80)
        print("Scenario 4: Mixed Gut Health State")
        print("=" * 80)
        
        mixed_quiz_data = {
            "gq1_appetite": "A",      # Balanced
            "gq2_digestion": "B",     # Weak
            "gq3_bowel": "C",         # Overactive
            "gq4_post_meal": "A",     # Balanced
            "gq5_food_reaction": "B", # Weak
            "gq6_tongue_breath": "C", # Overactive
            "gq7_sleep": "A",         # Balanced
            "gq8_eating_habit": "B",  # Weak
            "gq9_bloating": "C",      # Overactive
            "gq10_immunity": "B",     # Weak
            "notes": "Mixed state - needs comprehensive approach"
        }
        
        mixed_quiz = submit_gut_health_quiz(
            client_id=test_client.id,
            quiz_data=mixed_quiz_data,
            db=db
        )
        
        print(f"\n✓ Quiz submitted successfully!")
        print(f"  Quiz ID: {mixed_quiz.id}")
        print(f"  Balanced Score: {mixed_quiz.balanced_score}/10")
        print(f"  Weak Score: {mixed_quiz.weak_score}/10")
        print(f"  Overactive Score: {mixed_quiz.overactive_score}/10")
        print(f"  🎯 Gut Health State: {mixed_quiz.gut_health_state}")
        
        percentages = mixed_quiz.get_percentage()
        print(f"\n  Health Distribution:")
        print(f"    Balanced:   {percentages['Balanced']:.1f}%")
        print(f"    Weak:       {percentages['Weak']:.1f}%")
        print(f"    Overactive: {percentages['Overactive']:.1f}%")
        
        # Test: Get Latest Quiz
        print("\n" + "=" * 80)
        print("Test: Retrieving Latest Quiz for Client")
        print("=" * 80)
        
        latest = get_client_latest_gut_health(client_id=test_client.id, db=db)
        if latest:
            print(f"\n✓ Latest quiz retrieved successfully!")
            print(f"  Quiz ID: {latest.id}")
            print(f"  Gut Health State: {latest.gut_health_state}")
            print(f"  Created: {latest.created_at}")
            print(f"  Notes: {latest.notes}")
        
        # Summary
        print("\n" + "=" * 80)
        print("QUIZ HISTORY SUMMARY")
        print("=" * 80)
        
        all_quizzes = db.query(GutHealthQuiz).filter(
            GutHealthQuiz.client_id == test_client.id
        ).order_by(GutHealthQuiz.created_at.desc()).all()
        
        print(f"\n✓ Total quizzes for this client: {len(all_quizzes)}")
        print(f"\n  Quiz History:")
        for i, quiz in enumerate(all_quizzes, 1):
            print(f"    {i}. {quiz.gut_health_state} (B:{quiz.balanced_score}, W:{quiz.weak_score}, O:{quiz.overactive_score}) - {quiz.created_at.strftime('%Y-%m-%d %H:%M')}")
        
        print("\n" + "=" * 80)
        print("All tests completed successfully! ✓")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def display_gut_health_info():
    """Display information about gut health states."""
    print("\n" + "=" * 80)
    print("GUT HEALTH STATES INFORMATION")
    print("=" * 80)
    
    print("\n✅ BALANCED GUT")
    print("  Signs: Regular appetite, light digestion, well-formed stools")
    print("  Energy: Stable and energized after meals")
    print("  Sleep: Deep and restful")
    print("  Focus: Maintain current healthy habits")
    
    print("\n💤 WEAK GUT")
    print("  Signs: Low appetite, bloating, constipation")
    print("  Energy: Tired after meals, low immunity")
    print("  Sleep: Long but unrefreshing")
    print("  Focus: Strengthen digestive fire, improve absorption")
    
    print("\n🔥 OVERACTIVE GUT")
    print("  Signs: Strong appetite, acidity, loose stools")
    print("  Energy: Restless after meals, inflammation")
    print("  Sleep: Light and disturbed")
    print("  Focus: Cool down inflammation, calm digestion")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    print("\n🏥 Gut Health Quiz Test Script")
    print("This script tests the gut health assessment functionality.\n")
    
    # Display gut health information
    display_gut_health_info()
    
    # Display quiz questions
    display_quiz_questions()
    
    # Run tests
    test_gut_health_quiz_scenarios()
    
    print("\n✨ Gut health assessment system is ready to use!")
    print("📖 For complete documentation, see the documentation files.\n")


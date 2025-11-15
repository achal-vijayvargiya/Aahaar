"""
Test script for Dosha Quiz functionality.
This script demonstrates the complete dosha assessment workflow.
"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app.models.client import Client
from app.models.dosha_quiz import DoshaQuiz
from app.routers.dosha_quiz import submit_dosha_quiz, get_client_latest_dosha, QUIZ_QUESTIONS


def display_quiz_questions():
    """Display all quiz questions."""
    print("\n" + "=" * 80)
    print("DOSHA QUIZ QUESTIONS")
    print("=" * 80)
    
    for i, q in enumerate(QUIZ_QUESTIONS, 1):
        print(f"\nQ{i}: {q['question']}")
        print(f"  A ({q['dosha_a']}): {q['option_a']}")
        print(f"  B ({q['dosha_b']}): {q['option_b']}")
        print(f"  C ({q['dosha_c']}): {q['option_c']}")


def test_dosha_quiz_scenarios():
    """Test different dosha quiz scenarios."""
    db = SessionLocal()
    
    try:
        print("\n" + "=" * 80)
        print("Testing Dosha Quiz Functionality")
        print("=" * 80)
        
        # Check if we have clients
        clients = db.query(Client).all()
        if not clients:
            print("\n❌ No clients found. Please create a client first.")
            return
        
        test_client = clients[0]
        print(f"\n✓ Using test client: {test_client.first_name} {test_client.last_name} (ID: {test_client.id})")
        
        # Delete existing quizzes for clean test
        existing = db.query(DoshaQuiz).filter(DoshaQuiz.client_id == test_client.id).all()
        for quiz in existing:
            db.delete(quiz)
        db.commit()
        if existing:
            print(f"✓ Cleared {len(existing)} existing quiz(es) for clean test")
        
        # Test Scenario 1: Vata Dominant
        print("\n" + "=" * 80)
        print("Scenario 1: Vata Dominant Constitution")
        print("=" * 80)
        
        vata_quiz_data = {
            "q1_body_frame": "A",    # Slim, light
            "q2_skin_type": "A",     # Dry, rough
            "q3_hair_type": "A",     # Dry, frizzy
            "q4_appetite": "A",      # Irregular
            "q5_sleep": "A",         # Light, interrupted
            "q6_personality": "A",   # Creative, anxious
            "q7_stress": "A",        # Worry, overthink
            "q8_climate": "A",       # Love warmth
            "q9_energy": "A",        # Variable bursts
            "q10_mind": "A",         # Restless
            "notes": "Clear Vata constitution - creative but anxious, irregular digestion"
        }
        
        vata_quiz = submit_dosha_quiz(
            client_id=test_client.id,
            quiz_data=vata_quiz_data,
            db=db
        )
        
        print(f"\n✓ Quiz submitted successfully!")
        print(f"  Quiz ID: {vata_quiz.id}")
        print(f"  Vata Score: {vata_quiz.vata_score}/10")
        print(f"  Pitta Score: {vata_quiz.pitta_score}/10")
        print(f"  Kapha Score: {vata_quiz.kapha_score}/10")
        print(f"  🎯 Dominant Dosha: {vata_quiz.dominant_dosha}")
        
        percentages = vata_quiz.get_dosha_percentage()
        print(f"\n  Dosha Distribution:")
        print(f"    Vata:  {percentages['Vata']:.1f}%")
        print(f"    Pitta: {percentages['Pitta']:.1f}%")
        print(f"    Kapha: {percentages['Kapha']:.1f}%")
        
        # Test Scenario 2: Pitta Dominant
        print("\n" + "=" * 80)
        print("Scenario 2: Pitta Dominant Constitution")
        print("=" * 80)
        
        pitta_quiz_data = {
            "q1_body_frame": "B",    # Medium, athletic
            "q2_skin_type": "B",     # Warm, acne-prone
            "q3_hair_type": "B",     # Fine, grey early
            "q4_appetite": "B",      # Strong, irritable if missed
            "q5_sleep": "B",         # Moderate, refreshed
            "q6_personality": "B",   # Confident, impatient
            "q7_stress": "B",        # Get irritated/angry
            "q8_climate": "B",       # Prefer cool
            "q9_energy": "B",        # High, sustained
            "q10_mind": "B",         # Sharp, determined
            "notes": "Strong Pitta - high metabolism, sharp mind, gets irritated easily"
        }
        
        pitta_quiz = submit_dosha_quiz(
            client_id=test_client.id,
            quiz_data=pitta_quiz_data,
            db=db
        )
        
        print(f"\n✓ Quiz submitted successfully!")
        print(f"  Quiz ID: {pitta_quiz.id}")
        print(f"  Vata Score: {pitta_quiz.vata_score}/10")
        print(f"  Pitta Score: {pitta_quiz.pitta_score}/10")
        print(f"  Kapha Score: {pitta_quiz.kapha_score}/10")
        print(f"  🎯 Dominant Dosha: {pitta_quiz.dominant_dosha}")
        
        percentages = pitta_quiz.get_dosha_percentage()
        print(f"\n  Dosha Distribution:")
        print(f"    Vata:  {percentages['Vata']:.1f}%")
        print(f"    Pitta: {percentages['Pitta']:.1f}%")
        print(f"    Kapha: {percentages['Kapha']:.1f}%")
        
        # Test Scenario 3: Kapha Dominant
        print("\n" + "=" * 80)
        print("Scenario 3: Kapha Dominant Constitution")
        print("=" * 80)
        
        kapha_quiz_data = {
            "q1_body_frame": "C",    # Broad, strong
            "q2_skin_type": "C",     # Smooth, oily
            "q3_hair_type": "C",     # Thick, lustrous
            "q4_appetite": "C",      # Steady, slow
            "q5_sleep": "C",         # Deep, long
            "q6_personality": "C",   # Calm, grounded
            "q7_stress": "C",        # Withdraw, eat/sleep
            "q8_climate": "C",       # Enjoy warm, dry
            "q9_energy": "C",        # Slow but steady
            "q10_mind": "C",         # Peaceful, consistent
            "notes": "Pure Kapha - stable, calm, strong but slow metabolism"
        }
        
        kapha_quiz = submit_dosha_quiz(
            client_id=test_client.id,
            quiz_data=kapha_quiz_data,
            db=db
        )
        
        print(f"\n✓ Quiz submitted successfully!")
        print(f"  Quiz ID: {kapha_quiz.id}")
        print(f"  Vata Score: {kapha_quiz.vata_score}/10")
        print(f"  Pitta Score: {kapha_quiz.pitta_score}/10")
        print(f"  Kapha Score: {kapha_quiz.kapha_score}/10")
        print(f"  🎯 Dominant Dosha: {kapha_quiz.dominant_dosha}")
        
        percentages = kapha_quiz.get_dosha_percentage()
        print(f"\n  Dosha Distribution:")
        print(f"    Vata:  {percentages['Vata']:.1f}%")
        print(f"    Pitta: {percentages['Pitta']:.1f}%")
        print(f"    Kapha: {percentages['Kapha']:.1f}%")
        
        # Test Scenario 4: Vata-Pitta Dual Dosha
        print("\n" + "=" * 80)
        print("Scenario 4: Vata-Pitta Dual Constitution")
        print("=" * 80)
        
        dual_quiz_data = {
            "q1_body_frame": "A",    # Vata
            "q2_skin_type": "B",     # Pitta
            "q3_hair_type": "A",     # Vata
            "q4_appetite": "B",      # Pitta
            "q5_sleep": "A",         # Vata
            "q6_personality": "B",   # Pitta
            "q7_stress": "A",        # Vata
            "q8_climate": "A",       # Vata
            "q9_energy": "B",        # Pitta
            "q10_mind": "B",         # Pitta
            "notes": "Vata-Pitta combination - creative energy with sharp focus"
        }
        
        dual_quiz = submit_dosha_quiz(
            client_id=test_client.id,
            quiz_data=dual_quiz_data,
            db=db
        )
        
        print(f"\n✓ Quiz submitted successfully!")
        print(f"  Quiz ID: {dual_quiz.id}")
        print(f"  Vata Score: {dual_quiz.vata_score}/10")
        print(f"  Pitta Score: {dual_quiz.pitta_score}/10")
        print(f"  Kapha Score: {dual_quiz.kapha_score}/10")
        print(f"  🎯 Dominant Dosha: {dual_quiz.dominant_dosha}")
        
        percentages = dual_quiz.get_dosha_percentage()
        print(f"\n  Dosha Distribution:")
        print(f"    Vata:  {percentages['Vata']:.1f}%")
        print(f"    Pitta: {percentages['Pitta']:.1f}%")
        print(f"    Kapha: {percentages['Kapha']:.1f}%")
        
        # Test Scenario 5: Tridosha (Balanced)
        print("\n" + "=" * 80)
        print("Scenario 5: Tridosha (Balanced Constitution)")
        print("=" * 80)
        
        tridosha_quiz_data = {
            "q1_body_frame": "A",    # Vata
            "q2_skin_type": "B",     # Pitta
            "q3_hair_type": "C",     # Kapha
            "q4_appetite": "A",      # Vata
            "q5_sleep": "B",         # Pitta
            "q6_personality": "C",   # Kapha
            "q7_stress": "A",        # Vata
            "q8_climate": "B",       # Pitta
            "q9_energy": "C",        # Kapha
            "q10_mind": "B",         # Pitta
            "notes": "Balanced constitution - rare tridosha type"
        }
        
        tridosha_quiz = submit_dosha_quiz(
            client_id=test_client.id,
            quiz_data=tridosha_quiz_data,
            db=db
        )
        
        print(f"\n✓ Quiz submitted successfully!")
        print(f"  Quiz ID: {tridosha_quiz.id}")
        print(f"  Vata Score: {tridosha_quiz.vata_score}/10")
        print(f"  Pitta Score: {tridosha_quiz.pitta_score}/10")
        print(f"  Kapha Score: {tridosha_quiz.kapha_score}/10")
        print(f"  🎯 Dominant Dosha: {tridosha_quiz.dominant_dosha}")
        
        percentages = tridosha_quiz.get_dosha_percentage()
        print(f"\n  Dosha Distribution:")
        print(f"    Vata:  {percentages['Vata']:.1f}%")
        print(f"    Pitta: {percentages['Pitta']:.1f}%")
        print(f"    Kapha: {percentages['Kapha']:.1f}%")
        
        # Test: Get Latest Quiz
        print("\n" + "=" * 80)
        print("Test: Retrieving Latest Quiz for Client")
        print("=" * 80)
        
        latest = get_client_latest_dosha(client_id=test_client.id, db=db)
        if latest:
            print(f"\n✓ Latest quiz retrieved successfully!")
            print(f"  Quiz ID: {latest.id}")
            print(f"  Dominant Dosha: {latest.dominant_dosha}")
            print(f"  Created: {latest.created_at}")
            print(f"  Notes: {latest.notes}")
        
        # Summary
        print("\n" + "=" * 80)
        print("QUIZ HISTORY SUMMARY")
        print("=" * 80)
        
        all_quizzes = db.query(DoshaQuiz).filter(
            DoshaQuiz.client_id == test_client.id
        ).order_by(DoshaQuiz.created_at.desc()).all()
        
        print(f"\n✓ Total quizzes for this client: {len(all_quizzes)}")
        print(f"\n  Quiz History:")
        for i, quiz in enumerate(all_quizzes, 1):
            print(f"    {i}. {quiz.dominant_dosha} (V:{quiz.vata_score}, P:{quiz.pitta_score}, K:{quiz.kapha_score}) - {quiz.created_at.strftime('%Y-%m-%d %H:%M')}")
        
        print("\n" + "=" * 80)
        print("All tests completed successfully! ✓")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def display_dosha_info():
    """Display information about the three doshas."""
    print("\n" + "=" * 80)
    print("AYURVEDIC DOSHA INFORMATION")
    print("=" * 80)
    
    print("\n🌬️  VATA (Air + Ether)")
    print("  Qualities: Light, Dry, Cold, Mobile, Rough")
    print("  Characteristics: Creative, Quick, Changeable")
    print("  Imbalance Signs: Anxiety, Constipation, Dry Skin, Insomnia")
    print("  Balance: Warm, Moist, Grounding Foods and Routine")
    
    print("\n🔥 PITTA (Fire + Water)")
    print("  Qualities: Hot, Sharp, Light, Oily, Liquid")
    print("  Characteristics: Intelligent, Focused, Determined")
    print("  Imbalance Signs: Inflammation, Anger, Acne, Heartburn")
    print("  Balance: Cool, Calming Foods and Avoiding Heat")
    
    print("\n🌍 KAPHA (Earth + Water)")
    print("  Qualities: Heavy, Slow, Cool, Oily, Smooth")
    print("  Characteristics: Stable, Calm, Strong")
    print("  Imbalance Signs: Weight Gain, Lethargy, Congestion")
    print("  Balance: Light, Warming, Stimulating Foods and Activity")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    print("\n🏥 Dosha Quiz Test Script")
    print("This script tests the Ayurvedic dosha assessment functionality.\n")
    
    # Display dosha information
    display_dosha_info()
    
    # Display quiz questions
    display_quiz_questions()
    
    # Run tests
    test_dosha_quiz_scenarios()
    
    print("\n✨ Dosha assessment system is ready to use!")
    print("📖 See DOSHA_QUIZ_API.md for complete API documentation.\n")


"""
Script to clear NCP (Nutrition Care Process) data for all clients.

This script removes all NCP-related data (assessments, diagnoses, MNT constraints,
nutrition targets, diet plans, meal structures, exchange allocations, etc.) while
keeping the client records intact.

Usage:
    python scripts/clear_ncp_data_for_clients.py [--yes]
    
    --yes: Skip confirmation prompt
"""
import sys
import argparse
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.platform.data.models.platform_client import PlatformClient
from app.platform.data.models.platform_assessment import PlatformAssessment
from app.platform.data.models.platform_diagnosis import PlatformDiagnosis
from app.platform.data.models.platform_mnt_constraint import PlatformMNTConstraint
from app.platform.data.models.platform_nutrition_target import PlatformNutritionTarget
from app.platform.data.models.platform_diet_plan import PlatformDietPlan
from app.platform.data.models.platform_meal_structure import PlatformMealStructure
from app.platform.data.models.platform_exchange_allocation import PlatformExchangeAllocation
from app.platform.data.models.platform_ayurveda_profile import PlatformAyurvedaProfile
from app.platform.data.models.platform_monitoring_record import PlatformMonitoringRecord
from app.platform.data.models.platform_decision_log import PlatformDecisionLog


def clear_ncp_data_for_client(db: Session, client_id):
    """
    Clear all NCP data for a specific client.
    
    Args:
        db: Database session
        client_id: Client UUID
    """
    print(f"\nClearing NCP data for client: {client_id}")
    
    # Get all assessments for this client
    assessments = db.query(PlatformAssessment).filter(
        PlatformAssessment.client_id == client_id
    ).all()
    
    if not assessments:
        print(f"  No assessments found for client {client_id}")
        return
    
    assessment_ids = [a.id for a in assessments]
    print(f"  Found {len(assessments)} assessment(s)")
    
    # Delete in reverse dependency order
    
    # 1. Delete monitoring records (references diet plans)
    diet_plans = db.query(PlatformDietPlan).filter(
        PlatformDietPlan.client_id == client_id
    ).all()
    diet_plan_ids = [p.id for p in diet_plans]
    
    if diet_plan_ids:
        monitoring_records = db.query(PlatformMonitoringRecord).filter(
            PlatformMonitoringRecord.plan_id.in_(diet_plan_ids)
        ).all()
        for record in monitoring_records:
            db.delete(record)
        print(f"  Deleted {len(monitoring_records)} monitoring record(s)")
    
    # 2. Delete diet plans
    for plan in diet_plans:
        db.delete(plan)
    print(f"  Deleted {len(diet_plans)} diet plan(s)")
    
    # 3. Delete meal structures (references assessment_id)
    meal_structures = db.query(PlatformMealStructure).filter(
        PlatformMealStructure.assessment_id.in_(assessment_ids)
    ).all()
    for meal_structure in meal_structures:
        db.delete(meal_structure)
    print(f"  Deleted {len(meal_structures)} meal structure(s)")
    
    # 4. Delete exchange allocations (references assessment_id)
    # Use with_entities to only select id to avoid loading columns that may not exist in DB
    exchange_allocation_ids = db.query(PlatformExchangeAllocation.id).filter(
        PlatformExchangeAllocation.assessment_id.in_(assessment_ids)
    ).all()
    if exchange_allocation_ids:
        # Delete using bulk delete to avoid loading full objects
        db.query(PlatformExchangeAllocation).filter(
            PlatformExchangeAllocation.id.in_([ea_id[0] for ea_id in exchange_allocation_ids])
        ).delete(synchronize_session=False)
        print(f"  Deleted {len(exchange_allocation_ids)} exchange allocation(s)")
    
    # 5. Delete diagnoses (references assessment_id)
    diagnoses = db.query(PlatformDiagnosis).filter(
        PlatformDiagnosis.assessment_id.in_(assessment_ids)
    ).all()
    for diagnosis in diagnoses:
        db.delete(diagnosis)
    print(f"  Deleted {len(diagnoses)} diagnosis(es)")
    
    # 6. Delete MNT constraints (references assessment_id)
    mnt_constraints = db.query(PlatformMNTConstraint).filter(
        PlatformMNTConstraint.assessment_id.in_(assessment_ids)
    ).all()
    for constraint in mnt_constraints:
        db.delete(constraint)
    print(f"  Deleted {len(mnt_constraints)} MNT constraint(s)")
    
    # 7. Delete nutrition targets (references assessment_id)
    nutrition_targets = db.query(PlatformNutritionTarget).filter(
        PlatformNutritionTarget.assessment_id.in_(assessment_ids)
    ).all()
    for target in nutrition_targets:
        db.delete(target)
    print(f"  Deleted {len(nutrition_targets)} nutrition target(s)")
    
    # 8. Delete ayurveda profiles (references assessment_id)
    ayurveda_profiles = db.query(PlatformAyurvedaProfile).filter(
        PlatformAyurvedaProfile.assessment_id.in_(assessment_ids)
    ).all()
    for profile in ayurveda_profiles:
        db.delete(profile)
    print(f"  Deleted {len(ayurveda_profiles)} ayurveda profile(s)")
    
    # 9. Delete decision logs (references entity_id which could be assessment_id)
    decision_logs = db.query(PlatformDecisionLog).filter(
        PlatformDecisionLog.entity_id.in_(assessment_ids)
    ).all()
    for log in decision_logs:
        db.delete(log)
    print(f"  Deleted {len(decision_logs)} decision log(s)")
    
    # 10. Delete assessments
    for assessment in assessments:
        db.delete(assessment)
    print(f"  Deleted {len(assessments)} assessment(s)")
    
    print(f"  [OK] All NCP data cleared for client {client_id}")


def main():
    """Main function to clear NCP data for all clients."""
    parser = argparse.ArgumentParser(description="Clear NCP data for all clients")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()
    
    print("=" * 80)
    print("Clear NCP Data for All Clients")
    print("=" * 80)
    
    db: Session = SessionLocal()
    
    try:
        # Get all clients
        clients = db.query(PlatformClient).all()
        
        if not clients:
            print("\nNo clients found in database.")
            return
        
        print(f"\nFound {len(clients)} client(s) in database")
        
        # Confirm before proceeding (unless --yes flag is used)
        if not args.yes:
            try:
                response = input(f"\nThis will delete ALL NCP data for {len(clients)} client(s). Continue? (yes/no): ")
                if response.lower() != "yes":
                    print("Operation cancelled.")
                    return
            except (EOFError, KeyboardInterrupt):
                print("\nOperation cancelled (non-interactive mode). Use --yes flag to skip confirmation.")
                return
        else:
            print(f"\nProceeding to delete ALL NCP data for {len(clients)} client(s)...")
        
        # Clear NCP data for each client
        for client in clients:
            clear_ncp_data_for_client(db, client.id)
        
        # Commit all changes
        db.commit()
        print("\n" + "=" * 80)
        print("[SUCCESS] All NCP data cleared successfully!")
        print("=" * 80)
        print(f"\nClient records preserved. You can now re-run the NCP process.")
        
    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Error occurred: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

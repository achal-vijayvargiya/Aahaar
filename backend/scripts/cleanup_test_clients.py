"""
Cleanup script to delete all test clients created during E2E testing.

Usage:
    cd backend
    python scripts/cleanup_test_clients.py [--confirm]
    
Options:
    --confirm    Skip confirmation prompt and delete immediately

Safety:
    - Shows list of clients before deletion
    - Requires confirmation unless --confirm flag is used
    - Uses repository delete method which handles cascading deletes properly
"""
import sys
import argparse
from pathlib import Path

# Add backend to path
BACKEND_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal
from app.platform.data.repositories.platform_client_repository import PlatformClientRepository


def main():
    """Main cleanup function."""
    parser = argparse.ArgumentParser(description="Delete all test clients")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Skip confirmation prompt and delete immediately"
    )
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("Cleanup Test Clients Script")
    print("="*80 + "\n")
    
    # Initialize database connection
    db = SessionLocal()
    
    try:
        repository = PlatformClientRepository(db)
        
        # Get all clients
        print("Fetching all clients...")
        all_clients = repository.get_all(skip=0, limit=10000)  # Large limit to get all
        
        if not all_clients:
            print("✓ No clients found in database. Nothing to delete.\n")
            return
        
        print(f"Found {len(all_clients)} client(s):\n")
        
        # Display clients
        for idx, client in enumerate(all_clients, 1):
            print(f"  {idx}. ID: {client.id}")
            print(f"     Name: {client.name}")
            print(f"     Age: {client.age if client.age else 'N/A'}")
            print(f"     Gender: {client.gender if client.gender else 'N/A'}")
            print(f"     Created: {client.created_at if hasattr(client, 'created_at') else 'N/A'}")
            print()
        
        # Confirmation
        if not args.confirm:
            response = input(f"Delete all {len(all_clients)} client(s)? This will also delete all related records (assessments, plans, etc.). (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("\n✗ Cleanup cancelled. No clients were deleted.\n")
                return
        
        # Delete all clients
        print(f"\nDeleting {len(all_clients)} client(s)...")
        deleted_count = 0
        failed_count = 0
        errors = []
        
        for client in all_clients:
            try:
                # Use a separate transaction for each delete to avoid rollback affecting other deletions
                success = repository.delete(client.id)
                if success:
                    deleted_count += 1
                    print(f"  ✓ Deleted client: {client.name} ({client.id})")
                else:
                    failed_count += 1
                    error_msg = f"Failed to delete client: {client.name} ({client.id})"
                    print(f"  ✗ {error_msg}")
                    errors.append(error_msg)
            except Exception as e:
                failed_count += 1
                error_msg = f"Error deleting client {client.id} ({client.name if hasattr(client, 'name') else 'Unknown'}): {str(e)}"
                print(f"  ✗ {error_msg}")
                errors.append(error_msg)
                # Rollback this transaction to allow other deletions to proceed
                db.rollback()
        
        print(f"\n{'='*80}")
        print("Cleanup Complete!")
        print(f"{'='*80}")
        print(f"  ✓ Successfully deleted: {deleted_count}")
        if failed_count > 0:
            print(f"  ✗ Failed to delete: {failed_count}")
            if errors:
                print(f"\n  Errors encountered:")
                for error in errors[:10]:  # Show first 10 errors
                    print(f"    - {error}")
                if len(errors) > 10:
                    print(f"    ... and {len(errors) - 10} more errors")
        print()
        
    except Exception as e:
        print(f"\n✗ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

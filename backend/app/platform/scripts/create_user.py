"""
Create Platform User Script.

This script creates users in the platform_users table.
Can be run interactively or with command-line arguments.

Usage:
    # Interactive mode
    python -m app.platform.scripts.create_user

    # Command-line mode
    python -m app.platform.scripts.create_user --username admin --email admin@example.com --password admin123 --role admin

    # Create default admin and doctor users
    python -m app.platform.scripts.create_user --create-defaults
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.platform.data.repositories.platform_user_repository import PlatformUserRepository
from app.platform.utils.security import get_password_hash


def create_user(
    username: str,
    email: str,
    password: str,
    full_name: str = None,
    role: str = "doctor",
    is_active: bool = True,
    is_superuser: bool = False,
    db: Session = None
) -> bool:
    """
    Create a platform user.
    
    Args:
        username: Username for the user
        email: Email address
        password: Plain text password (will be hashed)
        full_name: Full name (optional)
        role: User role (doctor, admin, nurse) - default: doctor
        is_active: Whether user is active - default: True
        is_superuser: Whether user is superuser - default: False
        db: Database session (if None, creates new session)
        
    Returns:
        True if user was created, False if user already exists
    """
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False
    
    try:
        repo = PlatformUserRepository(db)
        
        # Check if user already exists
        existing_user = repo.get_by_username(username) or repo.get_by_email(email)
        if existing_user:
            print(f"✗ User already exists:")
            if existing_user.username == username:
                print(f"  Username '{username}' is already taken")
            if existing_user.email == email:
                print(f"  Email '{email}' is already registered")
            return False
        
        # Create user
        user_data = {
            "username": username,
            "email": email,
            "hashed_password": get_password_hash(password),
            "full_name": full_name,
            "role": role,
            "is_active": is_active,
            "is_superuser": is_superuser,
        }
        
        user = repo.create(user_data)
        
        print(f"✓ User created successfully!")
        print(f"  ID: {user.id}")
        print(f"  Username: {user.username}")
        print(f"  Email: {user.email}")
        print(f"  Full Name: {user.full_name or 'N/A'}")
        print(f"  Role: {user.role}")
        print(f"  Active: {user.is_active}")
        print(f"  Superuser: {user.is_superuser}")
        print(f"\n⚠️  Please change the password after first login!")
        
        return True
        
    except Exception as e:
        print(f"✗ Error creating user: {e}")
        if should_close:
            db.rollback()
        return False
    finally:
        if should_close:
            db.close()


def create_default_users(db: Session = None):
    """Create default admin and doctor users."""
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False
    
    try:
        print("Creating default users...")
        print("=" * 50)
        
        # Create admin user
        print("\n1. Creating admin user...")
        create_user(
            username="admin",
            email="admin@drassistent.com",
            password="admin123",
            full_name="System Administrator",
            role="admin",
            is_active=True,
            is_superuser=True,
            db=db
        )
        
        # Create doctor user
        print("\n2. Creating doctor user...")
        create_user(
            username="doctor",
            email="doctor@drassistent.com",
            password="doctor123",
            full_name="Dr. John Smith",
            role="doctor",
            is_active=True,
            is_superuser=False,
            db=db
        )
        
        print("\n" + "=" * 50)
        print("Default users creation completed!")
        
    except Exception as e:
        print(f"✗ Error creating default users: {e}")
        if should_close:
            db.rollback()
    finally:
        if should_close:
            db.close()


def interactive_mode():
    """Interactive mode to create a user."""
    print("=" * 50)
    print("Create Platform User")
    print("=" * 50)
    print()
    
    username = input("Username: ").strip()
    if not username:
        print("✗ Username is required")
        return
    
    email = input("Email: ").strip()
    if not email:
        print("✗ Email is required")
        return
    
    password = input("Password: ").strip()
    if not password:
        print("✗ Password is required")
        return
    
    full_name = input("Full Name (optional): ").strip() or None
    
    print("\nRole options: doctor, admin, nurse")
    role = input("Role [doctor]: ").strip() or "doctor"
    if role not in ["doctor", "admin", "nurse"]:
        print(f"✗ Invalid role '{role}'. Using 'doctor'")
        role = "doctor"
    
    is_active_input = input("Is Active? [Y/n]: ").strip().lower()
    is_active = is_active_input != "n"
    
    is_superuser_input = input("Is Superuser? [y/N]: ").strip().lower()
    is_superuser = is_superuser_input == "y"
    
    print()
    create_user(
        username=username,
        email=email,
        password=password,
        full_name=full_name,
        role=role,
        is_active=is_active,
        is_superuser=is_superuser
    )


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Create a platform user",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python -m app.platform.scripts.create_user

  # Create user with arguments
  python -m app.platform.scripts.create_user --username admin --email admin@example.com --password admin123 --role admin

  # Create default admin and doctor users
  python -m app.platform.scripts.create_user --create-defaults
        """
    )
    
    parser.add_argument("--username", type=str, help="Username")
    parser.add_argument("--email", type=str, help="Email address")
    parser.add_argument("--password", type=str, help="Password")
    parser.add_argument("--full-name", type=str, help="Full name")
    parser.add_argument("--role", type=str, choices=["doctor", "admin", "nurse"], default="doctor", help="User role")
    parser.add_argument("--inactive", action="store_true", help="Create user as inactive")
    parser.add_argument("--superuser", action="store_true", help="Create user as superuser")
    parser.add_argument("--create-defaults", action="store_true", help="Create default admin and doctor users")
    
    args = parser.parse_args()
    
    if args.create_defaults:
        create_default_users()
    elif args.username and args.email and args.password:
        # Command-line mode
        create_user(
            username=args.username,
            email=args.email,
            password=args.password,
            full_name=args.full_name,
            role=args.role,
            is_active=not args.inactive,
            is_superuser=args.superuser
        )
    else:
        # Interactive mode
        interactive_mode()


if __name__ == "__main__":
    main()


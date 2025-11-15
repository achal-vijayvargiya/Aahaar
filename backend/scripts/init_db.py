"""
Initialize database with sample data.
Run this script to create initial users and test data.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal, init_db
from app.models.user import User
from app.utils.security import get_password_hash
from app.utils.logger import logger


def create_initial_user(db: Session) -> None:
    """Create initial admin user if not exists."""
    admin_email = "admin@drassistent.com"
    
    # Check if admin user already exists
    existing_user = db.query(User).filter(User.email == admin_email).first()
    if existing_user:
        logger.info("Admin user already exists")
        return
    
    # Create admin user
    admin_user = User(
        email=admin_email,
        username="admin",
        hashed_password=get_password_hash("admin123"),
        full_name="System Administrator",
        role="admin",
        is_active=True,
        is_superuser=True
    )
    
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    
    logger.info(f"Created admin user: {admin_user.username}")
    print(f"✓ Admin user created successfully")
    print(f"  Email: {admin_email}")
    print(f"  Username: admin")
    print(f"  Password: admin123")
    print(f"  ⚠️  Please change the password after first login!")


def create_sample_doctor(db: Session) -> None:
    """Create a sample doctor user."""
    doctor_email = "doctor@drassistent.com"
    
    # Check if doctor user already exists
    existing_user = db.query(User).filter(User.email == doctor_email).first()
    if existing_user:
        logger.info("Doctor user already exists")
        return
    
    # Create doctor user
    doctor_user = User(
        email=doctor_email,
        username="doctor",
        hashed_password=get_password_hash("doctor123"),
        full_name="Dr. John Smith",
        role="doctor",
        is_active=True,
        is_superuser=False
    )
    
    db.add(doctor_user)
    db.commit()
    db.refresh(doctor_user)
    
    logger.info(f"Created doctor user: {doctor_user.username}")
    print(f"✓ Doctor user created successfully")
    print(f"  Email: {doctor_email}")
    print(f"  Username: doctor")
    print(f"  Password: doctor123")


def main():
    """Main function to initialize database."""
    print("=" * 50)
    print("Initializing DrAssistent Database")
    print("=" * 50)
    
    # Initialize database tables
    logger.info("Creating database tables...")
    init_db()
    print("✓ Database tables created")
    
    # Create session
    db = SessionLocal()
    
    try:
        # Create initial users
        create_initial_user(db)
        create_sample_doctor(db)
        
        print("=" * 50)
        print("Database initialization completed!")
        print("=" * 50)
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        print(f"✗ Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()


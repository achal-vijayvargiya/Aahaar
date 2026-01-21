"""
Run KB migration manually.

This script applies the KB fields migration (002_add_kb_fields.py) directly.
Use this if Alembic is not configured for platform migrations.

Usage:
    python scripts/run_kb_migration.py
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.database import engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_migration():
    """Run the KB fields migration."""
    logger.info("=" * 70)
    logger.info("RUNNING KB FIELDS MIGRATION")
    logger.info("=" * 70)
    
    # Read migration file
    migration_file = backend_dir / "app" / "platform" / "data" / "migrations" / "002_add_kb_fields.py"
    
    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        return False
    
    # Import migration module
    import importlib.util
    spec = importlib.util.spec_from_file_location("migration", migration_file)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    
    # Execute upgrade
    try:
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            try:
                logger.info("Executing migration upgrade()...")
                migration.upgrade()
                trans.commit()
                logger.info("✓ Migration completed successfully")
                return True
            except Exception as e:
                trans.rollback()
                logger.error(f"✗ Migration failed: {e}", exc_info=True)
                return False
    except Exception as e:
        logger.error(f"✗ Connection error: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)


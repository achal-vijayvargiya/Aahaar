"""
Platform Program Repository.
CRUD operations for platform programs.
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from app.platform.data.models.platform_program import PlatformProgram


class PlatformProgramRepository:
    """
    Repository for platform program operations.

    Provides CRUD and query methods for multi-week diet programs.
    """

    def __init__(self, db: Session):
        self.db = db

    def create(self, program_data: dict) -> PlatformProgram:
        """Create a new platform program."""
        program = PlatformProgram(**program_data)
        self.db.add(program)
        self.db.commit()
        self.db.refresh(program)
        return program

    def get_by_id(self, program_id: UUID) -> Optional[PlatformProgram]:
        """Get program by ID."""
        return self.db.query(PlatformProgram).filter(
            PlatformProgram.id == program_id
        ).first()

    def get_by_client_id(self, client_id: UUID) -> List[PlatformProgram]:
        """Get all programs for a client."""
        return self.db.query(PlatformProgram).filter(
            PlatformProgram.client_id == client_id
        ).all()

    def get_by_assessment_id(self, assessment_id: UUID) -> List[PlatformProgram]:
        """Get all programs for an assessment."""
        return self.db.query(PlatformProgram).filter(
            PlatformProgram.assessment_id == assessment_id
        ).all()

    def get_active_by_client_id(self, client_id: UUID) -> Optional[PlatformProgram]:
        """Get active program for a client (if any)."""
        return self.db.query(PlatformProgram).filter(
            PlatformProgram.client_id == client_id,
            PlatformProgram.status == "active"
        ).first()

    def update(self, program_id: UUID, program_data: dict) -> Optional[PlatformProgram]:
        """Update program."""
        program = self.get_by_id(program_id)
        if program:
            for key, value in program_data.items():
                setattr(program, key, value)
            self.db.commit()
            self.db.refresh(program)
        return program

    def delete(self, program_id: UUID) -> bool:
        """Delete program."""
        program = self.get_by_id(program_id)
        if program:
            self.db.delete(program)
            self.db.commit()
            return True
        return False

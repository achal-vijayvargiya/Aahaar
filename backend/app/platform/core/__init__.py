"""
Platform Core Module.
Core orchestration, state management, and context handling.
"""

from app.platform.core.context import (
    NCPStage,
    ClientContext,
    IntakeContext,
    AssessmentContext,
    DiagnosisContext,
    MNTContext,
    TargetContext,
    AyurvedaContext,
    InterventionContext,
    MonitoringContext,
)
from app.platform.core.state_machine import (
    ClientState,
    StateTransitionError,
    StateTransition,
    ClientStateMachine,
)
from app.platform.core.orchestration import NCPOrchestrator

__all__ = [
    # Context
    "NCPStage",
    "ClientContext",
    "IntakeContext",
    "AssessmentContext",
    "DiagnosisContext",
    "MNTContext",
    "TargetContext",
    "AyurvedaContext",
    "InterventionContext",
    "MonitoringContext",
    # State Machine
    "ClientState",
    "StateTransitionError",
    "StateTransition",
    "ClientStateMachine",
    # Orchestration
    "NCPOrchestrator",
]

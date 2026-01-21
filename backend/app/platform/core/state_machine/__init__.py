"""
Platform State Machine Module.
State management for client journey.
"""

from .client_state import (
    ClientState,
    StateTransitionError,
    StateTransition,
    ClientStateMachine,
)

__all__ = [
    "ClientState",
    "StateTransitionError",
    "StateTransition",
    "ClientStateMachine",
]

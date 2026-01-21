"""
Platform Client State Machine.
State management for client journey through NCP process.
"""
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID
from dataclasses import dataclass


class ClientState(Enum):
    """
    Client state enumeration.
    
    States follow the NCP process flow and prevent unsafe shortcuts.
    """
    NEW_CLIENT = "new_client"
    INTAKE_COMPLETED = "intake_completed"
    DIAGNOSED = "diagnosed"
    PLAN_GENERATED = "plan_generated"
    ACTIVE_MONITORING = "active_monitoring"


class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


@dataclass
class StateTransition:
    """
    State transition definition.
    
    Defines valid transitions between states.
    """
    from_state: ClientState
    to_state: ClientState
    condition: Optional[str] = None  # Optional condition description


class ClientStateMachine:
    """
    Client state machine.
    
    Manages client state transitions according to NCP process flow.
    Prevents unsafe shortcuts and enforces proper sequence.
    """
    
    # Valid state transitions
    VALID_TRANSITIONS: Dict[ClientState, list] = {
        ClientState.NEW_CLIENT: [ClientState.INTAKE_COMPLETED],
        ClientState.INTAKE_COMPLETED: [ClientState.DIAGNOSED],
        ClientState.DIAGNOSED: [ClientState.PLAN_GENERATED],
        ClientState.PLAN_GENERATED: [ClientState.ACTIVE_MONITORING],
        ClientState.ACTIVE_MONITORING: [],  # Terminal state
    }
    
    def __init__(self, client_id: UUID, initial_state: ClientState = ClientState.NEW_CLIENT):
        """
        Initialize state machine for a client.
        
        Args:
            client_id: Client UUID
            initial_state: Initial state (default: NEW_CLIENT)
        """
        self.client_id = client_id
        self.current_state = initial_state
        self.state_history: list = []
    
    def can_transition_to(self, target_state: ClientState) -> bool:
        """
        Check if transition to target state is valid.
        
        Args:
            target_state: Target state to check
            
        Returns:
            True if transition is valid, False otherwise
        """
        valid_targets = self.VALID_TRANSITIONS.get(self.current_state, [])
        return target_state in valid_targets
    
    def transition_to(self, target_state: ClientState) -> bool:
        """
        Attempt to transition to target state.
        
        Args:
            target_state: Target state to transition to
            
        Returns:
            True if transition succeeded, False otherwise
            
        Raises:
            StateTransitionError: If transition is invalid
        """
        if not self.can_transition_to(target_state):
            raise StateTransitionError(
                f"Cannot transition from {self.current_state.value} to {target_state.value}"
            )
        
        previous_state = self.current_state
        self.current_state = target_state
        self.state_history.append({
            "from": previous_state.value,
            "to": target_state.value,
        })
        return True
    
    def get_current_state(self) -> ClientState:
        """
        Get current state.
        
        Returns:
            Current ClientState
        """
        return self.current_state
    
    def get_state_history(self) -> list:
        """
        Get state transition history.
        
        Returns:
            List of state transitions
        """
        return self.state_history.copy()


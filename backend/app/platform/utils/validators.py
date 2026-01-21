"""
Platform Validators.
Validation utilities for the platform.
"""
from typing import Any, Optional, Dict
from uuid import UUID


def validate_uuid(value: Any) -> UUID:
    """
    Validate and convert value to UUID.
    
    Args:
        value: Value to validate
        
    Returns:
        UUID object
        
    Raises:
        ValueError: If value is not a valid UUID
    """
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        return UUID(value)
    raise ValueError(f"Invalid UUID: {value}")


def validate_required_field(data: Dict[str, Any], field_name: str) -> Any:
    """
    Validate that a required field exists in data.
    
    Args:
        data: Data dictionary
        field_name: Field name to validate
        
    Returns:
        Field value
        
    Raises:
        ValueError: If field is missing
    """
    if field_name not in data:
        raise ValueError(f"Required field missing: {field_name}")
    return data[field_name]


def validate_ncp_stage(stage: str) -> bool:
    """
    Validate NCP stage name.
    
    Args:
        stage: Stage name to validate
        
    Returns:
        True if valid stage
        
    Raises:
        ValueError: If stage is invalid
    """
    valid_stages = ["intake", "assessment", "diagnosis", "intervention", "monitoring"]
    if stage not in valid_stages:
        raise ValueError(f"Invalid NCP stage: {stage}. Valid stages: {valid_stages}")
    return True


def validate_client_state(state: str) -> bool:
    """
    Validate client state name.
    
    Args:
        state: State name to validate
        
    Returns:
        True if valid state
        
    Raises:
        ValueError: If state is invalid
    """
    valid_states = [
        "new_client",
        "intake_completed",
        "diagnosed",
        "plan_generated",
        "active_monitoring"
    ]
    if state not in valid_states:
        raise ValueError(f"Invalid client state: {state}. Valid states: {valid_states}")
    return True


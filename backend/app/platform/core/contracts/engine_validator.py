"""
Engine Validator Helper.

Provides validation functions that can be used by engines and orchestrator.
"""
from typing import Dict, Any, Type
import logging

from app.platform.core.contracts.validator import EngineContractValidator, ContractValidationError

logger = logging.getLogger(__name__)


def validate_engine_input(engine_name: str, input_data: Dict[str, Any], contract_class: Type) -> bool:
    """
    Validate engine input against contract.
    
    Args:
        engine_name: Name of engine for error messages
        input_data: Input data dictionary
        contract_class: Contract dataclass class
        
    Returns:
        True if valid
        
    Raises:
        ContractValidationError: If validation fails
    """
    return EngineContractValidator.validate_input(contract_class, input_data, engine_name)


def validate_engine_output(engine_name: str, output_data: Dict[str, Any], contract_class: Type) -> bool:
    """
    Validate engine output against contract.
    
    Args:
        engine_name: Name of engine for error messages
        output_data: Output data dictionary
        contract_class: Contract dataclass class
        
    Returns:
        True if valid
        
    Raises:
        ContractValidationError: If validation fails
    """
    return EngineContractValidator.validate_output(contract_class, output_data, engine_name)







"""
Platform Utils Module.
Utility functions and helpers for the platform.
"""

from .validators import (
    validate_uuid,
    validate_required_field,
    validate_ncp_stage,
    validate_client_state,
)
from .helpers import (
    generate_entity_id,
    format_timestamp,
    merge_dicts,
    safe_get,
    filter_none_values,
    chunk_list,
)
from .security import (
    verify_password,
    get_password_hash,
    create_access_token,
    verify_token,
)

__all__ = [
    # Validators
    "validate_uuid",
    "validate_required_field",
    "validate_ncp_stage",
    "validate_client_state",
    # Helpers
    "generate_entity_id",
    "format_timestamp",
    "merge_dicts",
    "safe_get",
    "filter_none_values",
    "chunk_list",
    # Security
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "verify_token",
]

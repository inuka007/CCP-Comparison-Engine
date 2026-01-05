"""
Mappings Module

Contains all mapping configurations for the comparison engine.
"""

from .column_mappings import (
    COLUMN_MAPPINGS,
    EXCLUDE_COLUMNS,
    get_ccp_to_at_mapping,
    get_mapped_columns,
    get_excluded_columns,
    should_compare_column
)

from .segment_mapping import (
    EXCHANGE_TO_SEGMENT,
    EXCHANGE_TO_REGION,
    get_region_for_exchange,
    is_etp,
    get_segment_name,
    classify_security
)

__all__ = [
    'COLUMN_MAPPINGS',
    'EXCLUDE_COLUMNS',
    'get_ccp_to_at_mapping',
    'get_mapped_columns',
    'get_excluded_columns',
    'should_compare_column',
    'EXCHANGE_TO_SEGMENT',
    'EXCHANGE_TO_REGION',
    'get_region_for_exchange',
    'is_etp',
    'get_segment_name',
    'classify_security'
]

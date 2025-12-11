"""
Column Mappings Configuration

This module defines the mapping between CCP whitelist column names and AT whitelist column names.
It serves as the single source of truth for column relationships in the comparison engine.

STRUCTURE:
1. COLUMN_MAPPINGS: Dictionary mapping CCP column names (keys) to AT column names (values)
2. EXCLUDE_COLUMNS: Set of columns to exclude from comparison
3. Helper functions for accessing and filtering the mappings

MAPPING DEFINITION:
The COLUMN_MAPPINGS dictionary maps CCP column names to their corresponding AT Whitelist column names.
- Key: CCP column name (normalized - lowercase with underscores)
- Value: AT column name (normalized - lowercase with underscores)
- Empty string (''): indicates no AT equivalent (CCP-only column)
"""

COLUMN_MAPPINGS = {
    'symbol': 'symbol',
    'exchange': 'exchange',
    'security_name': '',
    'currency': '',
    'isin': '',
    'country_code': '',
    'mic_code_x': '',
    'bbg_ticker': '',
    'tcl1': '',
    'tcl2': '',
    'tcl3': '',
    'status': '',
    'tradability': '',
    'mic_code_y': '',
    'minimum_order_value': 'minimum_order_value',
    'minimum_order_quantity': 'minimum_quantity',
    'minimum_ticker_price': 'min_ticker_price',
    'maximum_price_diff_preev_cls': '',
    'maximum_price_diff_other_prices': '',
    'enb_wfa_ord_in_prc_validtn': '',
    'buy_restricted': '',
    'sell_restricted': '',
    'maximum_notional': 'max_notional',
    'maximum_quantity': 'minimum_quantity',
    'maximum_single_moo_pool_quantity': 'max_single_moo_pool_qty',
    'accumulate_fractional_moo_order': 'accumulate_fractional_moo_order',
    'combine_buy_sell_moo_pool_order': 'combine_buy/sell_moo_pool_order',
    'accumulate_moo_in_pre_open': 'accumulate_moo_in_pre-open',
    'national_moo_pool_order': 'notional_moo_pool_order',
    'maximum_internal_exec_quantity': 'max_internal_exec_qty',
    'allow_less_than_one_execute_internally': 'allow_less_than_one_exec_intly',
    'enable_limit_less_than_eqty_min': 'enabled_limit_less_than_equity_min',
    'maximum_pool_profit_percent': 'max_pool_profit_%',
    'maximum_pool_loss_percent': 'max_pool_loss_%',
    'minimum_auto_close_quantity': 'min_auto_close_qty',
    'maximum_market_value_allowed_in_pool': 'max_market_value_allowed_in_pool',
    'allow_auto_close_limit': '',
    'allow_auto_close_whole_quantity_in_pool': 'allow_auto_close_whole_qty_pool',
    'allow_auto_close_whole_quantity_in_pool_scheduler': 'allow_auto_close_whole_qty_in_pool_scheduler',
    'minimum_quantity_for_additional_price_percent': 'minimum_qty_for_additional_price_%',
    'additional_price_percent': 'additional_price_%',
    'redis_price_enabled': '',
    'price_bracket_enabled': 'price_bracket_enabled',
}

EXCLUDE_COLUMNS = ['composite_key', 'updated_date', 'created_by', 'institution', 'updated_by', 'last_updated']


# ================================
# HELPER FUNCTIONS
# ================================

def get_ccp_to_at_mapping():
    """
    Get the CCP to AT column mapping
    
    Returns:
        Dictionary: {ccp_column: at_column}
    """
    return COLUMN_MAPPINGS.copy()


def get_mapped_columns():
    """
    Get list of (ccp_col, at_col) tuples for columns with AT equivalents
    Only returns mappings where AT column is not empty (excludes CCP-only fields)
    
    Returns:
        List of tuples: [(ccp_col, at_col), ...]
    """
    return [(ccp_col, at_col) for ccp_col, at_col in COLUMN_MAPPINGS.items() 
            if at_col and at_col != ""]


def get_excluded_columns():
    """
    Get set of columns to exclude from comparison
    All column names are converted to lowercase for case-insensitive matching
    
    Returns:
        Set: Set of excluded column names (lowercase)
    """
    return {col.lower() for col in EXCLUDE_COLUMNS}


def should_compare_column(ccp_col, at_col=None):
    """
    Determine if a column pair should be compared
    
    Returns False if:
    - The CCP column is in the exclusion list
    - The AT column is empty/None (CCP-only field)
    
    Args:
        ccp_col (str): CCP column name
        at_col (str): AT column name (optional)
    
    Returns:
        bool: True if column should be compared, False otherwise
    """
    ccp_col_lower = ccp_col.lower()
    
    # Check if CCP column is in exclusion list
    if ccp_col_lower in get_excluded_columns():
        return False
    
    # Check if AT column is empty
    if at_col is None or at_col == '' or at_col == "":
        return False
    
    return True

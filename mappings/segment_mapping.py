"""
Segment Mapping Module

Defines exchange-to-segment mapping and logic to classify securities as Equity or ETP.
"""

# Exchange to Region/Segment mapping
EXCHANGE_TO_SEGMENT = {
    'US': ['AMEX', 'NSDQ', 'NYSE', 'NSDQOT'],
    'EUROPE': ['CHIX', 'LSE'],
    'ASIA': ['HKEX', 'SGX']
}

# Reverse mapping: exchange -> region
EXCHANGE_TO_REGION = {}
for region, exchanges in EXCHANGE_TO_SEGMENT.items():
    for exchange in exchanges:
        EXCHANGE_TO_REGION[exchange.upper()] = region


def get_region_for_exchange(exchange):
    """
    Get region for a given exchange
    
    Args:
        exchange (str): Exchange code (case-insensitive)
    
    Returns:
        str: Region name ('US', 'EUROPE', 'ASIA') or None if not found
    """
    if exchange is None:
        return None
    exchange_upper = str(exchange).strip().upper()
    return EXCHANGE_TO_REGION.get(exchange_upper)


def is_etp(tcl1_value):
    """
    Determine if a security is an ETP based on tcl1 (Traded Products) column
    
    Args:
        tcl1_value: Value from ccp_only_tcl1 column
    
    Returns:
        bool: True if ETP, False if Equity (or unknown)
    """
    if tcl1_value is None or str(tcl1_value).strip() == '' or str(tcl1_value).lower() == 'nan':
        return False
    
    tcl1_str = str(tcl1_value).strip().upper()
    
    # Check for Equity indicator first (most common)
    if 'EQUITIES' in tcl1_str or 'EQUITY' in tcl1_str:
        return False
    
    # Check for ETP indicators
    etp_keywords = ['ETP', 'ETF', 'ETN', 'FUND', 'TRADED PRODUCTS']
    for keyword in etp_keywords:
        if keyword in tcl1_str:
            return True
    
    return False


def get_segment_name(region, is_etp_flag):
    """
    Get segment name from region and product type
    
    Args:
        region (str): Region ('US', 'EUROPE', 'ASIA')
        is_etp_flag (bool): True if ETP, False if Equity
    
    Returns:
        str: Segment name (e.g., 'US EQUITY', 'EUROPEAN ETP')
    """
    if region is None:
        return None
    
    region_upper = region.upper()
    product_type = 'ETP' if is_etp_flag else 'EQUITY'
    
    # Format region name for display
    if region_upper == 'US':
        region_display = 'US'
    elif region_upper == 'EUROPE':
        region_display = 'EUROPEAN'
    elif region_upper == 'ASIA':
        region_display = 'ASIA'
    else:
        return None
    
    return f"{region_display} {product_type}"


def classify_security(exchange, tcl1_value):
    """
    Classify a security into a segment name
    
    Args:
        exchange (str): Exchange code
        tcl1_value: Value from ccp_only_tcl1 column
    
    Returns:
        str: Segment name (e.g., 'US EQUITY', 'EUROPEAN ETP') or None if cannot classify
    """
    region = get_region_for_exchange(exchange)
    if region is None:
        return None
    
    etp_flag = is_etp(tcl1_value)
    return get_segment_name(region, etp_flag)

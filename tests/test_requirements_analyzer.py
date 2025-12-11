import pandas as pd
from requirements_analyzer import RequirementsAnalyzer


def make_composite_key(symbol, exchange):
    return f"{str(symbol).strip().upper()}|{str(exchange).strip().upper()}"


def test_requirements_analyzer_basic():
    # CCP combined (one record A|X)
    ccp_combined = pd.DataFrame([
        {'symbol': 'A', 'exchange': 'X', 'minimum_order_value': 100}
    ])
    ccp_combined['composite_key'] = ccp_combined.apply(lambda r: make_composite_key(r['symbol'], r['exchange']), axis=1)

    # AT whitelist: one matching record with different config, and one extra (C|Z)
    at = pd.DataFrame([
        {'symbol': 'A', 'exchange': 'X', 'minimum_order_value': 50},
        {'symbol': 'C', 'exchange': 'Z', 'minimum_order_value': 300}
    ])
    at['composite_key'] = at.apply(lambda r: make_composite_key(r['symbol'], r['exchange']), axis=1)

    analyzer = RequirementsAnalyzer(ccp_combined, at, 'symbol', 'symbol')
    results = analyzer.analyze()

    # Requirement 1: CCP but not in AT -> none
    assert len(results['requirement_1']) == 0

    # Requirement 2: AT but not in CCP -> C|Z (1)
    assert len(results['requirement_2']) == 1
    assert results['requirement_2'].iloc[0]['symbol'] == 'C'

    # Requirement 3: A|X exists in both but minimum_order_value differs
    assert len(results['requirement_3']) == 1
    mismatches = results['requirement_3'].iloc[0]['mismatched_fields']
    assert 'minimum_order_value' in mismatches

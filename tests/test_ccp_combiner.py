import pandas as pd
import sys
import os

# Add parent directory to path so imports resolve
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from combiners.ccp_combiner import CCPCombiner


def test_combine_basic_with_segment():
    """Test basic merge on exchange + segment"""
    ccp_sec = pd.DataFrame({
        'symbol': ['A', 'B'],
        'exchange': ['AMEX', 'CHIX'],
        'segment': ['US_EQUITY', 'EUROPEAN_EQUITY'],
        'security_name': ['s1', 's2']
    })

    ccp_rules = pd.DataFrame({
        'exchange': ['AMEX', 'CHIX'],
        'segment': ['US_EQUITY', 'EUROPEAN_EQUITY'],
        'minimum_order_value': [100, 200]
    })

    comb = CCPCombiner(ccp_sec, ccp_rules)
    comb.combine()
    combined = comb.get_combined()

    assert combined.shape[0] == 2
    assert 'minimum_order_value' in combined.columns
    assert comb.get_symbol_column() in ['symbol', 'security_id', 'isin', 'cusip', 'identifier', 'secid']


def test_segment_specific_rules():
    """Test that same exchange with different segments gets different rules"""
    ccp_sec = pd.DataFrame({
        'symbol': ['AAPL', 'SPY'],
        'exchange': ['AMEX', 'AMEX'],
        'segment': ['US_EQUITY', 'US_ETP'],
        'tcl1': ['Equities', 'Exchange Traded Products'],
        'security_name': ['Apple', 'SPY ETF']
    })

    ccp_rules = pd.DataFrame({
        'exchange': ['AMEX', 'AMEX'],
        'segment': ['US_EQUITY', 'US_ETP'],
        'minimum_order_value': [100, 500]
    })

    comb = CCPCombiner(ccp_sec, ccp_rules)
    comb.combine()
    combined = comb.get_combined()

    assert combined.shape[0] == 2
    # AAPL (US_EQUITY) should get rule 100
    aapl_row = combined[combined['symbol'] == 'AAPL'].iloc[0]
    assert aapl_row['minimum_order_value'] == 100
    # SPY (US_ETP) should get rule 500
    spy_row = combined[combined['symbol'] == 'SPY'].iloc[0]
    assert spy_row['minimum_order_value'] == 500


def test_exception_inclusion_reclassification():
    """Test that EXCEPTION_INCLUSION securities are reclassified to proper segments"""
    ccp_sec = pd.DataFrame({
        'symbol': ['AAPL', 'XYZ', 'ABC'],
        'exchange': ['AMEX', 'AMEX', 'CHIX'],
        'segment': ['US_EQUITY', 'EXCEPTION_INCLUSION', 'EXCEPTION_INCLUSION'],
        'tcl1': ['Equities', 'Equities', 'Exchange Traded Products'],
        'security_name': ['Apple', 'XYZ Corp', 'ABC Fund']
    })

    ccp_rules = pd.DataFrame({
        'exchange': ['AMEX', 'AMEX', 'CHIX', 'CHIX'],
        'segment': ['US_EQUITY', 'US_ETP', 'EUROPEAN_EQUITY', 'EUROPEAN_ETP'],
        'minimum_order_value': [100, 500, 200, 600]
    })

    comb = CCPCombiner(ccp_sec, ccp_rules)
    comb.combine()
    combined = comb.get_combined()

    assert combined.shape[0] == 3
    # XYZ was EXCEPTION_INCLUSION on AMEX with Equities tcl1 -> US_EQUITY -> rule 100
    xyz_row = combined[combined['symbol'] == 'XYZ'].iloc[0]
    assert xyz_row['segment'] == 'US_EQUITY'
    assert xyz_row['minimum_order_value'] == 100
    # ABC was EXCEPTION_INCLUSION on CHIX with ETP tcl1 -> EUROPEAN_ETP -> rule 600
    abc_row = combined[combined['symbol'] == 'ABC'].iloc[0]
    assert abc_row['segment'] == 'EUROPEAN_ETP'
    assert abc_row['minimum_order_value'] == 600


def test_fallback_exchange_only_merge():
    """Test fallback to exchange-only merge if no segment column"""
    ccp_sec = pd.DataFrame({
        'symbol': ['A', 'B'],
        'exchange': ['X', 'Y'],
        'security_name': ['s1', 's2']
    })

    ccp_rules = pd.DataFrame({
        'exchange': ['X', 'Y'],
        'minimum_order_value': [100, 200]
    })

    comb = CCPCombiner(ccp_sec, ccp_rules)
    comb.combine()
    combined = comb.get_combined()

    assert combined.shape[0] == 2
    assert 'minimum_order_value' in combined.columns


if __name__ == '__main__':
    test_combine_basic_with_segment()
    test_segment_specific_rules()
    test_exception_inclusion_reclassification()
    test_fallback_exchange_only_merge()
    print("All tests passed!")

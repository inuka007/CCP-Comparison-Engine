import pandas as pd
from ccp_combiner import CCPCombiner


def test_combine_basic():
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

    # Combined should have rows for each security and include rule columns
    assert combined.shape[0] == 2
    assert 'minimum_order_value' in combined.columns

    # Symbol column detected should be one of common candidates
    assert comb.get_symbol_column() in ['symbol', 'security_id', 'isin', 'cusip', 'identifier', 'secid']

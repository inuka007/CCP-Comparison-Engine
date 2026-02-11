"""
CCP Data Combiner Module

Combines CCP Security Whitelist and CCP Market Rules into a unified grid.
This module handles all CCP-specific data preparation and merging.
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class CCPCombiner:
    """Combines CCP Security Whitelist with CCP Market Rules"""
    
    def __init__(self, ccp_security_df, ccp_rules_df):
        """
        Initialize CCP combiner
        
        Args:
            ccp_security_df: CCP Security Whitelist dataframe (normalized columns)
            ccp_rules_df: CCP Market Rules dataframe (normalized columns)
        """
        self.ccp_sec = ccp_security_df.copy()
        self.ccp_rules = ccp_rules_df.copy()
        self.ccp_combined = None
        self.ccp_symbol_col = None
        
    def combine(self):
        """
        Combine CCP datasets
        
        Returns:
            CCPCombiner: self for method chaining
        """
        self._detect_symbol_column()
        self._merge_datasets()
        return self
    
    def _detect_symbol_column(self):
        """Detect symbol column in CCP Security whitelist"""
        common_names = ['symbol', 'security_id', 'isin', 'cusip', 'identifier', 'secid']
        
        for col in common_names:
            if col in self.ccp_sec.columns:
                self.ccp_symbol_col = col
                logger.info(f"Detected symbol column in CCP: {col}")
                return
        
        raise ValueError(f"Could not detect symbol column in CCP. Available: {list(self.ccp_sec.columns)}")
    
    def _merge_datasets(self):
        """
        Merge CCP Security Whitelist with CCP Market Rules
        
        Uses 'exchange' as the merge key with many-to-one relationship
        (many securities per exchange, one rule set per exchange)
        
        Handles duplicate exchange entries in Market Rules by keeping first occurrence
        """
        logger.info("Merging CCP Security Whitelist with CCP Market Rules...")
        
        # Check for duplicate exchanges in Market Rules
        if 'exchange' in self.ccp_rules.columns:
            duplicates = self.ccp_rules['exchange'].duplicated().sum()
            if duplicates > 0:
                logger.warning(f"Found {duplicates} duplicate exchange entries in CCP Market Rules")
                logger.info("Keeping first occurrence of each exchange")
                # Keep only the first occurrence of each exchange
                ccp_rules_unique = self.ccp_rules.drop_duplicates(subset=['exchange'], keep='first')
                logger.info(f"Reduced Market Rules from {len(self.ccp_rules)} to {len(ccp_rules_unique)} rows")
            else:
                ccp_rules_unique = self.ccp_rules
        else:
            ccp_rules_unique = self.ccp_rules
        
        self.ccp_combined = pd.merge(
            self.ccp_sec,
            ccp_rules_unique,
            on="exchange",
            how="left",
            validate="m:1"
        )
        
        logger.info(f"CCP combined shape: {self.ccp_combined.shape}")
        logger.info(f"CCP combined columns: {len(self.ccp_combined.columns)}")
    
    def get_combined(self):
        """
        Get the combined CCP dataframe
        
        Returns:
            pd.DataFrame: Combined CCP grid (Security + Market Rules)
        """
        if self.ccp_combined is None:
            raise ValueError("CCP data has not been combined. Call combine() first.")
        return self.ccp_combined
    
    def get_symbol_column(self):
        """
        Get the detected symbol column name
        
        Returns:
            str: Symbol column name
        """
        if self.ccp_symbol_col is None:
            raise ValueError("Symbol column has not been detected. Call combine() first.")
        return self.ccp_symbol_col
